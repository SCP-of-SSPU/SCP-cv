using System.Text.Json;
using ScpCv.Contracts.Ipc;

namespace ScpCv.Contracts.Tests;

public sealed class IpcContractTests
{
    [Fact]
    public void FrameUsesVersionOneAndFixedSnakeCaseEnvelope()
    {
        var messageId = Guid.Parse("e4f7b101-01cd-4b81-a818-b568b03555c1");
        var instanceId = Guid.Parse("9e1d0be3-017a-422d-953a-e97f4eb5b1fe");
        var frame = new IpcFrameDto
        {
            MessageType = "ClaimRequest",
            MessageId = messageId,
            InstanceId = instanceId,
            OwnerEpoch = 12,
            Target = new IpcTargetDto { Kind = "display", Id = 1 },
            Payload = JsonSerializer.SerializeToElement(new { }),
        };

        var json = JsonSerializer.SerializeToElement(frame);

        Assert.Equal(IpcProtocol.Version, json.GetProperty("protocol_version").GetInt32());
        Assert.Equal("ClaimRequest", json.GetProperty("message_type").GetString());
        Assert.Equal(messageId, json.GetProperty("message_id").GetGuid());
        Assert.Equal(JsonValueKind.Null, json.GetProperty("correlation_id").ValueKind);
        Assert.Equal(instanceId, json.GetProperty("instance_id").GetGuid());
        Assert.Equal(12, json.GetProperty("owner_epoch").GetInt64());
        Assert.Equal("display", json.GetProperty("target").GetProperty("kind").GetString());
        Assert.Equal(1, json.GetProperty("target").GetProperty("id").GetInt32());
        Assert.Equal(JsonValueKind.Object, json.GetProperty("payload").ValueKind);
        AssertPropertySet(
            json,
            "protocol_version",
            "message_type",
            "message_id",
            "correlation_id",
            "instance_id",
            "owner_epoch",
            "target",
            "payload");
    }

    [Fact]
    public void ProtocolLimitsMatchRuntimeIpcContract()
    {
        Assert.Equal(1, IpcProtocol.Version);
        Assert.Equal(1_048_576, IpcProtocol.MaximumFrameBytes);
        Assert.Equal(TimeSpan.FromSeconds(5), IpcProtocol.HandshakeTimeout);
        Assert.Equal(TimeSpan.FromSeconds(10), IpcProtocol.FrameReadTimeout);

        var contract = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Contracts", "runtime-ipc.md"));
        Assert.Contains("4字节little-endian无符号长度 + UTF-8 JSON", contract, StringComparison.Ordinal);
        Assert.Contains("1..1,048,576字节", contract, StringComparison.Ordinal);
        Assert.Contains("握手5秒截止", contract, StringComparison.Ordinal);
        Assert.Contains("帧读取10秒截止", contract, StringComparison.Ordinal);
    }

    [Fact]
    public void CommandLeaseContainsFencingAndLeaseIdentity()
    {
        var lease = JsonSerializer.SerializeToElement(new CommandLeaseDto
        {
            CommandId = Guid.NewGuid(),
            ClaimToken = Guid.NewGuid(),
            OwnerEpoch = 3,
            GroupEpoch = 4,
            SourceGeneration = 5,
            SourceRevision = 6,
            TargetSequence = 7,
        });

        AssertHasProperties(
            lease,
            "command_id",
            "claim_token",
            "owner_epoch",
            "group_epoch",
            "source_generation",
            "source_revision",
            "target_sequence",
            "lease_expires_at",
            "deadline");
    }

    [Fact]
    public void OfficeRequestContainsStableOperationAndEpochIdentity()
    {
        var request = JsonSerializer.SerializeToElement(new OfficeRequestDto
        {
            OfficeOperationId = Guid.NewGuid(),
            ParentCommandId = Guid.NewGuid(),
            ClaimToken = Guid.NewGuid(),
            SourceGeneration = 8,
            GroupEpoch = 9,
            HostEpoch = 10,
            SlotEpoch = 11,
        });

        AssertHasProperties(
            request,
            "office_operation_id",
            "parent_command_id",
            "parent_job_id",
            "claim_token",
            "source_generation",
            "group_epoch",
            "host_epoch",
            "slot_epoch",
            "deadline",
            "operation",
            "parameters");
    }

    [Fact]
    public void ShutdownMessagesCorrelateRequestAndCleanupResult()
    {
        var requestId = Guid.NewGuid();
        var request = JsonSerializer.SerializeToElement(new ShutdownRequestDto { RequestId = requestId });
        var result = JsonSerializer.SerializeToElement(new ShutdownCompleteDto
        {
            RequestId = requestId,
            Status = "completed",
            CleanupResults = new Dictionary<string, string> { ["vlc"] = "released" },
        });

        Assert.Equal(requestId, request.GetProperty("request_id").GetGuid());
        AssertHasProperties(request, "request_id", "reason", "deadline");
        Assert.Equal(requestId, result.GetProperty("request_id").GetGuid());
        Assert.Equal("released", result.GetProperty("cleanup_results").GetProperty("vlc").GetString());
        AssertHasProperties(result, "request_id", "status", "cleanup_results");
    }

    private static void AssertHasProperties(JsonElement element, params string[] properties)
    {
        foreach (var property in properties)
        {
            Assert.True(element.TryGetProperty(property, out _), $"缺少 IPC 字段 {property}");
        }
    }

    private static void AssertPropertySet(JsonElement element, params string[] expected) =>
        Assert.Equal(expected.Order(), element.EnumerateObject().Select(property => property.Name).Order());
}
