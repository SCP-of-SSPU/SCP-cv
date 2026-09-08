using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ScpCv.Infrastructure.Commands;

public sealed class CommandResultService(CommandRepository repository)
{
    public Task<CommandResultAcceptance> AcceptAsync(
        CompleteCommand result,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(result);
        var normalized = string.IsNullOrWhiteSpace(result.ResultHash)
            ? result with { ResultHash = ComputeFingerprint(result) }
            : result;
        return repository.CompleteAsync(normalized, cancellationToken);
    }

    public static string ComputeFingerprint(CompleteCommand result)
    {
        var payload = JsonSerializer.Serialize(new
        {
            result.CommandId,
            result.Status,
            result.ResultCode,
            result.ResultEvidenceJson,
        });
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(payload))).ToLowerInvariant();
    }
}
