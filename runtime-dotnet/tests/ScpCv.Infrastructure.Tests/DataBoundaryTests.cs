using ScpCv.Infrastructure.Configuration;

namespace ScpCv.Infrastructure.Tests;

public sealed class DataBoundaryTests
{
    [Fact]
    public void DataRootCannotAliasLegacyDatabase()
    {
        var contentRoot = Path.Combine(Path.GetTempPath(), "scp-cv-boundary", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(contentRoot);
        try
        {
            var options = new DataRootOptions { RootPath = contentRoot, DatabaseFileName = "db.sqlite3" };
            Assert.Throws<InvalidOperationException>(() => options.Resolve(contentRoot));
        }
        finally { Directory.Delete(contentRoot, true); }
    }
}
