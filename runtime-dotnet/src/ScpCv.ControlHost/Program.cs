using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using ScpCv.ControlHost.Auth;
using ScpCv.ControlHost.Configuration;
using ScpCv.ControlHost.Endpoints;
using ScpCv.ControlHost.Events;
using ScpCv.ControlHost.Health;
using ScpCv.ControlHost.Ipc;
using ScpCv.ControlHost.Logging;
using ScpCv.ControlHost.Runtime;
using ScpCv.ControlHost.Commands;
using ScpCv.Infrastructure.Auth;
using ScpCv.Infrastructure.Audio;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Configuration;
using ScpCv.Infrastructure.Devices;
using ScpCv.Infrastructure.Media;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Playback;
using ScpCv.Infrastructure.Presentations;
using ScpCv.Infrastructure.Runtime;
using ScpCv.Infrastructure.Scenarios;

var builder = WebApplication.CreateBuilder(args);

var dataRootOptions = new DataRootOptions();
builder.Configuration.GetSection(DataRootOptions.SectionName).Bind(dataRootOptions);
var flatDataRoot = builder.Configuration[DataRootOptions.SectionName];
if (!string.IsNullOrWhiteSpace(flatDataRoot))
{
    dataRootOptions.RootPath = flatDataRoot;
}

var safetyMode = SafetyModeOptions.Parse(builder.Configuration["SafetyMode"]);
var controlDbFactory = new ControlDbContextFactory(dataRootOptions, builder.Environment.ContentRootPath);
var mediaOptions = builder.Configuration.GetSection(MediaStorageOptions.SectionName)
    .Get<MediaStorageOptions>() ?? new MediaStorageOptions();
var deviceOptions = builder.Configuration.GetSection(DeviceOptions.SectionName)
    .Get<DeviceOptions>() ?? new DeviceOptions();
var sseOptions = builder.Configuration.GetSection("Sse")
    .Get<SseEventStreamOptions>() ?? new SseEventStreamOptions();
var supervisorOptions = builder.Configuration.GetSection(RuntimeSupervisorOptions.SectionName)
    .Get<RuntimeSupervisorOptions>() ?? new RuntimeSupervisorOptions();

builder.Services.AddSingleton(dataRootOptions);
builder.Services.AddSingleton(safetyMode);
builder.Services.AddSingleton(mediaOptions);
builder.Services.AddSingleton(deviceOptions);
builder.Services.AddSingleton(sseOptions);
builder.Services.AddSingleton(supervisorOptions);
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddHttpClient("stream-probe", client =>
{
    client.Timeout = TimeSpan.FromSeconds(5);
    client.DefaultRequestHeaders.UserAgent.Add(new System.Net.Http.Headers.ProductInfoHeaderValue("SCP-cv", "1.0"));
});
builder.Services.AddSingleton(controlDbFactory);
builder.Services.AddSingleton<IDbContextFactory<ControlDbContext>>(controlDbFactory);
builder.Services.AddSingleton<DatabaseInitializer>();
builder.Services.AddScoped<DatabaseCommands>();
builder.Services.AddSingleton<WriteCoordinator>();
builder.Services.AddSingleton<CommandRepository>();
builder.Services.AddSingleton<RegisteredProcessRegistry>();
builder.Services.AddSingleton<IRegisteredProcessRegistry>(services => services.GetRequiredService<RegisteredProcessRegistry>());
if (safetyMode.IsSimulation)
{
    builder.Services.AddSingleton<QueuedCommandWakeNotifier>();
    builder.Services.AddSingleton<ICommandWakeNotifier>(services => services.GetRequiredService<QueuedCommandWakeNotifier>());
}
else
{
    var installationId = CreateInstallationId(controlDbFactory.Layout.DatabasePath);
    var logonSessionId = Process.GetCurrentProcess().SessionId;
    builder.Services.AddSingleton(services => new NamedPipeServer(
        installationId,
        logonSessionId,
        services.GetRequiredService<IRegisteredProcessRegistry>()));
    builder.Services.AddSingleton<RuntimePipeBroker>();
    builder.Services.AddSingleton<ICommandWakeNotifier>(services => services.GetRequiredService<RuntimePipeBroker>());
    builder.Services.AddHostedService(services => services.GetRequiredService<RuntimePipeBroker>());
}
builder.Services.AddSingleton<RuntimeSupervisorControl>(services =>
    safetyMode.IsSimulation
        ? new RuntimeSupervisorControl(supervisorOptions)
        : new RuntimeSupervisorControl(supervisorOptions, services.GetRequiredService<NamedPipeServer>()));
builder.Services.AddSingleton<CommandCoordinator>();
builder.Services.AddSingleton<CommandLeaseService>();
builder.Services.AddSingleton<CommandResultService>();
builder.Services.AddSingleton<RuntimeAuthorityRepository>();
builder.Services.AddSingleton<MediaSourceService>();
builder.Services.AddSingleton<MediaPreparationService>();
builder.Services.AddSingleton<RuntimeStateService>();
builder.Services.AddSingleton<PresentationCoordinator>();
builder.Services.AddSingleton<ScenarioService>();
builder.Services.AddSingleton<BackgroundAudioService>();
builder.Services.AddSingleton<SseEventHub>();
builder.Services.AddSingleton<RuntimeProjectionPublisher>();
builder.Services.AddSingleton<RuntimeMessageDispatcher>();
builder.Services.AddSingleton<AudioFinishedEventProcessor>();
if (safetyMode.IsSimulation)
{
    builder.Services.AddSingleton<SimulationDeviceCommandTransport>();
    builder.Services.AddSingleton<IDeviceCommandTransport>(services =>
        services.GetRequiredService<SimulationDeviceCommandTransport>());
}
else
{
    builder.Services.AddSingleton<IDeviceCommandTransport, TcpDeviceCommandTransport>();
}
builder.Services.AddSingleton<DeviceService>();
builder.Services.AddScpCvAuthentication(builder.Configuration);
builder.Services.AddHealthChecks()
    .AddCheck<ControlDatabaseHealthCheck>("control_database", tags: ["ready"]);

var app = builder.Build();

await app.Services.GetRequiredService<DatabaseInitializer>()
    .InitializeAsync(app.Lifetime.ApplicationStopping);
await using (var seedScope = app.Services.CreateAsyncScope())
{
    await seedScope.ServiceProvider.GetRequiredService<DevelopmentAccountSeeder>()
        .SeedAsync(app.Lifetime.ApplicationStopping);
}

app.Use(async (context, next) =>
{
    context.Response.OnStarting(() =>
    {
        if (context.Request.Headers.ContainsKey("Origin") &&
            context.Response.Headers.ContainsKey("Access-Control-Allow-Origin"))
        {
            context.Response.Headers.AppendCommaSeparatedValues("Vary", "Origin");
        }

        return Task.CompletedTask;
    });
    await next().ConfigureAwait(false);
});
app.UseCors(AuthServiceCollectionExtensions.CorsPolicyName);
app.UseAuthentication();
app.UseAuthorization();

app.MapHealthChecks(
    "/health/live",
    new HealthCheckOptions { Predicate = _ => false });
app.MapHealthChecks(
    "/health/ready",
    new HealthCheckOptions { Predicate = registration => registration.Tags.Contains("ready") });
app.MapGet(
    "/",
    (SafetyModeOptions mode, ControlDbContextFactory database) => Results.Ok(new
    {
        service = "SCP-cv ControlHost",
        status = "ready",
        safety_mode = mode.Mode.ToString().ToLowerInvariant(),
        database = Path.GetFileName(database.Layout.DatabasePath),
    }));
app.MapAuthEndpoints();
app.MapMediaEndpoints();
app.MapPlaybackEndpoints();
app.MapPresentationEndpoints();
app.MapScenarioEndpoints();
app.MapSystemEndpoints();
app.MapBackgroundAudioEndpoints();
app.MapSseEventEndpoints();

ControlHostLog.Initialized(
    app.Logger,
    safetyMode.Mode,
    DataRootOptions.RequiredDatabaseFileName);

await app.RunAsync();

static Guid CreateInstallationId(string databasePath)
{
    var digest = SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(databasePath).ToUpperInvariant()));
    return new Guid(digest.AsSpan(0, 16));
}

public partial class Program;
