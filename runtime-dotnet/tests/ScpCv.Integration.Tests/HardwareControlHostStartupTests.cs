using System.Diagnostics;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using Microsoft.Data.Sqlite;

namespace ScpCv.Integration.Tests;

public sealed class HardwareControlHostStartupTests
{
    [Fact]
    public async Task HardwareControlHostReachesReadyEndpointWithoutDependencyDeadlock()
    {
        if (!OperatingSystem.IsWindows()) return;

        var dataRoot = Path.Combine(
            Path.GetTempPath(),
            "scp-cv-hardware-startup-tests",
            Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dataRoot);
        var port = ReserveLoopbackPort();
        var baseAddress = new Uri($"http://127.0.0.1:{port}");
        var assemblyPath = typeof(Program).Assembly.Location;
        using var process = Process.Start(new ProcessStartInfo
        {
            FileName = "dotnet",
            Arguments = $"\"{assemblyPath}\" --SafetyMode=Hardware --urls={baseAddress} --DataRoot=\"{dataRoot}\"",
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        }) ?? throw new InvalidOperationException("无法启动 Hardware ControlHost 测试进程。");

        try
        {
            using var client = new HttpClient { BaseAddress = baseAddress };
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            Exception? lastError = null;
            while (!deadline.IsCancellationRequested)
            {
                try
                {
                    using var response = await client.GetAsync("/health/ready", deadline.Token);
                    Assert.Equal(HttpStatusCode.OK, response.StatusCode);
                    return;
                }
                catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException)
                {
                    lastError = exception;
                    await Task.Delay(100, CancellationToken.None);
                }
            }

            if (!process.HasExited) process.Kill(entireProcessTree: true);
            await process.WaitForExitAsync();
            var output = await process.StandardOutput.ReadToEndAsync();
            var error = await process.StandardError.ReadToEndAsync();
            throw new Xunit.Sdk.XunitException(
                $"Hardware ControlHost 未在 10 秒内就绪。最后错误：{lastError?.Message}\nstdout:\n{output}\nstderr:\n{error}");
        }
        finally
        {
            if (!process.HasExited) process.Kill(entireProcessTree: true);
            await process.WaitForExitAsync();
            SqliteConnection.ClearAllPools();
            // 被终止的子进程可能在退出后仍短暂持有 SQLite 文件句柄；清理按重试处理，不掩盖启动断言。
            for (var attempt = 0; attempt < 20 && Directory.Exists(dataRoot); attempt++)
            {
                try
                {
                    Directory.Delete(dataRoot, recursive: true);
                }
                catch (IOException) when (attempt < 19)
                {
                    await Task.Delay(250);
                }
            }
        }
    }

    private static int ReserveLoopbackPort()
    {
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        try
        {
            return ((IPEndPoint)listener.LocalEndpoint).Port;
        }
        finally
        {
            listener.Stop();
        }
    }
}
