using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using ScpCv.Infrastructure.Configuration;

namespace ScpCv.Infrastructure.Persistence;

public sealed class ControlDbContextFactory : IDbContextFactory<ControlDbContext>
{
    private readonly string _connectionString;

    public ControlDbContextFactory(DataRootOptions options, string contentRootPath)
    {
        ArgumentNullException.ThrowIfNull(options);
        Layout = options.Resolve(contentRootPath);
        _connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = Layout.DatabasePath,
            Mode = SqliteOpenMode.ReadWriteCreate,
            ForeignKeys = true,
            DefaultTimeout = Math.Max(1, (int)Math.Ceiling(Layout.BusyTimeoutMilliseconds / 1_000d)),
        }.ToString();
    }

    public DataRootLayout Layout { get; }

    public ControlDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ControlDbContext>()
            .UseSqlite(_connectionString)
            .Options;
        return new ControlDbContext(options);
    }
}
