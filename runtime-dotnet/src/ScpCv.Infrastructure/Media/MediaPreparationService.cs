using System.Security.Cryptography;
using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Configuration;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Media;

public sealed record PrepareMediaRequest(
    long SourceId,
    long SourceRevision,
    string SourceDigest,
    PreparationJobKind Kind,
    int Priority,
    DateTimeOffset? Deadline,
    string RecipeVersion);

public sealed class MediaPreparationService(
    IDbContextFactory<ControlDbContext> contextFactory,
    WriteCoordinator writes,
    DataRootOptions dataRootOptions,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;

    public Task<MediaPreparationJob> EnqueueAsync(
        PrepareMediaRequest request,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(request.SourceDigest);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.RecipeVersion);
        return writes.ExecuteAsync(
            async (database, token) =>
            {
                var source = await database.MediaSources.SingleOrDefaultAsync(item => item.Id == request.SourceId, token)
                    .ConfigureAwait(false) ?? throw new KeyNotFoundException("媒体源不存在。");
                if (source.SourceRevision != request.SourceRevision ||
                    !string.Equals(source.ContentDigest, request.SourceDigest, StringComparison.Ordinal))
                    throw new InvalidOperationException("媒体源版本或摘要已变化，拒绝创建准备作业。");

                var existing = await database.MediaPreparationJobs.SingleOrDefaultAsync(item =>
                        item.SourceId == request.SourceId &&
                        item.SourceDigest == request.SourceDigest &&
                        item.Kind == request.Kind &&
                        item.RecipeVersion == request.RecipeVersion, token)
                    .ConfigureAwait(false);
                if (existing is not null) return existing;

                var job = new MediaPreparationJob
                {
                    JobId = Guid.NewGuid(),
                    SourceId = request.SourceId,
                    SourceRevision = request.SourceRevision,
                    SourceDigest = request.SourceDigest,
                    Kind = request.Kind,
                    Priority = request.Priority,
                    Deadline = request.Deadline,
                    RecipeVersion = request.RecipeVersion,
                };
                database.MediaPreparationJobs.Add(job);
                return job;
            },
            cancellationToken);
    }

    public Task<MediaPreparationJob?> ClaimNextAsync(CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (database, token) =>
            {
                var showing = await database.PlaybackSessions.AnyAsync(
                    item => item.PlaybackState == PlaybackState.Playing,
                    token).ConfigureAwait(false);
                if (showing) return null;
                var now = _timeProvider.GetUtcNow();
                var job = await database.MediaPreparationJobs
                    .Where(item => item.Status == OperationStatus.Queued &&
                                   (item.Deadline == null || item.Deadline > now))
                    .OrderByDescending(item => item.Priority)
                    .ThenBy(item => item.Id)
                    .FirstOrDefaultAsync(token).ConfigureAwait(false);
                if (job is null) return null;
                job.Status = OperationStatus.Running;
                return job;
            },
            cancellationToken);

    public async Task<ArtifactManifest> PublishArtifactAsync(
        Guid jobId,
        string stagingPath,
        string relativePath,
        long pageCount,
        CancellationToken cancellationToken = default)
    {
        var layout = dataRootOptions.Resolve(AppContext.BaseDirectory);
        var stagingRoot = Path.Combine(layout.RootPath, "cache", "staging");
        var cacheRoot = Path.Combine(layout.RootPath, "cache", "artifacts");
        var source = Path.GetFullPath(stagingPath);
        var normalizedRelative = NormalizeRelativePath(relativePath);
        if (!IsWithin(source, stagingRoot)) throw new InvalidOperationException("制品暂存路径越界。");

        await using var context = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var job = await context.MediaPreparationJobs.Include(item => item.Source)
            .SingleOrDefaultAsync(item => item.JobId == jobId, cancellationToken).ConfigureAwait(false)
            ?? throw new KeyNotFoundException("准备作业不存在。");
        if (job.Status != OperationStatus.Running) throw new InvalidOperationException("准备作业不是 running 状态。");
        if (job.Source.SourceRevision != job.SourceRevision ||
            !string.Equals(job.Source.ContentDigest, job.SourceDigest, StringComparison.Ordinal))
            throw new InvalidOperationException("源版本已变化，隔离并丢弃旧制品。");
        if (!File.Exists(source)) throw new FileNotFoundException("暂存制品不存在。", source);

        var destination = Path.Combine(
            cacheRoot,
            job.SourceId.ToString(System.Globalization.CultureInfo.InvariantCulture),
            SafePathSegment(job.SourceDigest),
            normalizedRelative);
        if (!IsWithin(destination, cacheRoot)) throw new InvalidOperationException("制品目标路径越界。");
        Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
        var sha256 = await ComputeSha256Async(source, cancellationToken).ConfigureAwait(false);
        File.Move(source, destination, overwrite: true);

        var manifest = await writes.ExecuteAsync(
                async (database, token) =>
                {
                    var currentJob = await database.MediaPreparationJobs.SingleAsync(item => item.JobId == jobId, token)
                        .ConfigureAwait(false);
                    var existing = await database.ArtifactManifests.SingleOrDefaultAsync(item =>
                            item.SourceId == currentJob.SourceId && item.SourceDigest == currentJob.SourceDigest &&
                            item.RecipeVersion == currentJob.RecipeVersion && item.RelativePath == normalizedRelative,
                            token).ConfigureAwait(false);
                    var candidate = existing ?? new ArtifactManifest
                    {
                        SourceId = currentJob.SourceId,
                        SourceDigest = currentJob.SourceDigest,
                        RecipeVersion = currentJob.RecipeVersion,
                        RelativePath = normalizedRelative,
                    };
                    if (existing is null) database.ArtifactManifests.Add(candidate);
                    candidate.Sha256 = sha256;
                    candidate.FileSize = new FileInfo(destination).Length;
                    candidate.PageCount = checked((int)Math.Max(0, pageCount));
                    candidate.Status = OperationStatus.Succeeded;
                    currentJob.Status = OperationStatus.Succeeded;
                    currentJob.ArtifactManifestJson = $"{{\"relative_path\":\"{normalizedRelative}\",\"sha256\":\"{sha256}\"}}";
                    return candidate;
                },
                cancellationToken)
            .ConfigureAwait(false);
        return manifest;
    }

    private static string NormalizeRelativePath(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        var normalized = path.Replace('/', Path.DirectorySeparatorChar).Replace('\\', Path.DirectorySeparatorChar);
        if (Path.IsPathRooted(normalized) || normalized.Split(Path.DirectorySeparatorChar).Any(part => part == ".."))
            throw new InvalidOperationException("制品相对路径越界。");
        return normalized.TrimStart(Path.DirectorySeparatorChar);
    }

    private static string SafePathSegment(string value)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var chars = value.Select(character => invalid.Contains(character) ? '_' : character).ToArray();
        return new string(chars);
    }

    private static bool IsWithin(string candidate, string root)
    {
        var fullCandidate = Path.GetFullPath(candidate).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        var fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        return fullCandidate.StartsWith(fullRoot, StringComparison.OrdinalIgnoreCase);
    }

    private static async Task<string> ComputeSha256Async(string path, CancellationToken cancellationToken)
    {
        await using var stream = File.OpenRead(path);
        var digest = await SHA256.HashDataAsync(stream, cancellationToken).ConfigureAwait(false);
        return Convert.ToHexString(digest).ToLowerInvariant();
    }
}
