using Microsoft.EntityFrameworkCore;

namespace ScpCv.Infrastructure.Persistence;

public sealed class WriteCoordinator(IDbContextFactory<ControlDbContext> contextFactory) : IDisposable
{
    private readonly SemaphoreSlim _writeGate = new(1, 1);

    public async Task<TResult> ExecuteAsync<TResult>(
        Func<ControlDbContext, CancellationToken, Task<TResult>> operation,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(operation);
        await _writeGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            await using var context = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
            await using var transaction = await context.Database.BeginTransactionAsync(cancellationToken).ConfigureAwait(false);
            var result = await operation(context, cancellationToken).ConfigureAwait(false);
            await context.SaveChangesAsync(cancellationToken).ConfigureAwait(false);
            await transaction.CommitAsync(cancellationToken).ConfigureAwait(false);
            return result;
        }
        finally
        {
            _writeGate.Release();
        }
    }

    public async Task ExecuteAsync(
        Func<ControlDbContext, CancellationToken, Task> operation,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(operation);
        await ExecuteAsync(
                async (context, token) =>
                {
                    await operation(context, token).ConfigureAwait(false);
                    return true;
                },
                cancellationToken)
            .ConfigureAwait(false);
    }

    public void Dispose()
    {
        _writeGate.Dispose();
        GC.SuppressFinalize(this);
    }
}
