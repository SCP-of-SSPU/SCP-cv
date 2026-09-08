using System.Diagnostics;
using System.Runtime.InteropServices;

namespace ScpCv.PowerPointHost.Ownership;

public sealed record OwnedOfficeProcessEvidence(int ProcessId, DateTimeOffset StartTime, long HostEpoch);

/// <summary>主机级唯一命名互斥锁与持续 Office 进程身份证据。</summary>
public sealed class PowerPointOwnershipGuard(string mutexName, long hostEpoch) : IDisposable
{
    private readonly Mutex _mutex = new(false, mutexName);
    private OwnedOfficeProcessEvidence? _evidence;
    private int _disposed;

    public bool TryAcquire(TimeSpan timeout)
    {
        ObjectDisposedException.ThrowIf(Volatile.Read(ref _disposed) != 0, this);
        try
        {
            return _mutex.WaitOne(timeout);
        }
        catch (AbandonedMutexException)
        {
            // Abandoned 只代表锁所有者消失，不能直接证明旧 Office 已退出；调用方仍须核验进程。
            return true;
        }
    }

    public OwnedOfficeProcessEvidence RegisterOwnedProcess(Process process)
    {
        ArgumentNullException.ThrowIfNull(process);
        if (!process.HasExited)
        {
            process.Refresh();
        }

        _evidence = new OwnedOfficeProcessEvidence(
            process.Id,
            new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero),
            hostEpoch);
        return _evidence;
    }

    public bool StillOwnsProcess(out Process? process)
    {
        process = null;
        var evidence = _evidence;
        if (evidence is null)
        {
            return false;
        }

        try
        {
            process = Process.GetProcessById(evidence.ProcessId);
            var currentStart = new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero);
            if (currentStart != evidence.StartTime || process.HasExited)
            {
                process.Dispose();
                process = null;
                return false;
            }

            return true;
        }
        catch (ArgumentException)
        {
            return false;
        }
        catch (InvalidOperationException)
        {
            return false;
        }
    }

    public void Release()
    {
        if (Volatile.Read(ref _disposed) == 0)
        {
            ReleaseMutexSafely();
        }
    }

    public void Dispose()
    {
        if (Interlocked.Exchange(ref _disposed, 1) == 0)
        {
            // 先释放内核互斥体，再标记对象已释放；Release() 会刻意忽略已释放实例。
            ReleaseMutexSafely();
            _mutex.Dispose();
        }

        GC.SuppressFinalize(this);
    }

    private void ReleaseMutexSafely()
    {
        try { _mutex.ReleaseMutex(); } catch (ApplicationException) { }
    }
}
