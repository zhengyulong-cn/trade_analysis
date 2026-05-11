from .types import AnalysisBar, BaseSegment, MomentumExhaustionSignal


def _segment_closed_interval(segment: BaseSegment) -> tuple[int, int]:
    return min(segment.start.index, segment.end.index), max(segment.start.index, segment.end.index)


def build_segment_exhaustion_flags(
    segments: list[BaseSegment],
    momentum_signals: list[MomentumExhaustionSignal],
    bars: list[AnalysisBar],
) -> list[bool]:
    if not segments:
        return []

    last_bar_index = bars[-1].index if bars else -1
    flags: list[bool] = []

    for index, segment in enumerate(segments):
        start_index, end_index = _segment_closed_interval(segment)
        segment_span = max(end_index - start_index, 0)
        valid_start_index = start_index + int(segment_span * 0.75)
        if index + 1 < len(segments):
            _, valid_end_index = _segment_closed_interval(segments[index + 1])
        else:
            valid_end_index = last_bar_index

        is_exhausted = False
        for signal in momentum_signals:
            if signal.direction != segment.direction:
                continue
            signal_index = signal.point.index
            if valid_start_index <= signal_index <= valid_end_index:
                is_exhausted = True
                break
        flags.append(is_exhausted)

    return flags
