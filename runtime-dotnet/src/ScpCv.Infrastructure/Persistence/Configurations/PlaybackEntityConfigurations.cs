using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ScpCv.Domain.Model;

namespace ScpCv.Infrastructure.Persistence.Configurations;

public sealed class PlaybackSessionConfiguration : IEntityTypeConfiguration<PlaybackSession>
{
    public void Configure(EntityTypeBuilder<PlaybackSession> builder)
    {
        builder.ToTable("playback_sessions", table =>
        {
            table.HasCheckConstraint("CK_playback_sessions_window", "WindowId >= 1 AND WindowId <= 4");
            table.HasCheckConstraint("CK_playback_sessions_volume", "Volume >= 0 AND Volume <= 100");
        });
        builder.HasKey(entity => entity.Id);
        builder.HasIndex(entity => entity.WindowId).IsUnique();
        builder.HasOne(entity => entity.MediaSource)
            .WithMany()
            .HasForeignKey(entity => entity.MediaSourceId)
            .OnDelete(DeleteBehavior.SetNull);
    }
}

public sealed class RuntimeStateConfiguration : IEntityTypeConfiguration<RuntimeState>
{
    public void Configure(EntityTypeBuilder<RuntimeState> builder)
    {
        builder.ToTable("runtime_state", table =>
        {
            table.HasCheckConstraint("CK_runtime_state_singleton", "Id = 1");
            table.HasCheckConstraint("CK_runtime_state_volume", "VolumeLevel >= 0 AND VolumeLevel <= 100");
        });
        builder.HasKey(entity => entity.Id);
    }
}

public sealed class BackgroundAudioStateConfiguration : IEntityTypeConfiguration<BackgroundAudioState>
{
    public void Configure(EntityTypeBuilder<BackgroundAudioState> builder)
    {
        builder.ToTable("background_audio_state", table =>
        {
            table.HasCheckConstraint("CK_background_audio_state_singleton", "Id = 1");
            table.HasCheckConstraint("CK_background_audio_state_volume", "Volume >= 0 AND Volume <= 100");
        });
        builder.HasKey(entity => entity.Id);
        builder.HasOne(entity => entity.CurrentSource)
            .WithMany()
            .HasForeignKey(entity => entity.CurrentSourceId)
            .OnDelete(DeleteBehavior.SetNull);
    }
}

public sealed class BackgroundAudioPlaylistItemConfiguration : IEntityTypeConfiguration<BackgroundAudioPlaylistItem>
{
    public void Configure(EntityTypeBuilder<BackgroundAudioPlaylistItem> builder)
    {
        builder.ToTable("background_audio_playlist_items");
        builder.HasKey(entity => entity.Id);
        builder.HasIndex(entity => new { entity.SortOrder, entity.Id });
        builder.HasOne(entity => entity.State)
            .WithMany(entity => entity.Playlist)
            .HasForeignKey(entity => entity.StateId)
            .OnDelete(DeleteBehavior.Cascade);
        builder.HasOne(entity => entity.Source)
            .WithMany()
            .HasForeignKey(entity => entity.SourceId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
