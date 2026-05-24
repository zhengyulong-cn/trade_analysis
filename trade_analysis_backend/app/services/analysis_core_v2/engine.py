from .segment import advance_segment, all_segments, create_segment_state
from .types import AnalysisBar

def analyze(
    bars: list[AnalysisBar],
    max_included: int = 10,
    min_distance: int = 4,
) -> dict:
    segment_state = create_segment_state()

    del max_included
    for bar in bars:
        advance_segment(segment_state, bars[: bar.index + 1], min_distance)

    final_segments = all_segments(segment_state)

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
                "is_momentum_exhaustion_segment": False,
            }
            for segment in final_segments
        ],
        "higher_segments": [],
        "trading_ranges": [],
        "momentum_exhaustions": [],
    }
