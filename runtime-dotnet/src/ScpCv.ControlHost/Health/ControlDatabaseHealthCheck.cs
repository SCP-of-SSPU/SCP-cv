using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.ControlHost.Health;

public sealed class ControlDatabaseHealthCheck(ControlDbContextFactory contextFactory) : IHealthCheck
{
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            await using var database = contextFactory.CreateDbContext();
            if (!await database.Database.CanConnectAsync(cancellationToken).ConfigureAwait(false))
            {
                return HealthCheckResult.Unhealthy("Control database is unavailable.");
            }

            var group = await database.RuntimeGroupControls
                .AsNoTracking()
                .SingleAsync(cancellationToken)
                .ConfigureAwait(false);
            return HealthCheckResult.Healthy(
                "Control database is ready.",
                new Dictionary<string, object>
                {
                    ["group_state"] = group.State.ToString().ToLowerInvariant(),
                    ["group_epoch"] = group.GroupEpoch,
                });
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return HealthCheckResult.Unhealthy("Control database health check failed.", exception);
        }
    }
}
