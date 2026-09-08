using System.Data.Common;
using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;

namespace ScpCv.Infrastructure.Persistence;

public sealed class DatabaseInitializer(
    ControlDbContextFactory contextFactory,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;

    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(contextFactory.Layout.RootPath);

        await ValidateExistingDatabaseAsync(cancellationToken).ConfigureAwait(false);
        await using (var migrationContext = contextFactory.CreateDbContext())
        {
            await migrationContext.Database.MigrateAsync(cancellationToken).ConfigureAwait(false);
        }

        await ConfigureAndSeedAsync(cancellationToken).ConfigureAwait(false);
    }

    private async Task ValidateExistingDatabaseAsync(CancellationToken cancellationToken)
    {
        var databasePath = contextFactory.Layout.DatabasePath;
        if (!File.Exists(databasePath) || new FileInfo(databasePath).Length == 0)
        {
            return;
        }

        await using var context = contextFactory.CreateDbContext();
        await context.Database.OpenConnectionAsync(cancellationToken).ConfigureAwait(false);
        var tableNames = await ReadTableNamesAsync(context.Database.GetDbConnection(), cancellationToken)
            .ConfigureAwait(false);
        var applicationTables = tableNames
            .Where(name => !string.Equals(name, "sqlite_sequence", StringComparison.Ordinal))
            .ToArray();
        if (applicationTables.Length == 0)
        {
            return;
        }

        if (!applicationTables.Contains("__EFMigrationsHistory", StringComparer.Ordinal))
        {
            throw IncompatibleDatabase("缺少 EF Core schema 历史表");
        }

        var appliedMigrations = (await context.Database.GetAppliedMigrationsAsync(cancellationToken)
                .ConfigureAwait(false))
            .ToArray();
        var knownMigrations = context.Database.GetMigrations().ToHashSet(StringComparer.Ordinal);
        var unknownMigrations = appliedMigrations.Where(migration => !knownMigrations.Contains(migration)).ToArray();
        if (unknownMigrations.Length > 0)
        {
            throw IncompatibleDatabase($"包含未知 schema 版本：{string.Join(", ", unknownMigrations)}");
        }

        if (appliedMigrations.Length == 0 && applicationTables.Length > 1)
        {
            throw IncompatibleDatabase("schema 历史为空但数据库已包含业务表");
        }
    }

    private async Task ConfigureAndSeedAsync(CancellationToken cancellationToken)
    {
        await using var context = contextFactory.CreateDbContext();
        await context.Database.OpenConnectionAsync(cancellationToken).ConfigureAwait(false);
        await ExecutePragmaAsync(context.Database.GetDbConnection(), "PRAGMA journal_mode=WAL;", cancellationToken)
            .ConfigureAwait(false);
        await ExecutePragmaAsync(
                context.Database.GetDbConnection(),
                $"PRAGMA busy_timeout={contextFactory.Layout.BusyTimeoutMilliseconds};",
                cancellationToken)
            .ConfigureAwait(false);

        var now = _timeProvider.GetUtcNow();
        if (!await context.RuntimeStates.AnyAsync(cancellationToken).ConfigureAwait(false))
        {
            context.RuntimeStates.Add(new RuntimeState { UpdatedAt = now });
        }

        if (!await context.BackgroundAudioStates.AnyAsync(cancellationToken).ConfigureAwait(false))
        {
            context.BackgroundAudioStates.Add(new BackgroundAudioState { UpdatedAt = now });
        }

        if (!await context.RuntimeGroupControls.AnyAsync(cancellationToken).ConfigureAwait(false))
        {
            context.RuntimeGroupControls.Add(new RuntimeGroupControl
            {
                State = RuntimeGroupState.Stopped,
                StopReason = "initialization",
            });
        }

        var existingWindows = await context.PlaybackSessions
            .Select(session => session.WindowId)
            .ToHashSetAsync(cancellationToken)
            .ConfigureAwait(false);
        foreach (var windowId in Enumerable.Range(1, 4).Where(windowId => !existingWindows.Contains(windowId)))
        {
            context.PlaybackSessions.Add(new PlaybackSession
            {
                WindowId = windowId,
                LastUpdatedAt = now,
            });
        }

        await context.SaveChangesAsync(cancellationToken).ConfigureAwait(false);
    }

    private static async Task<IReadOnlyList<string>> ReadTableNamesAsync(
        DbConnection connection,
        CancellationToken cancellationToken)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = "SELECT name FROM sqlite_master WHERE type = 'table';";
        var names = new List<string>();
        await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
        while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
        {
            names.Add(reader.GetString(0));
        }

        return names;
    }

    private static async Task ExecutePragmaAsync(
        DbConnection connection,
        string commandText,
        CancellationToken cancellationToken)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = commandText;
        await command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
    }

    private static InvalidOperationException IncompatibleDatabase(string reason) =>
        new($"已有 control.db 与当前运行时 schema 不兼容（{reason}）。请选择新的 DataRoot；初始化器不会删除或覆盖该文件。");
}
