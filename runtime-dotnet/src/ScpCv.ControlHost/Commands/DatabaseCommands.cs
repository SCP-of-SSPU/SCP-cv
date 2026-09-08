using Microsoft.EntityFrameworkCore;
using ScpCv.Infrastructure.Auth;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.ControlHost.Commands;

public sealed class DatabaseCommands(DatabaseInitializer initializer, DevelopmentAccountSeeder seeder, ControlDbContextFactory database)
{
    public async Task InitAsync(CancellationToken cancellationToken = default) => await initializer.InitializeAsync(cancellationToken).ConfigureAwait(false);
    public async Task SeedDevelopmentAsync(CancellationToken cancellationToken = default) => await seeder.SeedAsync(cancellationToken).ConfigureAwait(false);
    public async Task<IReadOnlyList<string>> StatusAsync(CancellationToken cancellationToken = default)
    {
        await using var context = database.CreateDbContext();
        return (await context.Database.GetAppliedMigrationsAsync(cancellationToken).ConfigureAwait(false)).ToArray();
    }
}
