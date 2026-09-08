using Microsoft.Data.Sqlite;
using ScpCv.Infrastructure.Configuration;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Integration.Tests;

public sealed class DevelopmentDataTests
{
    [Fact]
    public async Task FreshDirectoryInitializesIdempotently()
    {
        var root = Path.Combine(Path.GetTempPath(), "scp-cv-dev", Guid.NewGuid().ToString("N"));
        try
        {
            var factory = new ControlDbContextFactory(new DataRootOptions { RootPath = root }, root);
            var initializer = new DatabaseInitializer(factory);
            await initializer.InitializeAsync();
            await initializer.InitializeAsync();
            Assert.True(File.Exists(factory.Layout.DatabasePath));
        }
        finally
        {
            SqliteConnection.ClearAllPools();
            if (Directory.Exists(root))
            {
                Directory.Delete(root, true);
            }
        }
    }
}
