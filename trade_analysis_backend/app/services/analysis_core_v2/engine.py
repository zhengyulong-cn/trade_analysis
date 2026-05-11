from .higher_level_segment import (
    advance_higher_level,
    all_higher_segments,
    create_higher_level_state,
)
from .inclusion import advance_inclusion, create_inclusion_state
from .momentum_exhaustion import (
    advance_momentum_exhaustion,
    create_momentum_exhaustion_state,
)
from .segment import advance_segment, all_segments, create_segment_state
from .segment_momentum_binding import build_segment_exhaustion_flags
from .trading_range import advance_trading_range, create_trading_range_state
from .types import AnalysisBar

def analyze(
    bars: list[AnalysisBar],
    max_included: int = 10,
    min_distance: int = 4,
) -> dict:
    inclusion_state = create_inclusion_state()
    segment_state = create_segment_state()
    higher_level_state = create_higher_level_state()
    trading_range_state = create_trading_range_state()
    momentum_exhaustion_state = create_momentum_exhaustion_state()

    for bar in bars:
        advance_inclusion(inclusion_state, bar, max_included)
        advance_segment(segment_state, inclusion_state.merged_bars, min_distance)
        current_segments = all_segments(segment_state)
        advance_higher_level(higher_level_state, bar, bar.index, current_segments, min_distance)
        current_higher_dir: str | None = None
        if higher_level_state.last_cross_relation == "above":
            current_higher_dir = "up"
        elif higher_level_state.last_cross_relation == "below":
            current_higher_dir = "down"
        advance_trading_range(trading_range_state, bars, current_segments, current_higher_dir)
        advance_momentum_exhaustion(momentum_exhaustion_state, bars, current_segments, bar.index)

    final_segments = all_segments(segment_state)
    final_higher_segments = all_higher_segments(higher_level_state, min_distance)
    segment_exhaustion_flags = build_segment_exhaustion_flags(
        final_segments,
        momentum_exhaustion_state.signals,
        bars,
    )

    return {
        "bar_count": len(bars),
        "fractals": [],
        "segments": [
            {
                "direction": segment.direction,
                "start": {
                    "index": segment.start.index,
                    "time": segment.start.time,
                    "price": segment.start.price,
                },
                "end": {
                    "index": segment.end.index,
                    "time": segment.end.time,
                    "price": segment.end.price,
                },
                "is_momentum_exhaustion_segment": segment_exhaustion_flags[index],
            }
            for index, segment in enumerate(final_segments)
        ],
        "higher_segments": [
            {
                "direction": segment.direction,
                "start": {
                    "index": segment.start.index,
                    "time": segment.start.time,
                    "price": segment.start.price,
                },
                "end": {
                    "index": segment.end.index,
                    "time": segment.end.time,
                    "price": segment.end.price,
                },
            }
            for segment in final_higher_segments
        ],
        "trading_ranges": [
            {
                "top": trading_range.top,
                "bottom": trading_range.bottom,
                "left": {
                    "index": trading_range.left.index,
                    "time": trading_range.left.time,
                    "price": trading_range.left.price,
                },
                "right": {
                    "index": trading_range.right.index,
                    "time": trading_range.right.time,
                    "price": trading_range.right.price,
                },
            }
            for trading_range in trading_range_state.ranges
        ],
        "momentum_exhaustions": [
            {
                "direction": signal.direction,
                "point": {
                    "index": signal.point.index,
                    "time": signal.point.time,
                    "price": signal.point.price,
                },
                "previous_strength": signal.previous_strength,
                "current_strength": signal.current_strength,
            }
            for signal in momentum_exhaustion_state.signals
        ],
    }
