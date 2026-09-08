using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Configuration;
using ScpCv.Infrastructure.Media;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Tests;

public sealed class MediaPreparationTests
{
    [Fact]
    public async Task PreparationJobsDeduplicateAndPublishArtifactAtomically()
    {
        var root = CreateTemporaryRoot();
        try
        {
            var factory = await CreateInitializedFactoryAsync(root);
            using var writes = new WriteCoordinator(factory);
            var source = await writes.ExecuteAsync((database, token) =>
            {
                var item = new MediaSource { Name = "deck", SourceType = MediaSourceType.Presentation, ContentDigest = "sha:a", SourceRevision = 1 };
                database.MediaSources.Add(item);
                return Task.FromResult(item);
            });
            var service = new MediaPreparationService(factory, writes, new DataRootOptions { RootPath = root });
            var request = new PrepareMediaRequest(source.Id, 1, "sha:a", PreparationJobKind.Pdf, 10, null, "recipe-1");

            var first = await service.EnqueueAsync(request);
            var duplicate = await service.EnqueueAsync(request);
            Assert.Equal(first.JobId, duplicate.JobId);
            var claimed = await service.ClaimNextAsync();
            Assert.Equal(first.JobId, claimed!.JobId);

            var staging = Path.Combine(root, "cache", "staging");
            Directory.CreateDirectory(staging);
            var staged = Path.Combine(staging, "page.pdf");
            await File.WriteAllTextAsync(staged, "pdf-bytes");
            var manifest = await service.PublishArtifactAsync(first.JobId, staged, "pages/page-1.pdf", 1);

            Assert.Equal(OperationStatus.Succeeded, manifest.Status);
            Assert.True(File.Exists(Path.Combine(root, "cache", "artifacts", "1", "sha_a", "pages", "page-1.pdf")));
            await using var context = factory.CreateDbContext();
            Assert.Equal(OperationStatus.Succeeded, await context.MediaPreparationJobs.Select(item => item.Status).SingleAsync());
        }
        finally { DeleteTemporaryRoot(root); }
    }

    [Fact]
    public async Task OldSourceDigestCannotPublishLateArtifact()
    {
        var root = CreateTemporaryRoot();
        try
        {
            var factory = await CreateInitializedFactoryAsync(root);
            using var writes = new WriteCoordinator(factory);
            var source = await writes.ExecuteAsync((database, token) =>
            {
                var item = new MediaSource { Name = "deck", SourceType = MediaSourceType.Presentation, ContentDigest = "sha:a", SourceRevision = 1 };
                database.MediaSources.Add(item);
                return Task.FromResult(item);
            });
            var service = new MediaPreparationService(factory, writes, new DataRootOptions { RootPath = root });
            var job = await service.EnqueueAsync(new PrepareMediaRequest(source.Id, 1, "sha:a", PreparationJobKind.Pdf, 1, null, "recipe-1"));
            await service.ClaimNextAsync();
            await writes.ExecuteAsync((database, token) =>
            {
                var entity = database.MediaSources.Single(item => item.Id == source.Id);
                entity.SourceRevision = 2;
                entity.ContentDigest = "sha:b";
                return Task.CompletedTask;
            });
            var staging = Path.Combine(root, "cache", "staging");
            Directory.CreateDirectory(staging);
            var staged = Path.Combine(staging, "late.pdf");
            await File.WriteAllTextAsync(staged, "late");

            await Assert.ThrowsAsync<InvalidOperationException>(() => service.PublishArtifactAsync(job.JobId, staged, "late.pdf", 1));
            Assert.True(File.Exists(staged));
        }
        finally { DeleteTemporaryRoot(root); }
    }

    private static async Task<ControlDbContextFactory> CreateInitializedFactoryAsync(string root)
    {
        var factory = new ControlDbContextFactory(new DataRootOptions { RootPath = root }, root);
        await new DatabaseInitializer(factory).InitializeAsync();
        return factory;
    }

    private static string CreateTemporaryRoot() => Path.Combine(Path.GetTempPath(), "scp-cv-prep", Guid.NewGuid().ToString("N"));

    private static void DeleteTemporaryRoot(string root)
    {
        SqliteConnection.ClearAllPools();
        if (Directory.Exists(root)) Directory.Delete(root, true);
    }
}
