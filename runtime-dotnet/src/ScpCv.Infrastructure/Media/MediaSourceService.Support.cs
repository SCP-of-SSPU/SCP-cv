using System.Security.Cryptography;
using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Media;

public sealed partial class MediaSourceService
{
    private async Task<MediaSource> GetSourceAsync(long sourceId, CancellationToken cancellationToken)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        return await database.MediaSources.AsNoTracking().SingleOrDefaultAsync(
                source => source.Id == sourceId,
                cancellationToken).ConfigureAwait(false)
            ?? throw new MediaServiceException($"媒体源 id={sourceId} 不存在", isNotFound: true);
    }

    private static async Task<MediaSource> FindSourceAsync(
        ControlDbContext database,
        long sourceId,
        CancellationToken cancellationToken) =>
        await database.MediaSources.Include(source => source.PptResources).SingleOrDefaultAsync(
                source => source.Id == sourceId,
                cancellationToken).ConfigureAwait(false)
            ?? throw new MediaServiceException($"媒体源 id={sourceId} 不存在", isNotFound: true);

    private static async Task<long?> OptionalFolderIdAsync(
        ControlDbContext database,
        long? folderId,
        CancellationToken cancellationToken)
    {
        if (folderId is null || folderId <= 0)
        {
            return null;
        }

        return await database.MediaFolders.AnyAsync(folder => folder.Id == folderId, cancellationToken).ConfigureAwait(false)
            ? folderId
            : null;
    }

    private static async Task<HashSet<long>?> LoadAncestorIdsAsync(
        ControlDbContext database,
        long folderId,
        CancellationToken cancellationToken)
    {
        var folders = await database.MediaFolders.AsNoTracking().ToDictionaryAsync(
            folder => folder.Id,
            folder => folder.ParentId,
            cancellationToken).ConfigureAwait(false);
        if (!folders.ContainsKey(folderId))
        {
            return null;
        }

        var ancestors = new HashSet<long>();
        long? current = folderId;
        while (current is not null && ancestors.Add(current.Value) && folders.TryGetValue(current.Value, out current))
        {
        }

        return ancestors;
    }

    private static HashSet<long> CollectSubtree(long rootId, IReadOnlyCollection<MediaFolder> folders)
    {
        var result = new HashSet<long> { rootId };
        var pending = new Queue<long>();
        pending.Enqueue(rootId);
        while (pending.TryDequeue(out var parentId))
        {
            foreach (var childId in folders.Where(folder => folder.ParentId == parentId).Select(folder => folder.Id))
            {
                if (result.Add(childId))
                {
                    pending.Enqueue(childId);
                }
            }
        }

        return result;
    }

    private static int GetDepth(long folderId, IReadOnlyDictionary<long, long?> parentById)
    {
        var depth = 0;
        var seen = new HashSet<long> { folderId };
        var current = parentById.GetValueOrDefault(folderId);
        while (current is not null && seen.Add(current.Value))
        {
            depth++;
            current = parentById.GetValueOrDefault(current.Value);
        }

        return depth;
    }

    private string ResolveAllowedFile(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            throw new MediaServiceException("源文件不存在，无法访问");
        }

        var resolved = Path.GetFullPath(path);
        if (!_allowedRoots.Any(root => IsWithinRoot(resolved, root)))
        {
            throw new MediaServiceException("媒体路径超出允许目录");
        }

        if (!File.Exists(resolved))
        {
            throw new MediaServiceException($"文件不存在：{resolved}");
        }

        return resolved;
    }

    private string? ManagedFileOrNull(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return null;
        }

        var resolved = Path.GetFullPath(path);
        return IsWithinRoot(resolved, _uploadRoot) ? resolved : null;
    }

    private static bool IsWithinRoot(string path, string root)
    {
        var relative = Path.GetRelativePath(root, path);
        return relative != ".." &&
            !relative.StartsWith($"..{Path.DirectorySeparatorChar}", StringComparison.Ordinal) &&
            !Path.IsPathRooted(relative);
    }

    private static string[] BuildAllowedRoots(ControlDbContextFactory factory, MediaStorageOptions options) =>
        options.AllowedLocalRoots
            .Where(root => !string.IsNullOrWhiteSpace(root))
            .Select(Path.GetFullPath)
            .Append(Path.GetFullPath(factory.Layout.RootPath))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToArray();

    private static string ValidateName(string name, string emptyMessage)
    {
        var normalized = name.Trim();
        if (normalized.Length == 0)
        {
            throw new MediaServiceException(emptyMessage);
        }

        if (normalized.Length > 255)
        {
            throw new MediaServiceException("名称过长（≤ 255 字符）");
        }

        return normalized;
    }

    private static MediaSourceType ParseSourceType(string value) => value.Trim().ToLowerInvariant() switch
    {
        "ppt" => MediaSourceType.Presentation,
        "video" => MediaSourceType.Video,
        "audio" => MediaSourceType.Audio,
        "image" => MediaSourceType.Image,
        "web" => MediaSourceType.Web,
        "custom_stream" => MediaSourceType.CustomStream,
        "rtsp_stream" => MediaSourceType.RtspStream,
        "srt_stream" => MediaSourceType.SrtStream,
        _ => throw new MediaServiceException($"无效的媒体类型：{value}"),
    };

    private static MediaSourceType DetectSourceType(string fileName) => Path.GetExtension(fileName).ToLowerInvariant() switch
    {
        ".pdf" or ".pptx" or ".pptm" or ".ppt" or ".potx" or ".potm" or ".pot" or ".ppsx" or ".ppsm" or ".pps" or ".odp" => MediaSourceType.Presentation,
        ".mp4" or ".mkv" or ".avi" or ".mov" or ".wmv" or ".flv" or ".webm" or ".m4v" => MediaSourceType.Video,
        ".mp3" or ".wav" or ".flac" or ".aac" or ".ogg" or ".wma" or ".m4a" => MediaSourceType.Audio,
        ".png" or ".jpg" or ".jpeg" or ".gif" or ".bmp" or ".webp" or ".svg" => MediaSourceType.Image,
        var extension => throw new MediaServiceException($"无法识别的文件类型：{extension}"),
    };

    private static string NormalizeWebUrl(string value)
    {
        var trimmed = value.Trim();
        if (trimmed.Length == 0)
        {
            return string.Empty;
        }

        if (trimmed.StartsWith("http://", StringComparison.OrdinalIgnoreCase) ||
            trimmed.StartsWith("https://", StringComparison.OrdinalIgnoreCase) ||
            trimmed.StartsWith("file://", StringComparison.OrdinalIgnoreCase) ||
            trimmed.StartsWith("about:", StringComparison.OrdinalIgnoreCase))
        {
            return trimmed;
        }

        return trimmed.Length > 2 && trimmed[1] == ':' ? $"file:///{trimmed}" : $"http://{trimmed}";
    }

    private static string GuessMimeType(string fileName) => Path.GetExtension(fileName).ToLowerInvariant() switch
    {
        ".pdf" => "application/pdf",
        ".ppt" or ".pps" or ".pot" => "application/vnd.ms-powerpoint",
        ".pptx" or ".ppsx" or ".potx" => "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".png" => "image/png",
        ".jpg" or ".jpeg" => "image/jpeg",
        ".gif" => "image/gif",
        ".svg" => "image/svg+xml",
        ".mp4" => "video/mp4",
        ".webm" => "video/webm",
        ".mp3" => "audio/mpeg",
        ".wav" => "audio/wav",
        _ => "application/octet-stream",
    };

    private static async Task<string> ComputeDigestAsync(string path, CancellationToken cancellationToken)
    {
        await using var stream = new FileStream(
            path,
            FileMode.Open,
            FileAccess.Read,
            FileShare.Read,
            81920,
            FileOptions.Asynchronous | FileOptions.SequentialScan);
        var hash = await SHA256.HashDataAsync(stream, cancellationToken).ConfigureAwait(false);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private static void DeleteManagedFiles(IEnumerable<string> paths)
    {
        foreach (var path in paths)
        {
            TryDeleteFile(path);
        }
    }

    private static void TryDeleteFile(string path)
    {
        try
        {
            File.Delete(path);
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }
}
