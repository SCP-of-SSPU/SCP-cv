using ScpCv.Contracts.Runtime;

namespace ScpCv.Integration.Tests;

public sealed class RuntimeStartGateTests
{
    [Fact]
    public async Task WorkerWaitsUntilSupervisorOpensStartGate()
    {
        var name = $"Local\\SCP-cv.tests.startgate.{Guid.NewGuid():N}";
        using var gate = new EventWaitHandle(false, EventResetMode.ManualReset, name);

        var waiting = RuntimeStartGate.WaitAsync(name, timeout: TimeSpan.FromSeconds(20));
        var finishedBeforeOpen = await Task.WhenAny(waiting, Task.Delay(750)) == waiting;

        Assert.False(finishedBeforeOpen, "启动门未打开前 Worker 不得继续连接。");
        gate.Set();
        await waiting.WaitAsync(TimeSpan.FromSeconds(5));
    }

    [Fact]
    public async Task StandaloneWorkerWithoutStartGateProceedsImmediately()
    {
        await RuntimeStartGate.WaitAsync(null, timeout: TimeSpan.FromSeconds(5));
    }
}
