using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using ScpCv.Contracts.Http;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Media;

public sealed partial class MediaSourceService(
    IDbContextFactory<ControlDbContext> contextFactory,
    WriteCoordinator writes,
    ControlDbContextFactory controlDbFactory,
    MediaStorageOptions storageOptions,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;
    private readonly string _uploadRoot = Path.GetFullPath(
        Path.Combine(controlDbFactory.Layout.RootPath, "media", "uploads"));
    private readonly string[] _allowedRoots = BuildAllowedRoots(controlDbFactory, storageOptions);

    public async Task<IReadOnlyList<MediaFolderDto>> ListFoldersAsync(CancellationToken cancellationToken = default)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        return await database.MediaFolders.AsNoTracking()
            .OrderBy(folder => folder.Id)
            .Select(folder => new MediaFolderDto
            {
                Id = folder.Id,
                Name = folder.Name,
                ParentId = folder.ParentId,
                CreatedAt = folder.CreatedAt.ToString("O"),
                UpdatedAt = folder.UpdatedAt.ToString("O"),
            })
            .ToListAsync(cancellationToken)
            .ConfigureAwait(false);
    }

    public Task<MediaFolderDto> CreateFolderAsync(
        string name,
        long? parentId,
        CancellationToken cancellationToken = default)
    {
        var normalizedName = ValidateName(name, "文件夹名称不能为空");
        return writes.ExecuteAsync(
            async (database, token) =>
            {
                if (parentId is not null && !await database.MediaFolders.AnyAsync(
                        folder => folder.Id == parentId.Value,
                        token).ConfigureAwait(false))
                {
                    throw new MediaServiceException($"父文件夹 id={parentId.Value} 不存在");
                }

                var now = _timeProvider.GetUtcNow();
                var folder = new MediaFolder
                {
                    Name = normalizedName,
                    ParentId = parentId,
                    CreatedAt = now,
                    UpdatedAt = now,
                };
                database.MediaFolders.Add(folder);
                await database.SaveChangesAsync(token).ConfigureAwait(false);
                return ToFolderDto(folder);
            },
            cancellationToken);
    }

    public Task<MediaFolderDto> UpdateFolderAsync(
        long folderId,
        string? name,
        long? parentId,
        bool updateParent,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (database, token) =>
            {
                var folder = await database.MediaFolders.SingleOrDefaultAsync(
                        candidate => candidate.Id == folderId,
                        token).ConfigureAwait(false)
                    ?? throw new MediaServiceException($"文件夹 id={folderId} 不存在", isNotFound: true);
                if (name is not null)
                {
                    folder.Name = ValidateName(name, "文件夹名称不能为空");
                }

                if (updateParent)
                {
                    if (parentId == folderId)
                    {
                        throw new MediaServiceException("不能将文件夹设为自己的子文件夹");
                    }

                    if (parentId is not null)
                    {
                        var ancestors = await LoadAncestorIdsAsync(database, parentId.Value, token).ConfigureAwait(false);
                        if (ancestors is null)
                        {
                            throw new MediaServiceException($"父文件夹 id={parentId.Value} 不存在");
                        }

                        if (ancestors.Contains(folderId))
                        {
                            throw new MediaServiceException("不能将文件夹移动到自己的子文件夹");
                        }
                    }

                    folder.ParentId = parentId;
                }

                folder.UpdatedAt = _timeProvider.GetUtcNow();
                return ToFolderDto(folder);
            },
            cancellationToken);

    public async Task DeleteFolderAsync(
        long folderId,
        bool deleteContents,
        CancellationToken cancellationToken = default)
    {
        var managedFiles = await writes.ExecuteAsync(
            async (database, token) =>
            {
                if (!await database.MediaFolders.AnyAsync(folder => folder.Id == folderId, token).ConfigureAwait(false))
                {
                    throw new MediaServiceException($"文件夹 id={folderId} 不存在", isNotFound: true);
                }

                var folders = await database.MediaFolders.ToListAsync(token).ConfigureAwait(false);
                var subtree = CollectSubtree(folderId, folders);
                var sources = await database.MediaSources
                    .Where(source => source.FolderId != null && subtree.Contains(source.FolderId.Value))
                    .ToListAsync(token).ConfigureAwait(false);
                var files = deleteContents
                    ? sources.Select(source => ManagedFileOrNull(source.UploadedFile)).Where(path => path is not null).Cast<string>().ToArray()
                    : [];
                if (deleteContents)
                {
                    database.MediaSources.RemoveRange(sources);
                }
                else
                {
                    foreach (var source in sources)
                    {
                        source.FolderId = null;
                    }
                }

                var parentById = folders.ToDictionary(folder => folder.Id, folder => folder.ParentId);
                foreach (var folder in folders
                             .Where(folder => subtree.Contains(folder.Id))
                             .OrderByDescending(folder => GetDepth(folder.Id, parentById)))
                {
                    database.MediaFolders.Remove(folder);
                }

                return files;
            },
            cancellationToken).ConfigureAwait(false);
        DeleteManagedFiles(managedFiles);
    }

    public async Task<IReadOnlyList<MediaSourceDto>> ListSourcesAsync(
        string? sourceType,
        long? folderId,
        CancellationToken cancellationToken = default)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var query = database.MediaSources.AsNoTracking().Include(source => source.PptResources).AsQueryable();
        if (!string.IsNullOrWhiteSpace(sourceType))
        {
            var parsedType = ParseSourceType(sourceType);
            query = query.Where(source => source.SourceType == parsedType);
        }

        if (folderId is not null)
        {
            query = folderId < 0
                ? query.Where(source => source.FolderId == null)
                : query.Where(source => source.FolderId == folderId);
        }

        var sources = await query.OrderBy(source => source.Id).ToListAsync(cancellationToken).ConfigureAwait(false);
        return sources.Select(ToSourceDto).ToArray();
    }

    public async Task<MediaSourceDto> AddUploadedAsync(
        Stream content,
        string fileName,
        string? contentType,
        string? displayName,
        string? sourceType,
        long? folderId,
        bool isTemporary,
        bool preheatEnabled,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(content);
        var safeFileName = Path.GetFileName(fileName);
        if (safeFileName.Length == 0)
        {
            safeFileName = "未命名文件";
        }

        var parsedType = string.IsNullOrWhiteSpace(sourceType)
            ? DetectSourceType(safeFileName)
            : ParseSourceType(sourceType);
        Directory.CreateDirectory(_uploadRoot);
        var destination = Path.Combine(
            _uploadRoot,
            $"{Guid.NewGuid():N}{Path.GetExtension(safeFileName).ToLowerInvariant()}");
        string digest;
        long length;
        try
        {
            await using (var target = new FileStream(
                             destination,
                             FileMode.CreateNew,
                             FileAccess.Write,
                             FileShare.None,
                             81920,
                             FileOptions.Asynchronous | FileOptions.SequentialScan))
            {
                using var hasher = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
                var buffer = new byte[81920];
                length = 0;
                while (true)
                {
                    var read = await content.ReadAsync(buffer, cancellationToken).ConfigureAwait(false);
                    if (read == 0)
                    {
                        break;
                    }

                    await target.WriteAsync(buffer.AsMemory(0, read), cancellationToken).ConfigureAwait(false);
                    hasher.AppendData(buffer, 0, read);
                    length += read;
                }

                digest = Convert.ToHexString(hasher.GetHashAndReset()).ToLowerInvariant();
            }

            return await CreateFileSourceAsync(
                destination,
                destination,
                safeFileName,
                contentType,
                displayName,
                parsedType,
                folderId,
                isTemporary,
                preheatEnabled,
                length,
                digest,
                cancellationToken).ConfigureAwait(false);
        }
        catch
        {
            TryDeleteFile(destination);
            throw;
        }
    }

    public async Task<MediaSourceDto> AddLocalAsync(
        string path,
        string? displayName,
        string? sourceType,
        long? folderId,
        bool preheatEnabled,
        CancellationToken cancellationToken = default)
    {
        var resolved = ResolveAllowedFile(path);
        var parsedType = string.IsNullOrWhiteSpace(sourceType)
            ? DetectSourceType(resolved)
            : ParseSourceType(sourceType);
        var info = new FileInfo(resolved);
        var digest = await ComputeDigestAsync(resolved, cancellationToken).ConfigureAwait(false);
        return await CreateFileSourceAsync(
            resolved,
            string.Empty,
            info.Name,
            null,
            displayName,
            parsedType,
            folderId,
            false,
            preheatEnabled,
            info.Length,
            digest,
            cancellationToken).ConfigureAwait(false);
    }

    public Task<MediaSourceDto> AddWebAsync(
        string url,
        string? displayName,
        long? folderId,
        bool preheatEnabled,
        CancellationToken cancellationToken = default)
    {
        var normalizedUrl = NormalizeWebUrl(url);
        if (normalizedUrl.Length == 0)
        {
            throw new MediaServiceException("URL 不能为空");
        }

        return writes.ExecuteAsync(
            async (database, token) =>
            {
                var effectiveFolder = await OptionalFolderIdAsync(database, folderId, token).ConfigureAwait(false);
                var source = new MediaSource
                {
                    SourceType = MediaSourceType.Web,
                    Name = string.IsNullOrWhiteSpace(displayName) ? normalizedUrl[..Math.Min(80, normalizedUrl.Length)] : ValidateName(displayName, "显示名称不能为空"),
                    Uri = normalizedUrl,
                    IsAvailable = true,
                    MimeType = "text/html",
                    FolderId = effectiveFolder,
                    KeepAlive = preheatEnabled,
                    SourceRevision = 1,
                    CreatedAt = _timeProvider.GetUtcNow(),
                };
                database.MediaSources.Add(source);
                await database.SaveChangesAsync(token).ConfigureAwait(false);
                return ToSourceDto(source);
            },
            cancellationToken);
    }

    public Task<MediaSourceDto> MoveSourceAsync(
        long sourceId,
        long? folderId,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (database, token) =>
            {
                var source = await FindSourceAsync(database, sourceId, token).ConfigureAwait(false);
                if (folderId is not null && !await database.MediaFolders.AnyAsync(
                        folder => folder.Id == folderId.Value,
                        token).ConfigureAwait(false))
                {
                    throw new MediaServiceException($"文件夹 id={folderId.Value} 不存在", isNotFound: true);
                }

                source.FolderId = folderId;
                return ToSourceDto(source);
            },
            cancellationToken);

    public Task<MediaSourceDto> UpdateSourceAsync(
        long sourceId,
        string? name,
        string? uri,
        bool? preheatEnabled,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (database, token) =>
            {
                var source = await FindSourceAsync(database, sourceId, token).ConfigureAwait(false);
                if (name is not null)
                {
                    source.Name = ValidateName(name, "显示名称不能为空");
                }

                if (uri is not null && source.SourceType == MediaSourceType.Web)
                {
                    var normalized = NormalizeWebUrl(uri);
                    if (normalized.Length == 0)
                    {
                        throw new MediaServiceException("网页 URL 不能为空");
                    }

                    source.Uri = normalized;
                    source.SourceRevision = checked(source.SourceRevision + 1);
                }

                if (preheatEnabled is not null)
                {
                    source.KeepAlive = preheatEnabled.Value;
                }

                return ToSourceDto(source);
            },
            cancellationToken);

    public async Task DeleteSourceAsync(long sourceId, CancellationToken cancellationToken = default)
    {
        var managedFile = await writes.ExecuteAsync(
            async (database, token) =>
            {
                var source = await FindSourceAsync(database, sourceId, token).ConfigureAwait(false);
                var path = ManagedFileOrNull(source.UploadedFile);
                database.MediaSources.Remove(source);
                return path;
            },
            cancellationToken).ConfigureAwait(false);
        if (managedFile is not null)
        {
            TryDeleteFile(managedFile);
        }
    }

    public async Task<MediaFileResult> GetDownloadAsync(long sourceId, CancellationToken cancellationToken = default)
    {
        var source = await GetSourceAsync(sourceId, cancellationToken).ConfigureAwait(false);
        var path = ResolveAllowedFile(source.Uri);
        return new MediaFileResult(
            path,
            source.MimeType.Length == 0 ? GuessMimeType(path) : source.MimeType,
            source.OriginalFilename.Length == 0 ? Path.GetFileName(path) : source.OriginalFilename,
            Download: true);
    }

    public async Task<MediaFileResult> GetPreviewAsync(long sourceId, CancellationToken cancellationToken = default)
    {
        var source = await GetSourceAsync(sourceId, cancellationToken).ConfigureAwait(false);
        if (source.SourceType is not (MediaSourceType.Image or MediaSourceType.Video))
        {
            throw new MediaServiceException("仅图片和视频源支持文件预览");
        }

        var path = ResolveAllowedFile(source.Uri);
        return new MediaFileResult(
            path,
            source.MimeType.Length == 0 ? GuessMimeType(path) : source.MimeType,
            Path.GetFileName(path),
            Download: false);
    }

    private Task<MediaSourceDto> CreateFileSourceAsync(
        string uri,
        string uploadedFile,
        string originalFilename,
        string? contentType,
        string? displayName,
        MediaSourceType sourceType,
        long? folderId,
        bool isTemporary,
        bool preheatEnabled,
        long fileSize,
        string digest,
        CancellationToken cancellationToken) =>
        writes.ExecuteAsync(
            async (database, token) =>
            {
                var effectiveFolder = await OptionalFolderIdAsync(database, folderId, token).ConfigureAwait(false);
                var source = new MediaSource
                {
                    SourceType = sourceType,
                    Name = string.IsNullOrWhiteSpace(displayName) ? Path.GetFileNameWithoutExtension(originalFilename) : ValidateName(displayName, "显示名称不能为空"),
                    Uri = uri,
                    UploadedFile = uploadedFile,
                    IsAvailable = true,
                    FolderId = effectiveFolder,
                    OriginalFilename = originalFilename,
                    FileSize = fileSize,
                    MimeType = string.IsNullOrWhiteSpace(contentType) ? GuessMimeType(originalFilename) : contentType,
                    IsTemporary = isTemporary,
                    ExpiresAt = isTemporary ? _timeProvider.GetUtcNow().AddDays(1) : null,
                    KeepAlive = preheatEnabled,
                    SourceRevision = 1,
                    ContentDigest = digest,
                    CreatedAt = _timeProvider.GetUtcNow(),
                };
                database.MediaSources.Add(source);
                await database.SaveChangesAsync(token).ConfigureAwait(false);
                return ToSourceDto(source);
            },
            cancellationToken);

}

public sealed record MediaFileResult(string Path, string ContentType, string FileName, bool Download);

public sealed class MediaServiceException(string message, bool isNotFound = false) : Exception(message)
{
    public bool IsNotFound { get; } = isNotFound;
}
