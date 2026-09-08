using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using ScpCv.ControlHost.Configuration;
using ScpCv.ControlHost.Health;
using ScpCv.ControlHost.Logging;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Configuration;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Runtime;

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

builder.Services.AddSingleton(dataRootOptions);
builder.Services.AddSingleton(safetyMode);
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton(controlDbFactory);
builder.Services.AddSingleton<IDbContextFactory<ControlDbContext>>(controlDbFactory);
builder.Services.AddSingleton<DatabaseInitializer>();
builder.Services.AddSingleton<WriteCoordinator>();
builder.Services.AddSingleton<CommandRepository>();
builder.Services.AddSingleton<RuntimeAuthorityRepository>();
builder.Services.AddHealthChecks()
    .AddCheck<ControlDatabaseHealthCheck>("control_database", tags: ["ready"]);

var app = builder.Build();

await app.Services.GetRequiredService<DatabaseInitializer>()
    .InitializeAsync(app.Lifetime.ApplicationStopping);

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

ControlHostLog.Initialized(
    app.Logger,
    safetyMode.Mode,
    DataRootOptions.RequiredDatabaseFileName);

await app.RunAsync();

public partial class Program;
