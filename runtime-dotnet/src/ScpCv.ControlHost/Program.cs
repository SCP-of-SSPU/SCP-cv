using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using ScpCv.ControlHost.Auth;
using ScpCv.ControlHost.Configuration;
using ScpCv.ControlHost.Endpoints;
using ScpCv.ControlHost.Health;
using ScpCv.ControlHost.Logging;
using ScpCv.Infrastructure.Auth;
using ScpCv.Infrastructure.Audio;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Configuration;
using ScpCv.Infrastructure.Devices;
using ScpCv.Infrastructure.Media;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Playback;
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

builder.Services.AddSingleton(dataRootOptions);
builder.Services.AddSingleton(safetyMode);
builder.Services.AddSingleton(mediaOptions);
builder.Services.AddSingleton(deviceOptions);
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton(controlDbFactory);
builder.Services.AddSingleton<IDbContextFactory<ControlDbContext>>(controlDbFactory);
builder.Services.AddSingleton<DatabaseInitializer>();
builder.Services.AddSingleton<WriteCoordinator>();
builder.Services.AddSingleton<CommandRepository>();
builder.Services.AddSingleton<RuntimeAuthorityRepository>();
builder.Services.AddSingleton<MediaSourceService>();
builder.Services.AddSingleton<RuntimeStateService>();
builder.Services.AddSingleton<ScenarioService>();
builder.Services.AddSingleton<BackgroundAudioService>();
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
app.MapScenarioEndpoints();
app.MapSystemEndpoints();
app.MapBackgroundAudioEndpoints();

ControlHostLog.Initialized(
    app.Logger,
    safetyMode.Mode,
    DataRootOptions.RequiredDatabaseFileName);

await app.RunAsync();

public partial class Program;
