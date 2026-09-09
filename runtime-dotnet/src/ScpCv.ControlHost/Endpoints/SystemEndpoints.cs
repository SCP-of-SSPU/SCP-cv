using ScpCv.Infrastructure.Devices;
using ScpCv.Infrastructure.Playback;
using ScpCv.Infrastructure.Runtime;
using ScpCv.ControlHost.Runtime;
using ScpCv.Domain.Model;

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
        RuntimeSupervisorControl supervisor,
        CancellationToken cancellationToken) =>
        RequestRuntimeStopAsync("shutdown", "系统关闭请求已发送", authority, runtime, supervisor, cancellationToken);

    private static Task<IResult> RestartAsync(
        RuntimeAuthorityRepository authority,
        RuntimeStateService runtime,
        RuntimeSupervisorControl supervisor,
        CancellationToken cancellationToken) =>
        RequestRuntimeRestartAsync(authority, runtime, supervisor, cancellationToken);

    private static async Task<IResult> RequestRuntimeStopAsync(
        string action,
        string detail,
        RuntimeAuthorityRepository authority,
        RuntimeStateService runtime,
        RuntimeSupervisorControl supervisor,
        CancellationToken cancellationToken)
    {
        var draining = await authority.BeginDrainAsync($"system_{action}", cancellationToken).ConfigureAwait(false);
        var sessions = await runtime.ResetAllAsync(cancellationToken).ConfigureAwait(false);
        if (supervisor.IsConfigured)
        {
            var stopped = await supervisor.LaunchAsync("stop", cancellationToken).ConfigureAwait(false);
            if (!stopped.Accepted)
            {
                return ApiEndpointSupport.Error(stopped.Detail, stopped.Code, StatusCodes.Status503ServiceUnavailable);
            }
        }
        if (draining.State == RuntimeGroupState.Draining)
        {
            await authority.CompleteStopAsync(draining.GroupEpoch, cancellationToken).ConfigureAwait(false);
        }
        return Results.Ok(new { success = true, sessions, detail });
    }

    private static async Task<IResult> RequestRuntimeStartAsync(
        RuntimeAuthorityRepository authority,
        RuntimeSupervisorControl supervisor,
        CancellationToken cancellationToken)
    {
        if (!supervisor.IsConfigured)
            return ApiEndpointSupport.Error("当前 ControlHost 未配置 Supervisor 控制通道", "supervisor_unavailable", StatusCodes.Status503ServiceUnavailable);
        var requestId = Guid.NewGuid();
        var starting = await authority.BeginStartAsync(requestId, cancellationToken).ConfigureAwait(false);
        SupervisorLaunchResult launch;
        try
        {
            launch = await supervisor.LaunchAsync("start", starting.GroupEpoch, cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            await FailAndCleanStartAsync(
                supervisor,
                authority,
                requestId,
                starting.GroupEpoch,
                "runtime_start_cancelled").ConfigureAwait(false);
            throw;
        }
        if (!launch.Accepted)
        {
            var detail = await FailAndCleanStartAsync(
                supervisor,
                authority,
                requestId,
                starting.GroupEpoch,
                launch.Code,
                launch.Detail).ConfigureAwait(false);
            return ApiEndpointSupport.Error(detail, launch.Code, StatusCodes.Status503ServiceUnavailable);
        }
        await authority.ArmAsync(requestId, starting.GroupEpoch, cancellationToken).ConfigureAwait(false);
        return Results.Accepted(value: new { success = true, group_epoch = starting.GroupEpoch, detail = launch.Detail });
    }

    private static async Task<IResult> RequestRuntimeRestartAsync(
        RuntimeAuthorityRepository authority,
        RuntimeStateService runtime,
        RuntimeSupervisorControl supervisor,
        CancellationToken cancellationToken)
    {
        if (!supervisor.IsConfigured)
            return await RequestRuntimeStopAsync("restart", "系统重启请求已发送", authority, runtime, supervisor, cancellationToken).ConfigureAwait(false);

        var draining = await authority.BeginDrainAsync("system_restart", cancellationToken).ConfigureAwait(false);
        await runtime.ResetAllAsync(cancellationToken).ConfigureAwait(false);
        await authority.CompleteStopAsync(draining.GroupEpoch, cancellationToken).ConfigureAwait(false);
        var requestId = Guid.NewGuid();
        var starting = await authority.BeginStartAsync(requestId, cancellationToken).ConfigureAwait(false);
        SupervisorLaunchResult launch;
        try
        {
            launch = await supervisor.LaunchAsync("restart", starting.GroupEpoch, cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            await FailAndCleanStartAsync(
                supervisor,
                authority,
                requestId,
                starting.GroupEpoch,
                "runtime_restart_cancelled").ConfigureAwait(false);
            throw;
        }
        if (!launch.Accepted)
        {
            var detail = await FailAndCleanStartAsync(
                supervisor,
                authority,
                requestId,
                starting.GroupEpoch,
                launch.Code,
                launch.Detail).ConfigureAwait(false);
            return ApiEndpointSupport.Error(detail, launch.Code, StatusCodes.Status503ServiceUnavailable);
        }
        await authority.ArmAsync(requestId, starting.GroupEpoch, cancellationToken).ConfigureAwait(false);
        return Results.Accepted(value: new { success = true, group_epoch = starting.GroupEpoch, detail = launch.Detail });
    }

    private static async Task<string> FailAndCleanStartAsync(
        RuntimeSupervisorControl supervisor,
        RuntimeAuthorityRepository authority,
        Guid requestId,
        long groupEpoch,
        string reason,
        string? detail = null)
    {
        var cleanup = await supervisor.LaunchAsync("stop", CancellationToken.None).ConfigureAwait(false);
        await authority.FailStartAsync(requestId, groupEpoch, reason, CancellationToken.None).ConfigureAwait(false);
        if (cleanup.Accepted)
        {
            return detail ?? reason;
        }

        return $"{detail ?? reason} 启动失败后的运行组清理也失败：{cleanup.Detail}";
    }

    private static IResult DeviceError(DeviceServiceException exception) =>
        ApiEndpointSupport.Error(exception.Message, "device_error", StatusCodes.Status404NotFound);
}
