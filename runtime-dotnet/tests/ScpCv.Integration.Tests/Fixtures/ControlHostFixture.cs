using Microsoft.Data.Sqlite;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Configuration;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Runtime;
using ScpCv.Integration.Tests.Fakes;

namespace ScpCv.Integration.Tests.Fixtures;

public sealed class ControlHostFixture : IAsyncDisposable
{
    private ControlHostFixture(
        string temporaryRoot,
        DeterministicTimeProvider timeProvider,
        ControlDbContextFactory database,
        WriteCoordinator writes)
    {
        TemporaryRoot = temporaryRoot;
        TimeProvider = timeProvider;
        Database = database;
        Writes = writes;
        Commands = new CommandRepository(writes, timeProvider);
        RuntimeAuthority = new RuntimeAuthorityRepository(database, writes, timeProvider);
    }

    public string TemporaryRoot { get; }
    public DeterministicTimeProvider TimeProvider { get; }
    public ControlDbContextFactory Database { get; }
    public WriteCoordinator Writes { get; }
    public CommandRepository Commands { get; }
    public RuntimeAuthorityRepository RuntimeAuthority { get; }
    public FakeOfficeHost Office { get; } = new();
    public FakeDeviceAdapter Devices { get; } = new();

    public static async Task<ControlHostFixture> CreateAsync()
    {
        var root = Path.Combine(Path.GetTempPath(), "scp-cv-integration", Guid.NewGuid().ToString("N"));
        var time = new DeterministicTimeProvider(new DateTimeOffset(2026, 9, 8, 0, 0, 0, TimeSpan.Zero));
        var database = new ControlDbContextFactory(new DataRootOptions { RootPath = root }, root);
        await new DatabaseInitializer(database, time).InitializeAsync();
        return new ControlHostFixture(root, time, database, new WriteCoordinator(database));
    }

    public ValueTask DisposeAsync()
    {
        Writes.Dispose();
        SqliteConnection.ClearAllPools();
        var fullRoot = Path.GetFullPath(TemporaryRoot);
        var expectedParent = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "scp-cv-integration"));
        if (!string.Equals(Path.GetDirectoryName(fullRoot), expectedParent, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("拒绝清理测试根目录之外的路径。");
        }

        if (Directory.Exists(fullRoot))
        {
            Directory.Delete(fullRoot, recursive: true);
        }

        GC.SuppressFinalize(this);
        return ValueTask.CompletedTask;
    }
}
