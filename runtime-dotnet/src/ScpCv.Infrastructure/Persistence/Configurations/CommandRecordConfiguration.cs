using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ScpCv.Domain.Model;

namespace ScpCv.Infrastructure.Persistence.Configurations;

public sealed class CommandRecordConfiguration : IEntityTypeConfiguration<CommandRecord>
{
    public void Configure(EntityTypeBuilder<CommandRecord> builder)
    {
        builder.ToTable("command_records", table =>
            table.HasCheckConstraint(
                "CK_command_records_target",
                "(TargetKind = 'Display' AND TargetId >= 1 AND TargetId <= 4) OR (TargetKind = 'Audio' AND TargetId = 1)"));
        builder.HasKey(entity => entity.Id);
        builder.HasIndex(entity => entity.CommandId).IsUnique();
        builder.HasIndex(entity => new { entity.TargetKind, entity.TargetId, entity.TargetSequence }).IsUnique();
        builder.HasIndex(entity => new { entity.TargetKind, entity.TargetId, entity.Status, entity.TargetSequence });
        builder.HasIndex(entity => new { entity.Status, entity.LeaseExpiresAt });
        builder.HasIndex(entity => new { entity.TargetKind, entity.TargetId })
            .HasFilter("Status = 'Processing'")
            .IsUnique();
        builder.Property(entity => entity.Command).HasMaxLength(80);
        builder.Property(entity => entity.ResultCode).HasMaxLength(100);
        builder.Property(entity => entity.ResultHash).HasMaxLength(128);
    }
}
