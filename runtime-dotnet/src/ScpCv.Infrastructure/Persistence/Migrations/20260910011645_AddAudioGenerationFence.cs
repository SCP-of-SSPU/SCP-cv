using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace ScpCv.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddAudioGenerationFence : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<long>(
                name: "DesiredGeneration",
                table: "background_audio_state",
                type: "INTEGER",
                nullable: false,
                defaultValue: 0L);

            migrationBuilder.AddColumn<long>(
                name: "ObservedGeneration",
                table: "background_audio_state",
                type: "INTEGER",
                nullable: false,
                defaultValue: 0L);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "DesiredGeneration",
                table: "background_audio_state");

            migrationBuilder.DropColumn(
                name: "ObservedGeneration",
                table: "background_audio_state");
        }
    }
}
