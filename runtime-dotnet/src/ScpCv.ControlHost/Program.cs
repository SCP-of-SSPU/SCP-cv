using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using ScpCv.ControlHost.Auth;
using ScpCv.ControlHost.Configuration;
using ScpCv.ControlHost.Health;
using ScpCv.ControlHost.Logging;
using ScpCv.Infrastructure.Auth;
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

ControlHostLog.Initialized(
    app.Logger,
    safetyMode.Mode,
    DataRootOptions.RequiredDatabaseFileName);

await app.RunAsync();

public partial class Program;
