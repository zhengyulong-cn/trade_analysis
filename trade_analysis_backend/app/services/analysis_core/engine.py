"""统一增量分析引擎。

逐根 K 线推进，每步只能用到当前已知的信息，杜绝未来函数。
"""

from .fenxing import advance_fenxing, create_fenxing_state
from .higher_level_segment import (
    advance_higher_level,
    all_higher_segments,
    create_higher_level_state,
)
from .segment import advance_segment, create_segment_state
from .trading_range import advance_trading_range, create_trading_range_state


def analyze(
    bars,
    max_included: int = 10,
    min_distance: int = 3,
) -> dict:
    """增量分析全部 K 线。"""
    fx = create_fenxing_state()
    seg = create_segment_state()
    higher = create_higher_level_state()
    tr = create_trading_range_state()

    prev_higher_count = 0

    for bar in bars:
        # 1. 分型
        new_signal = advance_fenxing(fx, bar, max_included)

        # 2. 本级别线段
        if new_signal is not None:
            advance_segment(seg, bars, fx.signals, new_signal, min_distance)

        # 3. 大级别线段
        current_segs = seg.historical + ([seg.active] if seg.active else [])
        advance_higher_level(higher, bar, bar.index, current_segs, min_distance)

        # 4. 交易区间：大级别变化时重新评估所有可用线段
        current_higher = all_higher_segments(higher, min_distance)
        if current_higher and len(current_higher) != prev_higher_count:
            prev_higher_count = len(current_higher)
            # 重新过一遍所有已知线段，只追加未处理过的
            tr.processed_segment_count = 0
            tr.ranges = []
            tr.last_feature = None
        if current_higher:
            for i in range(tr.processed_segment_count, len(current_segs)):
                advance_trading_range(tr, bars, current_segs, current_higher, i)

    # 收集结果
    final_segs = seg.historical + ([seg.active] if seg.active else [])
    final_higher = all_higher_segments(higher, min_distance)

    return {
        "bar_count": len(bars),
        "fractals": [
            {"index": s.point.index, "time": s.point.time, "price": s.point.price, "type": s.type}
            for s in fx.signals
        ],
        "segments": [
            {"direction": s.direction,
             "start": {"index": s.start.index, "time": s.start.time, "price": s.start.price},
             "end": {"index": s.end.index, "time": s.end.time, "price": s.end.price}}
            for s in final_segs
        ],
        "higher_segments": [
            {"direction": s.direction,
             "start": {"index": s.start.index, "time": s.start.time, "price": s.start.price},
             "end": {"index": s.end.index, "time": s.end.time, "price": s.end.price}}
            for s in final_higher
        ],
        "trading_ranges": [
            {"top": r.top, "bottom": r.bottom,
             "left": {"index": r.left.index, "time": r.left.time, "price": r.left.price},
             "right": {"index": r.right.index, "time": r.right.time, "price": r.right.price}}
            for r in tr.ranges
        ],
    }
