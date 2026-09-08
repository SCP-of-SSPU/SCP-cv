using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ScpCv.Domain.Model;

namespace ScpCv.Infrastructure.Persistence.Configurations;

public sealed class UserAccountConfiguration : IEntityTypeConfiguration<UserAccount>
{
    public void Configure(EntityTypeBuilder<UserAccount> builder)
    {
        builder.ToTable("user_accounts");
        builder.HasKey(entity => entity.Id);
        builder.HasIndex(entity => entity.Username).IsUnique();
        builder.Property(entity => entity.Username).HasMaxLength(150);
        builder.Property(entity => entity.PasswordHash).HasMaxLength(512);
    }
}

public sealed class MediaFolderConfiguration : IEntityTypeConfiguration<MediaFolder>
{
    public void Configure(EntityTypeBuilder<MediaFolder> builder)
    {
        builder.ToTable("media_folders");
        builder.HasKey(entity => entity.Id);
        builder.Property(entity => entity.Name).HasMaxLength(255);
        builder.HasOne(entity => entity.Parent)
            .WithMany(entity => entity.Children)
            .HasForeignKey(entity => entity.ParentId)
            .OnDelete(DeleteBehavior.Restrict);
    }
}

public sealed class MediaSourceConfiguration : IEntityTypeConfiguration<MediaSource>
{
    public void Configure(EntityTypeBuilder<MediaSource> builder)
    {
        builder.ToTable("media_sources");
        builder.HasKey(entity => entity.Id);
        builder.Property(entity => entity.Name).HasMaxLength(255);
        builder.Property(entity => entity.MimeType).HasMaxLength(255);
        builder.Property(entity => entity.ContentDigest).HasMaxLength(128);
        builder.HasOne(entity => entity.Folder)
            .WithMany(entity => entity.Sources)
            .HasForeignKey(entity => entity.FolderId)
            .OnDelete(DeleteBehavior.SetNull);
        builder.HasIndex(entity => entity.ExpiresAt);
        builder.HasIndex(entity => entity.StreamIdentifier);
    }
}

public sealed class PptResourceConfiguration : IEntityTypeConfiguration<PptResource>
{
    public void Configure(EntityTypeBuilder<PptResource> builder)
    {
        builder.ToTable("ppt_resources", table => table.HasCheckConstraint("CK_ppt_resources_page_index", "PageIndex >= 1"));
        builder.HasKey(entity => entity.Id);
        builder.HasIndex(entity => new { entity.SourceId, entity.PageIndex }).IsUnique();
        builder.HasOne(entity => entity.Source)
            .WithMany(entity => entity.PptResources)
            .HasForeignKey(entity => entity.SourceId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}

public sealed class ScenarioConfiguration : IEntityTypeConfiguration<Scenario>
{
    public void Configure(EntityTypeBuilder<Scenario> builder)
    {
        builder.ToTable("scenarios", table =>
            table.HasCheckConstraint("CK_scenarios_volume", "VolumeLevel >= 0 AND VolumeLevel <= 100"));
        builder.HasKey(entity => entity.Id);
        builder.Property(entity => entity.Name).HasMaxLength(255);
        builder.HasIndex(entity => new { entity.SortOrder, entity.UpdatedAt });
    }
}

public sealed class StreamSourceConfiguration : IEntityTypeConfiguration<StreamSource>
{
    public void Configure(EntityTypeBuilder<StreamSource> builder)
    {
        builder.ToTable("stream_sources");
        builder.HasKey(entity => entity.Id);
        builder.Property(entity => entity.StreamIdentifier).HasMaxLength(255);
        builder.HasIndex(entity => entity.StreamIdentifier).IsUnique();
    }
}
