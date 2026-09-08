using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace ScpCv.Infrastructure.Persistence;

public sealed class ControlDbContextDesignFactory : IDesignTimeDbContextFactory<ControlDbContext>
{
    public ControlDbContext CreateDbContext(string[] args)
    {
        var databasePath = Path.Combine(
            Directory.GetCurrentDirectory(),
            "data",
            "dotnet",
            "control.design.db");
        var options = new DbContextOptionsBuilder<ControlDbContext>()
            .UseSqlite($"Data Source={databasePath}")
            .Options;

        return new ControlDbContext(options);
    }
}
