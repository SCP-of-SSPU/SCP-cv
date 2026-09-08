using System.Collections.Concurrent;
using System.Net.Sockets;
using ScpCv.Contracts.Http;

namespace ScpCv.Infrastructure.Devices;

public sealed class DeviceOptions
{
    public const string SectionName = "Devices";

    public int TcpTimeoutMilliseconds { get; set; } = 3000;
    public List<DeviceEndpointOptions> Endpoints { get; set; } = [];
}

public sealed class DeviceEndpointOptions
{
    public string DeviceType { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Label { get; set; } = string.Empty;
    public string Host { get; set; } = string.Empty;
    public int Port { get; set; }
}

public sealed record DeviceCommand(
    string DeviceType,
    string Host,
    int Port,
    IReadOnlyList<string> Frames,
    TimeSpan InterFrameDelay);

public interface IDeviceCommandTransport
{
    bool IsSimulation { get; }

    Task SendAsync(DeviceCommand command, CancellationToken cancellationToken = default);
}

public sealed class SimulationDeviceCommandTransport : IDeviceCommandTransport
{
    private readonly ConcurrentQueue<DeviceCommand> _commands = new();

    public bool IsSimulation => true;
    public IReadOnlyCollection<DeviceCommand> Commands => _commands.ToArray();

    public Task SendAsync(DeviceCommand command, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        _commands.Enqueue(command);
        return Task.CompletedTask;
    }
}

public sealed class TcpDeviceCommandTransport(DeviceOptions options) : IDeviceCommandTransport
{
    public bool IsSimulation => false;

    public async Task SendAsync(DeviceCommand command, CancellationToken cancellationToken = default)
    {
        for (var index = 0; index < command.Frames.Count; index++)
        {
            await SendFrameAsync(command, command.Frames[index], cancellationToken).ConfigureAwait(false);
            if (index < command.Frames.Count - 1)
            {
                await Task.Delay(command.InterFrameDelay, cancellationToken).ConfigureAwait(false);
            }
        }
    }

    private async Task SendFrameAsync(
        DeviceCommand command,
        string hexFrame,
        CancellationToken cancellationToken)
    {
        byte[] bytes;
        try
        {
            bytes = Convert.FromHexString(hexFrame.Replace(" ", string.Empty, StringComparison.Ordinal));
        }
        catch (FormatException exception)
        {
            throw new DeviceServiceException("设备控制帧格式无效", exception);
        }

        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromMilliseconds(options.TcpTimeoutMilliseconds));
        try
        {
            using var client = new TcpClient();
            await client.ConnectAsync(command.Host, command.Port, timeout.Token).ConfigureAwait(false);
            await client.GetStream().WriteAsync(bytes, timeout.Token).ConfigureAwait(false);
        }
        catch (Exception exception) when (exception is SocketException or IOException or OperationCanceledException)
        {
            if (exception is OperationCanceledException && cancellationToken.IsCancellationRequested)
            {
                throw;
            }

            throw new DeviceServiceException(
                $"发送设备电源指令失败：{command.Host}:{command.Port} {exception.Message}",
                exception);
        }
    }
}

public sealed class DeviceService
{
    private static readonly string[] SpliceOnFrames = ["FF06010A00010001FA", "FF06010A00010000FA"];
    private static readonly string[] SpliceOffFrames = ["FF06010A00020001FA", "FF06010A00020000FA"];
    private static readonly string[] TvToggleFrames = ["FF06010A00330001FA", "FF06010A00330000FA"];
    private readonly IReadOnlyList<DeviceEndpointOptions> _orderedDevices;
    private readonly Dictionary<string, DeviceEndpointOptions> _devices;
    private readonly IDeviceCommandTransport _transport;

    public DeviceService(DeviceOptions options, IDeviceCommandTransport transport)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentNullException.ThrowIfNull(transport);
        if (options.TcpTimeoutMilliseconds <= 0)
        {
            throw new InvalidOperationException("Devices:TcpTimeoutMilliseconds 必须大于 0。");
        }

        foreach (var device in options.Endpoints)
        {
            Validate(device);
        }

        _orderedDevices = options.Endpoints.ToArray();
        try
        {
            _devices = _orderedDevices.ToDictionary(
                device => device.DeviceType,
                StringComparer.OrdinalIgnoreCase);
        }
        catch (ArgumentException exception)
        {
            throw new InvalidOperationException("Devices:Endpoints 包含重复的 device_type。", exception);
        }
        _transport = transport;
    }

    public IReadOnlyList<DeviceDto> List() =>
        _orderedDevices.Select(device => ToDto(device, string.Empty)).ToArray();

    public Task<DeviceDto> ToggleAsync(string deviceType, CancellationToken cancellationToken = default)
    {
        var device = GetDevice(deviceType);
        if (!IsTelevision(device.DeviceType))
        {
            throw new DeviceServiceException("拼接屏不支持切换指令，请使用开机或关机");
        }

        return ExecuteAsync(device, "toggle", TvToggleFrames, TimeSpan.FromMilliseconds(100), cancellationToken);
    }

    public Task<DeviceDto> PowerAsync(
        string deviceType,
        string action,
        CancellationToken cancellationToken = default)
    {
        var device = GetDevice(deviceType);
        if (!string.Equals(device.DeviceType, "splice_screen", StringComparison.OrdinalIgnoreCase))
        {
            throw new DeviceServiceException("电视仅支持开关机切换指令");
        }

        return action switch
        {
            "on" => ExecuteAsync(device, action, SpliceOnFrames, TimeSpan.FromSeconds(5), cancellationToken),
            "off" => ExecuteAsync(device, action, SpliceOffFrames, TimeSpan.FromSeconds(5), cancellationToken),
            _ => throw new ArgumentOutOfRangeException(nameof(action)),
        };
    }

    private async Task<DeviceDto> ExecuteAsync(
        DeviceEndpointOptions device,
        string action,
        IReadOnlyList<string> frames,
        TimeSpan interFrameDelay,
        CancellationToken cancellationToken)
    {
        await _transport.SendAsync(
            new DeviceCommand(device.DeviceType, device.Host, device.Port, frames, interFrameDelay),
            cancellationToken).ConfigureAwait(false);
        return ToDto(device, action);
    }

    private DeviceEndpointOptions GetDevice(string deviceType)
    {
        var normalized = deviceType.Trim();
        return _devices.TryGetValue(normalized, out var device)
            ? device
            : throw new DeviceServiceException($"设备类型 {normalized} 不存在");
    }

    private DeviceDto ToDto(DeviceEndpointOptions device, string action) => new()
    {
        Name = device.Name,
        DeviceType = device.DeviceType,
        DeviceTypeLabel = device.Label.Length == 0 ? device.Name : device.Label,
        Host = device.Host,
        Port = device.Port,
        Action = action,
        Detail = _transport.IsSimulation
            ? "Simulation 模式：已接受指令，未发送网络流量"
            : "电源指令已发送，未读取设备返回",
    };

    private static bool IsTelevision(string deviceType) =>
        string.Equals(deviceType, "tv_left", StringComparison.OrdinalIgnoreCase) ||
        string.Equals(deviceType, "tv_right", StringComparison.OrdinalIgnoreCase);

    private static void Validate(DeviceEndpointOptions device)
    {
        if (string.IsNullOrWhiteSpace(device.DeviceType) ||
            string.IsNullOrWhiteSpace(device.Name) ||
            string.IsNullOrWhiteSpace(device.Host) ||
            device.Port is < 1 or > 65535)
        {
            throw new InvalidOperationException("Devices:Endpoints 中的设备类型、名称、主机或端口无效。");
        }
    }
}

public sealed class DeviceServiceException : Exception
{
    public DeviceServiceException(string message)
        : base(message)
    {
    }

    public DeviceServiceException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}
