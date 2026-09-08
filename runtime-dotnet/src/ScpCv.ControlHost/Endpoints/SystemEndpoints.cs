using ScpCv.Infrastructure.Devices;
using ScpCv.Infrastructure.Playback;
using ScpCv.Infrastructure.Runtime;

namespace ScpCv.ControlHost.Endpoints;

public static class SystemEndpoints
{
    public static IEndpointRouteBuilder MapSystemEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var api = endpoints.MapGroup("/api").RequireSessionAndCsrf();
        api.MapGet("/devices/", ListDevices);
        api.MapPost("/devices/{deviceType}/toggle/", ToggleDeviceAsync);
        api.MapPost("/devices/{deviceType}/power/{action}/", PowerDeviceAsync);
        api.MapPost("/system/shutdown/", ShutdownAsync);
        api.MapPost("/system/restart/", RestartAsync);
        return endpoints;
    }

    private static IResult ListDevices(DeviceService devices) =>
        Results.Ok(new { success = true, devices = devices.List() });

    private static async Task<IResult> ToggleDeviceAsync(
        string deviceType,
        DeviceService devices,
        CancellationToken cancellationToken)
    {
        try
        {
            var device = await devices.ToggleAsync(deviceType, cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, device });
        }
        catch (DeviceServiceException exception)
        {
            return DeviceError(exception);
        }
    }

    private static async Task<IResult> PowerDeviceAsync(
        string deviceType,
        string action,
        DeviceService devices,
        CancellationToken cancellationToken)
    {
        var normalizedAction = action.Trim().ToLowerInvariant();
        if (normalizedAction is not ("on" or "off"))
        {
            return ApiEndpointSupport.Error("action 必须是 on 或 off", "invalid_action");
        }

        try
        {
            var device = await devices.PowerAsync(deviceType, normalizedAction, cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, device });
        }
        catch (DeviceServiceException exception)
        {
            return DeviceError(exception);
        }
    }

    private static Task<IResult> ShutdownAsync(
        RuntimeAuthorityRepository authority,
        RuntimeStateService runtime,
        CancellationToken cancellationToken) =>
        RequestRuntimeStopAsync("shutdown", "系统关闭请求已发送", authority, runtime, cancellationToken);

    private static Task<IResult> RestartAsync(
        RuntimeAuthorityRepository authority,
        RuntimeStateService runtime,
        CancellationToken cancellationToken) =>
        RequestRuntimeStopAsync("restart", "系统重启请求已发送", authority, runtime, cancellationToken);

    private static async Task<IResult> RequestRuntimeStopAsync(
        string action,
        string detail,
        RuntimeAuthorityRepository authority,
        RuntimeStateService runtime,
        CancellationToken cancellationToken)
    {
        await authority.BeginDrainAsync($"system_{action}", cancellationToken).ConfigureAwait(false);
        var sessions = await runtime.ResetAllAsync(cancellationToken).ConfigureAwait(false);
        return Results.Ok(new { success = true, sessions, detail });
    }

    private static IResult DeviceError(DeviceServiceException exception) =>
        ApiEndpointSupport.Error(exception.Message, "device_error", StatusCodes.Status404NotFound);
}
