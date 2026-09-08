using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ScpCv.Domain.Model;

namespace ScpCv.Infrastructure.Persistence.Configurations;

public sealed class MediaPreparationJobConfiguration : IEntityTypeConfiguration<MediaPreparationJob>
{
    public void Configure(EntityTypeBuilder<MediaPreparationJob> builder)
    {
        builder.ToTable("media_preparation_jobs");
        builder.HasKey(entity => entity.Id);
        builder.HasIndex(entity => entity.JobId).IsUnique();
        builder.HasIndex(entity => new
        {
            entity.SourceId,
            entity.SourceDigest,
            entity.Kind,
            entity.RecipeVersion,
        }).IsUnique();
        builder.HasOne(entity => entity.Source)
            .WithMany()
            .HasForeignKey(entity => entity.SourceId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}

public sealed class ArtifactManifestConfiguration : IEntityTypeConfiguration<ArtifactManifest>
{
    public void Configure(EntityTypeBuilder<ArtifactManifest> builder)
    {
        builder.ToTable("artifact_manifests");
        builder.HasKey(entity => entity.Id);
        builder.HasIndex(entity => new
        {
            entity.SourceId,
            entity.SourceDigest,
            entity.RecipeVersion,
            entity.RelativePath,
        }).IsUnique();
        builder.HasOne(entity => entity.Source)
            .WithMany()
            .HasForeignKey(entity => entity.SourceId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
