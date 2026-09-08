using ScpCv.Supervisor.Processes;

namespace ScpCv.Supervisor.Runtime;

public sealed class MediaMtxProcess(ProcessRegistry registry, HttpClient httpClient)
{
    public OwnedProcess? Owned { get; private set; }
    public void Start(string executable, string configPath)
    {
        if (Owned is not null && ProcessRegistry.StillOwns(Owned)) return;
        var process = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(executable, configPath) { UseShellExecute = false })
            ?? throw new InvalidOperationException("无法启动 MediaMTX");
        Owned = registry.Register("mediamtx", process);
    }

    public async Task<bool> IsHealthyAsync(Uri healthUri, CancellationToken cancellationToken = default)
    {
        try { using var response = await httpClient.GetAsync(healthUri, cancellationToken).ConfigureAwait(false); return response.IsSuccessStatusCode; }
        catch (HttpRequestException) { return false; }
    }
}
