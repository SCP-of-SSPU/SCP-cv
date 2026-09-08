using ScpCv.Domain.Model;
using ScpCv.Domain.Rules;

namespace ScpCv.Infrastructure.Presentations;

public sealed record PresentationSlot(
    long HostEpoch,
    long SlotEpoch,
    int WindowId,
    long SourceId,
    string SourceDigest,
    PlaybackMode Mode,
    bool Resettable);

public sealed class PresentationCoordinator
{
    private readonly object _gate = new();
    private PresentationSlot? _slot;

    public PresentationSlot? CurrentSlot
    {
        get { lock (_gate) return _slot; }
    }

    public PresentationDecision Open(
        int windowId,
        long sourceId,
        string sourceDigest,
        bool pdfAvailable,
        string? pdfDigest,
        bool pdfFresh,
        long hostEpoch)
    {
        lock (_gate)
        {
            var decision = PresentationPolicy.ChooseOpen(new PresentationOpenRequest(
                sourceDigest,
                _slot is null,
                pdfAvailable,
                pdfDigest,
                pdfFresh));
            if (decision.Accepted && decision.Mode == PlaybackMode.PowerPoint)
            {
                _slot = new PresentationSlot(
                    hostEpoch,
                    (_slot?.SlotEpoch ?? 0) + 1,
                    windowId,
                    sourceId,
                    sourceDigest,
                    PlaybackMode.PowerPoint,
                    Resettable: true);
            }

            return decision;
        }
    }

    public bool Release(long hostEpoch, long slotEpoch)
    {
        lock (_gate)
        {
            if (_slot is null || _slot.HostEpoch != hostEpoch || _slot.SlotEpoch != slotEpoch) return false;
            _slot = null;
            return true;
        }
    }

    public bool ShouldResetCurrent()
    {
        lock (_gate) return _slot is not null && PresentationPolicy.ShouldReset(_slot.Mode);
    }
}
