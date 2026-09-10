using Microsoft.EntityFrameworkCore;
using ScpCv.Contracts.Http;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Playback;
using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

public sealed class HostHardwareIntegrationTests
{
    [Fact]
    public async Task PhysicalDisplayTopologyPreservesNegativeCoordinatesAndRejectsUnknownTarget()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var topology = new StubDisplayTopologyProvider(new DisplayTopologySnapshot(
            true,
            [
                Display(1, @"\\.\DISPLAY1", 0, 0, true),
                Display(2, @"\\.\DISPLAY2", -1920, 120, false),
            ],
            "windows_display_topology"));
        var runtime = CreateRuntime(fixture, topology, new SimulationSystemAudioController());

        var targets = runtime.ListDisplays();
        Assert.Equal(2, targets.Count);
        Assert.Equal(-1920, targets[1].X);
        Assert.Equal(120, targets[1].Y);

        var sessions = await runtime.SelectDisplayAsync(1, "single", @"\\.\DISPLAY2");
        Assert.Equal(@"\\.\DISPLAY2", sessions.Single(item => item.WindowId == 1).TargetDisplayLabel);
        var error = await Assert.ThrowsAsync<PlaybackServiceException>(
            () => runtime.SelectDisplayAsync(1, "single", @"\\.\DISPLAY9"));
        Assert.Equal("display_target_unavailable", error.Code);
    }

    [Fact]
    public async Task HardwareVolumePersistsOnlyObservedCoreAudioState()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var audio = new StubSystemAudioController(
            new SystemAudioSnapshot(true, 64, false, "windows_core_audio"),
            new SystemAudioSnapshot(true, 41, true, "windows_core_audio"));
        var runtime = CreateRuntime(
            fixture,
            new SimulationDisplayTopologyProvider(),
            audio);

        var initial = await runtime.GetSystemVolumeAsync();
        Assert.Equal(64, initial.Level);
        Assert.True(initial.SystemSynced);
        Assert.Equal("windows_core_audio", initial.Backend);

        var applied = await runtime.SetSystemVolumeAsync(42, true);
        Assert.Equal((42, true), audio.LastSet);
        Assert.Equal(41, applied.Level);
        Assert.True(applied.Muted);
        Assert.True(applied.SystemSynced);

        await using var database = fixture.Database.CreateDbContext();
        var persisted = await database.RuntimeStates.AsNoTracking().SingleAsync();
        Assert.Equal(41, persisted.VolumeLevel);
        Assert.True(persisted.VolumeMuted);
    }

    [Fact]
    public async Task UnavailableCoreAudioFailsClosedWithoutChangingPersistedIntent()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var audio = new StubSystemAudioController(
            new SystemAudioSnapshot(false, 0, false, "windows_core_audio_unavailable", "没有默认渲染设备。"),
            new SystemAudioSnapshot(false, 0, false, "windows_core_audio_unavailable", "没有默认渲染设备。"));
        var runtime = CreateRuntime(
            fixture,
            new SimulationDisplayTopologyProvider(),
            audio);

        var current = await runtime.GetSystemVolumeAsync();
        Assert.False(current.SystemSynced);
        Assert.Equal("windows_core_audio_unavailable", current.Backend);

        var error = await Assert.ThrowsAsync<PlaybackServiceException>(
            () => runtime.SetSystemVolumeAsync(22, false));
        Assert.Equal("system_audio_unavailable", error.Code);

        await using var database = fixture.Database.CreateDbContext();
        var persisted = await database.RuntimeStates.AsNoTracking().SingleAsync();
        Assert.NotEqual(22, persisted.VolumeLevel);
    }

    private static RuntimeStateService CreateRuntime(
        ControlHostFixture fixture,
        IDisplayTopologyProvider displays,
        ISystemAudioController audio)
    {
        var coordinator = new CommandCoordinator(fixture.Commands, new NullCommandWakeNotifier());
        return new RuntimeStateService(
            fixture.Database,
            fixture.Writes,
            coordinator,
            fixture.TimeProvider,
            displays,
            audio);
    }

    private static DisplayTargetDto Display(int index, string name, int x, int y, bool primary) => new()
    {
        Index = index,
        Name = name,
        Width = 1920,
        Height = 1080,
        X = x,
        Y = y,
        IsPrimary = primary,
    };

    private sealed class StubDisplayTopologyProvider(DisplayTopologySnapshot snapshot) : IDisplayTopologyProvider
    {
        public DisplayTopologySnapshot GetCurrent() => snapshot;
    }

    private sealed class StubSystemAudioController(
        SystemAudioSnapshot current,
        SystemAudioSnapshot applied) : ISystemAudioController
    {
        public bool IsHardware => true;
        public (int? Level, bool? Muted) LastSet { get; private set; }

        public SystemAudioSnapshot GetCurrent() => current;

        public SystemAudioSnapshot Apply(int? level, bool? muted)
        {
            LastSet = (level, muted);
            return applied;
        }
    }
}
