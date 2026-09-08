using System.Collections.Concurrent;
using System.Windows.Threading;

namespace ScpCv.PowerPointHost.Sta;

public sealed class OfficeStaDispatcher : IDisposable
{
    private readonly Thread _thread;
    private readonly TaskCompletionSource _started = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly ConcurrentDictionary<Guid, Task<object?>> _operations = new();
    private Dispatcher? _dispatcher;
    private int _disposed;

    public OfficeStaDispatcher()
    {
        _thread = new Thread(Run)
        {
            IsBackground = true,
            Name = "SCP-cv PowerPoint STA",
        };
        _thread.SetApartmentState(ApartmentState.STA);
        _thread.Start();
    }

    public async Task<T> InvokeAsync<T>(
        Guid operationId,
        Func<CancellationToken, T> operation,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(operation);
        ObjectDisposedException.ThrowIf(Volatile.Read(ref _disposed) != 0, this);
        await _started.Task.WaitAsync(cancellationToken).ConfigureAwait(false);
        if (_operations.TryGetValue(operationId, out var existing))
        {
            return (T)(await existing.WaitAsync(cancellationToken).ConfigureAwait(false))!;
        }

        var completion = new TaskCompletionSource<object?>(TaskCreationOptions.RunContinuationsAsynchronously);
        if (!_operations.TryAdd(operationId, completion.Task))
        {
            return (T)(await _operations[operationId].WaitAsync(cancellationToken).ConfigureAwait(false))!;
        }

        _ = _dispatcher!.BeginInvoke(DispatcherPriority.Normal, new Action(() =>
        {
            try
            {
                // 取消只在 STA 真正出队前生效；一旦开始执行 COM，同步调用不可安全撤销。
                if (cancellationToken.IsCancellationRequested)
                {
                    completion.TrySetCanceled(cancellationToken);
                    return;
                }

                completion.TrySetResult(operation(cancellationToken));
            }
            catch (Exception exception)
            {
                completion.TrySetException(exception);
            }
            finally
            {
                // 保留完成结果，确保重复 operation_id 永不再次触发 COM 副作用。
                // 该缓存随 PowerPointHost 进程生命周期存在，避免跨进程持久化 COM 结果。
            }
        }));

        return (T)(await completion.Task.WaitAsync(cancellationToken).ConfigureAwait(false))!;
    }

    public void Dispose()
    {
        if (Interlocked.Exchange(ref _disposed, 1) == 0)
        {
            _dispatcher?.BeginInvokeShutdown(DispatcherPriority.Normal);
            if (_thread.IsAlive && !ReferenceEquals(Thread.CurrentThread, _thread))
            {
                _thread.Join(TimeSpan.FromSeconds(3));
            }

            _started.TrySetCanceled();
        }

        GC.SuppressFinalize(this);
    }

    private void Run()
    {
        _dispatcher = Dispatcher.CurrentDispatcher;
        _started.TrySetResult();
        Dispatcher.Run();
    }
}
