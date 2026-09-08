namespace ScpCv.Contracts.Errors;

public static class ErrorCodes
{
    public const string BadRequest = "bad_request";
    public const string InvalidJson = "invalid_json";
    public const string Unauthorized = "unauthorized";
    public const string InvalidCredentials = "invalid_credentials";
    public const string InvalidPassword = "invalid_password";
    public const string WeakPassword = "weak_password";
    public const string InvalidAction = "invalid_action";
    public const string InvalidSource = "invalid_source";
    public const string InvalidWindow = "invalid_window";
    public const string MissingAction = "missing_action";
    public const string MissingFile = "missing_file";
    public const string MissingPath = "missing_path";
    public const string MissingUrl = "missing_url";
    public const string MissingName = "missing_name";
    public const string InvalidResources = "invalid_resources";
    public const string MediaError = "media_error";
    public const string PlaybackError = "playback_error";
    public const string VolumeError = "volume_error";
    public const string BackgroundAudioError = "background_audio_error";
    public const string ScenarioError = "scenario_error";
    public const string DeviceError = "device_error";
    public const string RuntimeNotArmed = "runtime_not_armed";
    public const string QueueBusy = "queue_busy";
    public const string StaleEpoch = "stale_epoch";
    public const string StaleClaim = "stale_claim";
    public const string ResultConflict = "result_conflict";
    public const string UnsupportedMessage = "unsupported_message";
    public const string DatabaseIncompatible = "database_incompatible";
    public const string SimulationOnly = "simulation_only";
}
