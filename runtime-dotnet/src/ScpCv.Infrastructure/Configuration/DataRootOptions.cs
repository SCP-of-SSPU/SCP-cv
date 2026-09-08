namespace ScpCv.Infrastructure.Configuration;

public sealed class DataRootOptions
{
    public const string SectionName = "DataRoot";
    public const string RequiredDatabaseFileName = "control.db";

    public string RootPath { get; set; } = Path.Combine("data", "dotnet");
    public string DatabaseFileName { get; set; } = RequiredDatabaseFileName;
    public int BusyTimeoutMilliseconds { get; set; } = 5_000;

    public DataRootLayout Resolve(string contentRootPath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(contentRootPath);

        if (!string.Equals(DatabaseFileName, RequiredDatabaseFileName, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException($"新运行时数据库必须使用独立文件名 {RequiredDatabaseFileName}，不能接管旧数据库。");
        }

        if (BusyTimeoutMilliseconds <= 0)
        {
            throw new InvalidOperationException("SQLite busy timeout 必须大于零。");
        }

        var absoluteContentRoot = Path.GetFullPath(contentRootPath);
        var absoluteRoot = Path.GetFullPath(
            Path.IsPathRooted(RootPath)
                ? RootPath
                : Path.Combine(absoluteContentRoot, RootPath));
        var databasePath = Path.Combine(absoluteRoot, RequiredDatabaseFileName);
        var legacyPath = Path.Combine(absoluteContentRoot, "db.sqlite3");
        if (string.Equals(databasePath, legacyPath, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("新运行时数据库不能覆盖旧 Django db.sqlite3。");
        }

        return new DataRootLayout(absoluteRoot, databasePath, BusyTimeoutMilliseconds);
    }
}

public sealed record DataRootLayout(
    string RootPath,
    string DatabasePath,
    int BusyTimeoutMilliseconds);
