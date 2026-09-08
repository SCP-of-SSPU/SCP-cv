using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ScpCv.Domain.Model;

namespace ScpCv.Infrastructure.Persistence.Configurations;

public sealed class WorkerOwnershipConfiguration : IEntityTypeConfiguration<WorkerOwnership>
{
    public void Configure(EntityTypeBuilder<WorkerOwnership> builder)
    {
        builder.ToTable("worker_ownerships");
        builder.HasKey(entity => entity.Id);
        builder.HasIndex(entity => new { entity.TargetKind, entity.TargetId }).IsUnique();
        builder.HasIndex(entity => entity.WorkerInstanceId).IsUnique();
    }
}

public sealed class RuntimeGroupControlConfiguration : IEntityTypeConfiguration<RuntimeGroupControl>
{
    public void Configure(EntityTypeBuilder<RuntimeGroupControl> builder)
    {
        builder.ToTable("runtime_group_control", table =>
            table.HasCheckConstraint("CK_runtime_group_control_singleton", "Id = 1"));
        builder.HasKey(entity => entity.Id);
    }
}

public sealed class OfficeOperationConfiguration : IEntityTypeConfiguration<OfficeOperation>
{
    public void Configure(EntityTypeBuilder<OfficeOperation> builder)
    {
        builder.ToTable("office_operations");
        builder.HasKey(entity => entity.Id);
        builder.HasIndex(entity => entity.OperationId).IsUnique();
        builder.HasIndex(entity => new { entity.Status, entity.Deadline });
        builder.HasIndex(entity => entity.ParentCommandId);
        builder.HasIndex(entity => entity.ParentJobId);
    }
}
