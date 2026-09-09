using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace ScpCv.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddCommandTriggerEvent : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<Guid>(
                name: "TriggerEventId",
                table: "command_records",
                type: "TEXT",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_command_records_TriggerEventId",
                table: "command_records",
                column: "TriggerEventId",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_command_records_TriggerEventId",
                table: "command_records");

            migrationBuilder.DropColumn(
                name: "TriggerEventId",
                table: "command_records");
        }
    }
}
