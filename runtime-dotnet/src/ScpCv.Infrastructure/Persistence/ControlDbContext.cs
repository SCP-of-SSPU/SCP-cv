using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage.ValueConversion;
using ScpCv.Domain.Model;

namespace ScpCv.Infrastructure.Persistence;

public sealed class ControlDbContext(DbContextOptions<ControlDbContext> options) : DbContext(options)
{
    public DbSet<UserAccount> UserAccounts => Set<UserAccount>();
    public DbSet<MediaFolder> MediaFolders => Set<MediaFolder>();
    public DbSet<MediaSource> MediaSources => Set<MediaSource>();
    public DbSet<PptResource> PptResources => Set<PptResource>();
    public DbSet<PlaybackSession> PlaybackSessions => Set<PlaybackSession>();
    public DbSet<RuntimeState> RuntimeStates => Set<RuntimeState>();
    public DbSet<Scenario> Scenarios => Set<Scenario>();
    public DbSet<BackgroundAudioState> BackgroundAudioStates => Set<BackgroundAudioState>();
    public DbSet<BackgroundAudioPlaylistItem> BackgroundAudioPlaylistItems => Set<BackgroundAudioPlaylistItem>();
    public DbSet<StreamSource> StreamSources => Set<StreamSource>();
    public DbSet<CommandRecord> CommandRecords => Set<CommandRecord>();
    public DbSet<WorkerOwnership> WorkerOwnerships => Set<WorkerOwnership>();
    public DbSet<RuntimeGroupControl> RuntimeGroupControls => Set<RuntimeGroupControl>();
    public DbSet<OfficeOperation> OfficeOperations => Set<OfficeOperation>();
    public DbSet<MediaPreparationJob> MediaPreparationJobs => Set<MediaPreparationJob>();
    public DbSet<ArtifactManifest> ArtifactManifests => Set<ArtifactManifest>();

    protected override void ConfigureConventions(ModelConfigurationBuilder configurationBuilder)
    {
        configurationBuilder.Properties<DateTimeOffset>().HaveConversion<UtcTicksConverter>();
        configurationBuilder.Properties<Enum>().HaveConversion<string>();
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder) =>
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(ControlDbContext).Assembly);

    private sealed class UtcTicksConverter()
        : ValueConverter<DateTimeOffset, long>(
            value => value.UtcTicks,
            value => new DateTimeOffset(value, TimeSpan.Zero));
}
