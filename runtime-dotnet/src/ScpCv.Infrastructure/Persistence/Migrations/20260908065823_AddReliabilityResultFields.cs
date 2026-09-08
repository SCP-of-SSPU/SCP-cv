using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace ScpCv.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddReliabilityResultFields : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<long>(
                name: "SourceGeneration",
                table: "office_operations",
                type: "INTEGER",
                nullable: false,
                defaultValue: 0L);

            migrationBuilder.AddColumn<string>(
                name: "ResultHash",
                table: "command_records",
                type: "TEXT",
                maxLength: 128,
                nullable: false,
                defaultValue: "");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "SourceGeneration",
                table: "office_operations");

            migrationBuilder.DropColumn(
                name: "ResultHash",
                table: "command_records");
        }
    }
}
