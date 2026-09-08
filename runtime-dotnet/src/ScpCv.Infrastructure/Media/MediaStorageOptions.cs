namespace ScpCv.Infrastructure.Media;

public sealed class MediaStorageOptions
{
    public const string SectionName = "Media";

    public string[] AllowedLocalRoots { get; set; } = [];
}
