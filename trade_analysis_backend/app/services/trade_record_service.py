from collections import defaultdict
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from typing import Any

from fastapi import HTTPException, status
import pandas as pd
from sqlmodel import Session, select

from app.models.trade_fill_record import TradeFillRecord
from app.models.trade_record import TradeRecord
from app.schemas.trade_record import (
    TradeRecordAnalysisBreakdownItem,
    TradeRecordAnalysisLossStreakItem,
    TradeRecordAnalysisPeriodItem,
    TradeRecordAnalysisQuery,
    TradeRecordAnalysisResult,
    TradeRecordAnalysisSummary,
    TradeRecordCreate,
    TradeRecordImportResult,
    TradeRecordListQuery,
    TradeRecordMergeRequest,
    TradeRecordUpdate,
)
from app.services.trade_record_storage import TradeRecordStorageService


TRADE_DETAIL_CONTRACT = "合约"
TRADE_DETAIL_TRADE_NO = "成交序号"
TRADE_DETAIL_TIME = "成交时间"
TRADE_DETAIL_SIDE = "买/卖"
TRADE_DETAIL_PRICE = "成交价"
TRADE_DETAIL_LOTS = "手数"
TRADE_DETAIL_OFFSET = "开/平"
TRADE_DETAIL_FEE = "手续费"
TRADE_DETAIL_DATE = "实际成交日期"

CLOSE_DETAIL_CONTRACT = "合约"
CLOSE_DETAIL_TRADE_NO = "成交序号"
CLOSE_DETAIL_OPEN_PRICE = "开仓价"
CLOSE_DETAIL_CLOSE_PRICE = "成交价"
CLOSE_DETAIL_LOTS = "手数"
CLOSE_DETAIL_PNL = "平仓盈亏"
CLOSE_DETAIL_ORIGINAL_TRADE_NO = "原成交序号"

SIDE_BUY = "buy"
SIDE_SELL = "sell"
OFFSET_OPEN = "open"
OFFSET_CLOSE = "close"
SOURCE_MANUAL = "manual"
SOURCE_IMPORT = "import"
TRADE_NO_LENGTH = 18


class TradeRecordService:
    def __init__(self, session: Session, storage_service: TradeRecordStorageService):
        self.session = session
        self.storage_service = storage_service

    def list_trade_records(self, query: TradeRecordListQuery) -> list[TradeRecord]:
        statement = select(TradeRecord)

        if query.contract:
            statement = statement.where(TradeRecord.contract.contains(query.contract.strip()))
        if query.open_direction:
            statement = statement.where(TradeRecord.open_direction == query.open_direction)
        if query.segment_type:
            statement = statement.where(TradeRecord.segment_type == query.segment_type)
        if query.open_signal:
            statement = statement.where(TradeRecord.open_signal == query.open_signal)
        if query.open_time_start:
            statement = statement.where(TradeRecord.open_time >= query.open_time_start)
        if query.open_time_end:
            statement = statement.where(TradeRecord.open_time <= query.open_time_end)
        if query.close_time_start:
            statement = statement.where(TradeRecord.close_time >= query.close_time_start)
        if query.close_time_end:
            statement = statement.where(TradeRecord.close_time <= query.close_time_end)

        statement = statement.order_by(TradeRecord.open_time, TradeRecord.trade_record_id)
        return list(self.session.exec(statement).all())

    def analyze_trade_records(self, query: TradeRecordAnalysisQuery) -> TradeRecordAnalysisResult:
        records = self._list_closed_trade_records_for_analysis(query)
        records.sort(key=lambda item: (item.open_time, item.trade_record_id or 0))

        summary = self._build_analysis_summary(records)
        period_series = self._build_period_series(records, query.period_type)

        return TradeRecordAnalysisResult(
            summary=summary,
            period_series=period_series,
            by_contract=self._build_breakdown(records, lambda item: item.contract, lambda value: value or "未填写"),
            by_direction=self._build_breakdown(records, lambda item: item.open_direction, self._format_open_direction),
            by_segment_type=self._build_breakdown(records, lambda item: item.segment_type, self._format_segment_type),
            by_open_signal=self._build_breakdown(records, lambda item: item.open_signal, self._format_open_signal),
            continuous_loss_periods=[] if query.period_type != "day" else self._build_continuous_loss_periods(period_series),
            high_frequency_periods=[
                item
                for item in period_series
                if "high_frequency" in item.risk_flags
            ],
            execution_worse_periods=[item for item in period_series if "execution_worse" in item.risk_flags],
        )

    def create_trade_record(self, payload: TradeRecordCreate) -> TradeRecord:
        trade_record = TradeRecord.model_validate(
            {
                **payload.model_dump(),
                "source": SOURCE_MANUAL,
            }
        )
        self._validate_time_range(trade_record.open_time, trade_record.close_time)
        self.session.add(trade_record)
        self.session.commit()
        self.session.refresh(trade_record)
        return trade_record

    def import_trade_records_from_excel(self, file_bytes: bytes, file_name: str | None = None) -> TradeRecordImportResult:
        try:
            trade_details = self._load_statement_sheet(file_bytes, sheet_index=2)
            close_details = self._load_statement_sheet(file_bytes, sheet_index=3)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to parse trade record workbook",
            ) from exc

        trade_details = self._clean_sheet_rows(trade_details)
        close_details = self._clean_sheet_rows(close_details)

        close_detail_index = self._build_close_detail_index(close_details)
        fill_records_by_trade_no = self._load_fill_records_by_trade_no()

        imported = 0
        skipped = 0
        failed = 0

        for _, row in trade_details.iterrows():
            try:
                trade_no = self._normalize_trade_no(row.get(TRADE_DETAIL_TRADE_NO))
                if not trade_no:
                    failed += 1
                    continue

                close_detail = close_detail_index.get(trade_no)
                trade_fill = fill_records_by_trade_no.get(trade_no)
                is_new = trade_fill is None
                if trade_fill is None:
                    trade_fill = TradeFillRecord(
                        trade_no=trade_no,
                        contract=str(row.get(TRADE_DETAIL_CONTRACT)).strip(),
                        side=self._resolve_side(row.get(TRADE_DETAIL_SIDE)),
                        offset=self._resolve_offset(row.get(TRADE_DETAIL_OFFSET)),
                        trade_time=self._combine_trade_datetime(
                            row.get(TRADE_DETAIL_DATE),
                            row.get(TRADE_DETAIL_TIME),
                        ),
                        price=self._to_decimal(row.get(TRADE_DETAIL_PRICE)),
                        lots=self._to_int(row.get(TRADE_DETAIL_LOTS)),
                        fee=self._to_decimal(row.get(TRADE_DETAIL_FEE)),
                        source_file_name=file_name,
                    )
                    self.session.add(trade_fill)
                    fill_records_by_trade_no[trade_no] = trade_fill
                else:
                    trade_fill.contract = str(row.get(TRADE_DETAIL_CONTRACT)).strip()
                    trade_fill.side = self._resolve_side(row.get(TRADE_DETAIL_SIDE))
                    trade_fill.offset = self._resolve_offset(row.get(TRADE_DETAIL_OFFSET))
                    trade_fill.trade_time = self._combine_trade_datetime(
                        row.get(TRADE_DETAIL_DATE),
                        row.get(TRADE_DETAIL_TIME),
                    )
                    trade_fill.price = self._to_decimal(row.get(TRADE_DETAIL_PRICE))
                    trade_fill.lots = self._to_int(row.get(TRADE_DETAIL_LOTS))
                    trade_fill.fee = self._to_decimal(row.get(TRADE_DETAIL_FEE))
                    trade_fill.source_file_name = file_name
                    trade_fill.updated_at = datetime.now(timezone.utc)

                if close_detail is not None:
                    trade_fill.matched_open_trade_no = close_detail["original_trade_no"]
                    trade_fill.close_pnl = self._to_decimal(close_detail["pnl"])
                else:
                    trade_fill.matched_open_trade_no = None
                    trade_fill.close_pnl = None

                if is_new:
                    imported += 1
                else:
                    skipped += 1
            except Exception:
                failed += 1

        self.session.commit()
        generated_count = self._sync_import_trade_records()
        return TradeRecordImportResult(
            imported=imported,
            skipped=skipped,
            failed=failed,
            message=f"导入成交明细 {imported} 条，更新 {skipped} 条，失败 {failed} 条；同步交易记录 {generated_count} 条",
        )

    def update_trade_record(self, payload: TradeRecordUpdate) -> TradeRecord:
        trade_record = self.get_trade_record_by_id(payload.trade_record_id)
        update_data = payload.model_dump(exclude={"trade_record_id"}, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No trade record fields to update",
            )

        old_screenshot_paths = self._extract_screenshot_paths(trade_record.screenshots)

        for field_name, value in update_data.items():
            setattr(trade_record, field_name, value)

        self._validate_time_range(trade_record.open_time, trade_record.close_time)
        trade_record.updated_at = datetime.now(timezone.utc)
        self.session.add(trade_record)
        self.session.commit()
        self.session.refresh(trade_record)

        current_screenshot_paths = self._extract_screenshot_paths(trade_record.screenshots)
        for orphan_path in old_screenshot_paths - current_screenshot_paths:
            self.storage_service.delete_relative_path(orphan_path)

        return trade_record

    def merge_trade_records(self, payload: TradeRecordMergeRequest) -> TradeRecord:
        trade_record_ids = list(dict.fromkeys(payload.trade_record_ids))
        if len(trade_record_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 trade records are required for merge",
            )

        statement = select(TradeRecord).where(TradeRecord.trade_record_id.in_(trade_record_ids))
        records = list(self.session.exec(statement).all())
        if len(records) != len(trade_record_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more trade records were not found",
            )

        records.sort(key=lambda item: item.trade_record_id or 0)
        self._validate_merge_records(records)

        merged_record = TradeRecord(
            contract=records[0].contract,
            source=SOURCE_MANUAL,
            open_direction=records[0].open_direction,
            lots=sum(item.lots for item in records),
            open_time=min(item.open_time for item in records),
            open_price=self._weighted_average_price(records, "open_price"),
            close_time=max(item.close_time for item in records if item.close_time is not None),
            close_price=self._weighted_average_price(records, "close_price"),
            segment_type=self._merge_segment_type(records),
            tags=self._merge_tags(records),
            fee=sum((item.fee for item in records), Decimal("0")),
            actual_pnl=sum((item.actual_pnl or Decimal("0") for item in records), Decimal("0")),
            screenshots=self._merge_screenshots(records),
            comment=self._merge_comments(records),
        )
        self._validate_time_range(merged_record.open_time, merged_record.close_time)
        self.session.add(merged_record)
        self.session.flush()

        self._exclude_import_fill_records(records)

        screenshot_paths = set()
        for record in records:
            screenshot_paths.update(self._extract_screenshot_paths(record.screenshots))
            self.session.delete(record)

        self.session.commit()
        self.session.refresh(merged_record)
        return merged_record

    def delete_trade_record(self, trade_record_id: int) -> None:
        trade_record = self.get_trade_record_by_id(trade_record_id)
        screenshot_paths = self._extract_screenshot_paths(trade_record.screenshots)
        self.session.delete(trade_record)
        self.session.commit()
        for screenshot_path in screenshot_paths:
            self.storage_service.delete_relative_path(screenshot_path)

    def get_trade_record_by_id(self, trade_record_id: int) -> TradeRecord:
        trade_record = self.session.get(TradeRecord, trade_record_id)
        if trade_record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade record not found: {trade_record_id}",
            )
        return trade_record

    def _list_closed_trade_records_for_analysis(self, query: TradeRecordAnalysisQuery) -> list[TradeRecord]:
        statement = select(TradeRecord).where(
            TradeRecord.close_time.is_not(None),
            TradeRecord.close_price.is_not(None),
            TradeRecord.actual_pnl.is_not(None),
        )

        if query.contract:
            statement = statement.where(TradeRecord.contract.contains(query.contract.strip()))
        if query.open_direction:
            statement = statement.where(TradeRecord.open_direction == query.open_direction)
        if query.segment_type:
            statement = statement.where(TradeRecord.segment_type == query.segment_type)
        if query.open_signal:
            statement = statement.where(TradeRecord.open_signal == query.open_signal)
        if query.open_time_start:
            statement = statement.where(TradeRecord.open_time >= query.open_time_start)
        if query.open_time_end:
            statement = statement.where(TradeRecord.open_time <= query.open_time_end)

        statement = statement.order_by(TradeRecord.open_time, TradeRecord.trade_record_id)
        return list(self.session.exec(statement).all())

    def _build_analysis_summary(self, records: list[TradeRecord]) -> TradeRecordAnalysisSummary:
        metrics = self._calculate_record_metrics(records)
        trading_days = len({item.open_time.date() for item in records})
        return TradeRecordAnalysisSummary(
            **metrics,
            trading_days=trading_days,
            avg_trades_per_day=self._safe_float(metrics["trade_count"], trading_days),
        )

    def _build_period_series(
        self,
        records: list[TradeRecord],
        period_type: str,
    ) -> list[TradeRecordAnalysisPeriodItem]:
        grouped_records: dict[tuple[date, date], list[TradeRecord]] = defaultdict(list)
        for record in records:
            grouped_records[self._get_period_bounds(record.open_time.date(), period_type)].append(record)

        period_series: list[TradeRecordAnalysisPeriodItem] = []
        cumulative_net_pnl = Decimal("0")
        previous_item: TradeRecordAnalysisPeriodItem | None = None
        previous_bad_signal_rate: float | None = None

        for period_start, period_end in sorted(grouped_records.keys()):
            period_records = grouped_records[(period_start, period_end)]
            metrics = self._calculate_record_metrics(period_records)
            cumulative_net_pnl += metrics["net_pnl"]
            bad_signal_rate = self._calculate_bad_signal_rate(period_records)

            risk_flags = self._build_period_risk_flags(
                metrics=metrics,
                bad_signal_rate=bad_signal_rate,
                previous_item=previous_item,
                previous_bad_signal_rate=previous_bad_signal_rate,
            )
            current_item = TradeRecordAnalysisPeriodItem(
                period_label=self._format_period_label(period_start, period_end, period_type),
                period_start=period_start,
                period_end=period_end,
                **metrics,
                cumulative_net_pnl=cumulative_net_pnl,
                net_pnl_change=None if previous_item is None else metrics["net_pnl"] - previous_item.net_pnl,
                trade_count_change=None
                if previous_item is None
                else metrics["trade_count"] - previous_item.trade_count,
                win_rate_change=None
                if previous_item is None or metrics["win_rate"] is None or previous_item.win_rate is None
                else metrics["win_rate"] - previous_item.win_rate,
                risk_flags=risk_flags,
            )
            period_series.append(current_item)
            previous_item = current_item
            previous_bad_signal_rate = bad_signal_rate

        return period_series

    def _build_breakdown(
        self,
        records: list[TradeRecord],
        key_getter,
        label_getter,
    ) -> list[TradeRecordAnalysisBreakdownItem]:
        grouped_records: dict[str | None, list[TradeRecord]] = defaultdict(list)
        for record in records:
            grouped_records[key_getter(record)].append(record)

        items: list[TradeRecordAnalysisBreakdownItem] = []
        for key, group_records in grouped_records.items():
            metrics = self._calculate_record_metrics(group_records)
            items.append(
                TradeRecordAnalysisBreakdownItem(
                    key=key,
                    label=label_getter(key),
                    **metrics,
                )
            )

        return sorted(items, key=lambda item: (item.net_pnl, item.trade_count), reverse=True)

    def _calculate_record_metrics(self, records: list[TradeRecord]) -> dict[str, Any]:
        trade_count = len(records)
        total_lots = sum(item.lots for item in records)
        gross_pnl = sum((item.actual_pnl or Decimal("0") for item in records), Decimal("0"))
        total_fee = sum((item.fee for item in records), Decimal("0"))
        net_pnl = gross_pnl - total_fee
        net_pnls = [self._get_net_pnl(item) for item in records]
        win_count = sum(1 for value in net_pnls if value > 0)
        loss_count = sum(1 for value in net_pnls if value < 0)
        empty_signal_count = sum(1 for item in records if item.open_signal is None)
        invalid_signal_count = sum(1 for item in records if item.open_signal == "not_matching_open_signal")
        valid_signal_count = trade_count - empty_signal_count - invalid_signal_count

        return {
            "trade_count": trade_count,
            "total_lots": total_lots,
            "gross_pnl": gross_pnl,
            "total_fee": total_fee,
            "net_pnl": net_pnl,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": self._safe_float(win_count, trade_count),
            "avg_net_pnl": None if trade_count == 0 else net_pnl / Decimal(trade_count),
            "empty_signal_count": empty_signal_count,
            "invalid_signal_count": invalid_signal_count,
            "valid_signal_count": valid_signal_count,
            "signal_coverage_rate": self._safe_float(trade_count - empty_signal_count, trade_count),
            "invalid_signal_rate": self._safe_float(invalid_signal_count, trade_count),
        }

    def _build_period_risk_flags(
        self,
        metrics: dict[str, Any],
        bad_signal_rate: float | None,
        previous_item: TradeRecordAnalysisPeriodItem | None,
        previous_bad_signal_rate: float | None,
    ) -> list[str]:
        risk_flags: list[str] = []
        if metrics["trade_count"] >= 5:
            risk_flags.append("high_frequency")
        if previous_item is None:
            return risk_flags
        if metrics["win_rate"] is not None and previous_item.win_rate is not None:
            if metrics["win_rate"] - previous_item.win_rate <= -0.2:
                risk_flags.append("win_rate_down")
        if bad_signal_rate is not None and previous_bad_signal_rate is not None:
            if bad_signal_rate - previous_bad_signal_rate >= 0.2:
                risk_flags.append("execution_worse")

        return risk_flags

    def _calculate_bad_signal_rate(self, records: list[TradeRecord]) -> float | None:
        if not records:
            return None
        bad_signal_count = sum(
            1
            for item in records
            if item.open_signal is None or item.open_signal == "not_matching_open_signal"
        )
        return bad_signal_count / len(records)

    def _build_continuous_loss_periods(
        self,
        period_series: list[TradeRecordAnalysisPeriodItem],
    ) -> list[TradeRecordAnalysisLossStreakItem]:
        streaks: list[TradeRecordAnalysisLossStreakItem] = []
        current_streak: list[TradeRecordAnalysisPeriodItem] = []

        for item in period_series:
            if item.net_pnl < 0:
                current_streak.append(item)
            elif current_streak:
                streaks.append(self._build_loss_streak_item(current_streak))
                current_streak = []

        if current_streak:
            streaks.append(self._build_loss_streak_item(current_streak))

        return streaks

    def _build_loss_streak_item(
        self,
        streak_items: list[TradeRecordAnalysisPeriodItem],
    ) -> TradeRecordAnalysisLossStreakItem:
        trade_count = sum(item.trade_count for item in streak_items)
        gross_pnl = sum((item.gross_pnl for item in streak_items), Decimal("0"))
        total_fee = sum((item.total_fee for item in streak_items), Decimal("0"))
        net_pnl = sum((item.net_pnl for item in streak_items), Decimal("0"))
        win_count = sum(item.win_count for item in streak_items)
        loss_count = sum(item.loss_count for item in streak_items)

        return TradeRecordAnalysisLossStreakItem(
            streak_length=len(streak_items),
            start_period_label=streak_items[0].period_label,
            end_period_label=streak_items[-1].period_label,
            start_period_start=streak_items[0].period_start,
            end_period_end=streak_items[-1].period_end,
            trade_count=trade_count,
            gross_pnl=gross_pnl,
            total_fee=total_fee,
            net_pnl=net_pnl,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=self._safe_float(win_count, trade_count),
        )

    def _get_net_pnl(self, record: TradeRecord) -> Decimal:
        return (record.actual_pnl or Decimal("0")) - record.fee

    def _safe_float(self, numerator: int | Decimal, denominator: int) -> float | None:
        if denominator <= 0:
            return None
        return float(numerator / denominator)

    def _get_period_bounds(self, current_date: date, period_type: str) -> tuple[date, date]:
        if period_type == "day":
            return current_date, current_date
        if period_type == "week":
            start = current_date - timedelta(days=current_date.weekday())
            return start, start + timedelta(days=6)
        if period_type == "half_month":
            if current_date.day <= 14:
                return current_date.replace(day=1), current_date.replace(day=14)
            last_day = monthrange(current_date.year, current_date.month)[1]
            return current_date.replace(day=15), current_date.replace(day=last_day)
        if period_type == "month":
            last_day = monthrange(current_date.year, current_date.month)[1]
            return current_date.replace(day=1), current_date.replace(day=last_day)
        raise ValueError(f"Unsupported period type: {period_type}")

    def _format_period_label(self, period_start: date, period_end: date, period_type: str) -> str:
        if period_type == "day":
            return period_start.isoformat()
        if period_type == "week":
            return f"{period_start.isoformat()} ~ {period_end.isoformat()}"
        if period_type == "half_month":
            half_label = "上半月" if period_start.day == 1 else "下半月"
            return f"{period_start:%Y-%m} {half_label}"
        if period_type == "month":
            return f"{period_start:%Y-%m}"
        return f"{period_start.isoformat()} ~ {period_end.isoformat()}"

    def _format_open_direction(self, value: str | None) -> str:
        return {"long": "多单", "short": "空单"}.get(value or "", "未填写")

    def _format_segment_type(self, value: str | None) -> str:
        return {
            "trend_push": "趋势推动段",
            "trend_pullback": "趋势回调段",
            "range_internal": "区间内部段",
            "false_break_range_transition": "（假突破）回调转区间段",
            "true_break_trend_push_transition": "（真突破）区间转推动段",
        }.get(value or "", "未填写")

    def _format_open_signal(self, value: str | None) -> str:
        return {
            "ema20_resistance_key_level_confirmed": "EMA20阻力+站稳关键位",
            "ema120_resistance_head_shoulders": "EMA120阻力+头肩顶/头肩底",
            "ema120_resistance_three_push_wedge": "EMA120阻力+三推楔形",
            "ema120_resistance_range_break_pullback": "EMA120阻力+突破交易区间然后回拉",
            "range_edge_multiple_breakout_failures": "区间上下轨附近+两次以上尝试突破受阻",
            "not_matching_open_signal": "不符合开仓信号",
        }.get(value or "", "未填写")

    def _sync_import_trade_records(self) -> int:
        fill_records = list(self.session.exec(select(TradeFillRecord).order_by(TradeFillRecord.trade_time)).all())
        open_fills = [item for item in fill_records if item.offset == OFFSET_OPEN and not item.is_excluded_from_sync]
        close_fills = [item for item in fill_records if item.offset == OFFSET_CLOSE]

        close_fill_map: dict[str, list[TradeFillRecord]] = defaultdict(list)
        for close_fill in close_fills:
            if close_fill.matched_open_trade_no:
                close_fill_map[close_fill.matched_open_trade_no].append(close_fill)

        for items in close_fill_map.values():
            items.sort(key=lambda item: item.trade_time)

        existing_import_records = list(
            self.session.exec(select(TradeRecord).where(TradeRecord.source == SOURCE_IMPORT)).all()
        )
        existing_records_by_key: dict[tuple[str, str], list[TradeRecord]] = defaultdict(list)
        existing_records_by_open_key: dict[str, list[TradeRecord]] = defaultdict(list)
        for item in existing_import_records:
            record_key = self._build_import_record_key(item.import_open_trade_no, item.import_close_trade_no)
            open_key = self._normalize_trade_no(item.import_open_trade_no) or ""
            existing_records_by_key[record_key].append(item)
            existing_records_by_open_key[open_key].append(item)

        generated_keys: set[tuple[str, str]] = set()
        deleted_record_ids: set[int] = set()

        for open_fill in open_fills:
            if not open_fill.trade_no:
                continue

            open_key = self._normalize_trade_no(open_fill.trade_no) or ""
            current_keys_for_open: set[tuple[str, str]] = set()
            all_related_close_fills = close_fill_map.get(open_fill.trade_no, [])
            related_close_fills = [item for item in all_related_close_fills if not item.is_excluded_from_sync]
            matched_close_lots = 0
            consumed_close_lots = sum(item.lots for item in all_related_close_fills)

            for close_fill in related_close_fills:
                matched_close_lots += close_fill.lots
                record_key = self._build_import_record_key(open_fill.trade_no, close_fill.trade_no)
                current_keys_for_open.add(record_key)
                generated_keys.add(record_key)
                matching_records = existing_records_by_key.get(record_key, [])
                trade_record = matching_records[0] if matching_records else None
                for duplicate_record in matching_records[1:]:
                    duplicate_id = duplicate_record.trade_record_id
                    if duplicate_id is not None and duplicate_id not in deleted_record_ids:
                        self.session.delete(duplicate_record)
                        deleted_record_ids.add(duplicate_id)
                if trade_record is None:
                    trade_record = TradeRecord(
                        contract=open_fill.contract,
                        source=SOURCE_IMPORT,
                        open_direction=self._resolve_open_direction_from_fill_side(open_fill.side),
                        lots=close_fill.lots,
                        open_time=open_fill.trade_time,
                        open_price=open_fill.price,
                        close_time=close_fill.trade_time,
                        close_price=close_fill.price,
                        segment_type=None,
                        tags=[],
                        fee=Decimal("0"),
                        actual_pnl=close_fill.close_pnl,
                        import_open_trade_no=open_fill.trade_no,
                        import_close_trade_no=close_fill.trade_no,
                        screenshots=[],
                        comment=None,
                    )
                trade_record.contract = open_fill.contract
                trade_record.source = SOURCE_IMPORT
                trade_record.open_direction = self._resolve_open_direction_from_fill_side(open_fill.side)
                trade_record.lots = close_fill.lots
                trade_record.open_time = open_fill.trade_time
                trade_record.open_price = open_fill.price
                trade_record.close_time = close_fill.trade_time
                trade_record.close_price = close_fill.price
                trade_record.tags = []
                trade_record.fee = self._allocate_fee(open_fill.fee, close_fill.lots, open_fill.lots) + close_fill.fee
                trade_record.actual_pnl = close_fill.close_pnl
                trade_record.import_open_trade_no = open_fill.trade_no
                trade_record.import_close_trade_no = close_fill.trade_no
                trade_record.updated_at = datetime.now(timezone.utc)
                self._validate_time_range(trade_record.open_time, trade_record.close_time)
                self.session.add(trade_record)

            remaining_lots = max(open_fill.lots - consumed_close_lots, 0)
            if remaining_lots > 0:
                record_key = self._build_import_record_key(open_fill.trade_no, None)
                current_keys_for_open.add(record_key)
                generated_keys.add(record_key)
                matching_records = existing_records_by_key.get(record_key, [])
                trade_record = matching_records[0] if matching_records else None
                for duplicate_record in matching_records[1:]:
                    duplicate_id = duplicate_record.trade_record_id
                    if duplicate_id is not None and duplicate_id not in deleted_record_ids:
                        self.session.delete(duplicate_record)
                        deleted_record_ids.add(duplicate_id)
                if trade_record is None:
                    trade_record = TradeRecord(
                        contract=open_fill.contract,
                        source=SOURCE_IMPORT,
                        open_direction=self._resolve_open_direction_from_fill_side(open_fill.side),
                        lots=remaining_lots,
                        open_time=open_fill.trade_time,
                        open_price=open_fill.price,
                        close_time=None,
                        close_price=None,
                        segment_type=None,
                        tags=[],
                        fee=Decimal("0"),
                        actual_pnl=None,
                        import_open_trade_no=open_fill.trade_no,
                        import_close_trade_no=None,
                        screenshots=[],
                        comment=None,
                    )
                trade_record.contract = open_fill.contract
                trade_record.source = SOURCE_IMPORT
                trade_record.open_direction = self._resolve_open_direction_from_fill_side(open_fill.side)
                trade_record.lots = remaining_lots
                trade_record.open_time = open_fill.trade_time
                trade_record.open_price = open_fill.price
                trade_record.close_time = None
                trade_record.close_price = None
                trade_record.tags = []
                trade_record.fee = self._allocate_fee(open_fill.fee, remaining_lots, open_fill.lots)
                trade_record.actual_pnl = None
                trade_record.import_open_trade_no = open_fill.trade_no
                trade_record.import_close_trade_no = None
                trade_record.updated_at = datetime.now(timezone.utc)
                self.session.add(trade_record)

            for existing_record in existing_records_by_open_key.get(open_key, []):
                existing_id = existing_record.trade_record_id
                if existing_id is not None and existing_id in deleted_record_ids:
                    continue
                existing_key = self._build_import_record_key(
                    existing_record.import_open_trade_no,
                    existing_record.import_close_trade_no,
                )
                if existing_key not in current_keys_for_open:
                    self.session.delete(existing_record)
                    if existing_id is not None:
                        deleted_record_ids.add(existing_id)

        stale_records = [
            item
            for item in existing_import_records
            if self._build_import_record_key(item.import_open_trade_no, item.import_close_trade_no) not in generated_keys
            and (item.trade_record_id is None or item.trade_record_id not in deleted_record_ids)
        ]
        for stale_record in stale_records:
            self.session.delete(stale_record)

        self.session.commit()
        return len(generated_keys)

    def _build_close_detail_index(self, dataframe: pd.DataFrame) -> dict[str, dict[str, Any]]:
        close_detail_index: dict[str, dict[str, Any]] = {}
        for _, row in dataframe.iterrows():
            close_trade_no = self._normalize_trade_no(row.get(CLOSE_DETAIL_TRADE_NO))
            original_trade_no = self._normalize_trade_no(row.get(CLOSE_DETAIL_ORIGINAL_TRADE_NO))
            if not close_trade_no or not original_trade_no:
                continue
            close_detail_index[close_trade_no] = {
                "contract": str(row.get(CLOSE_DETAIL_CONTRACT)).strip(),
                "close_price": row.get(CLOSE_DETAIL_CLOSE_PRICE),
                "open_price": row.get(CLOSE_DETAIL_OPEN_PRICE),
                "lots": row.get(CLOSE_DETAIL_LOTS),
                "pnl": row.get(CLOSE_DETAIL_PNL),
                "original_trade_no": original_trade_no,
            }
        return close_detail_index

    def _load_fill_records_by_trade_no(self) -> dict[str, TradeFillRecord]:
        fill_records = self.session.exec(select(TradeFillRecord)).all()
        return {item.trade_no: item for item in fill_records}

    def _build_import_record_key(
        self,
        import_open_trade_no: str | None,
        import_close_trade_no: str | None,
    ) -> tuple[str, str]:
        open_key = self._normalize_trade_no(import_open_trade_no) or ""
        close_key = self._normalize_trade_no(import_close_trade_no) or ""
        return (open_key, close_key)

    def _validate_merge_records(self, records: list[TradeRecord]) -> None:
        first_record = records[0]
        contract = first_record.contract
        open_direction = first_record.open_direction

        for record in records:
            if record.contract != contract:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only trade records with the same contract can be merged",
                )
            if record.open_direction != open_direction:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only trade records with the same open direction can be merged",
                )
            if record.close_time is None or record.close_price is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only closed trade records can be merged",
                )

    def _weighted_average_price(self, records: list[TradeRecord], field_name: str) -> Decimal:
        total_lots = sum(item.lots for item in records)
        weighted_sum = sum(
            (getattr(item, field_name) or Decimal("0")) * Decimal(item.lots)
            for item in records
        )
        if total_lots <= 0:
            return Decimal("0")
        return (weighted_sum / Decimal(total_lots)).quantize(Decimal("0.01"))

    def _merge_segment_type(self, records: list[TradeRecord]) -> str | None:
        segment_types = {item.segment_type for item in records if item.segment_type}
        if len(segment_types) == 1:
            return next(iter(segment_types))
        return None

    def _merge_screenshots(self, records: list[TradeRecord]) -> list[dict]:
        screenshots: list[dict] = []
        seen_paths: set[str] = set()
        for record in records:
            for item in record.screenshots or []:
                if not isinstance(item, dict):
                    continue
                path = item.get("path")
                if path and path not in seen_paths:
                    screenshots.append(item)
                    seen_paths.add(path)
        return screenshots

    def _merge_tags(self, records: list[TradeRecord]) -> list[str]:
        tags: list[str] = []
        seen_tags: set[str] = set()
        for record in records:
            for item in record.tags or []:
                if item not in seen_tags:
                    tags.append(item)
                    seen_tags.add(item)
        return tags

    def _merge_comments(self, records: list[TradeRecord]) -> str | None:
        comments = [item.comment.strip() for item in records if item.comment and item.comment.strip()]
        if not comments:
            return None
        return "\n\n".join(comments)

    def _exclude_import_fill_records(self, records: list[TradeRecord]) -> None:
        close_trade_nos = {
            item.import_close_trade_no
            for item in records
            if item.source == SOURCE_IMPORT and item.import_close_trade_no
        }
        if not close_trade_nos:
            return

        statement = select(TradeFillRecord).where(TradeFillRecord.trade_no.in_(close_trade_nos))
        fill_records = self.session.exec(statement).all()
        for fill_record in fill_records:
            fill_record.is_excluded_from_sync = True
            fill_record.updated_at = datetime.now(timezone.utc)
            self.session.add(fill_record)

    def _validate_time_range(self, open_time: datetime, close_time: datetime | None) -> None:
        if close_time is not None and close_time < open_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="close_time must be greater than or equal to open_time",
            )

    def _extract_screenshot_paths(self, screenshots: list[dict] | None) -> set[str]:
        if not screenshots:
            return set()

        paths = set()
        for item in screenshots:
            path = item.get("path") if isinstance(item, dict) else None
            if path:
                paths.add(path)
        return paths

    def _clean_sheet_rows(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        cleaned = dataframe.copy()
        cleaned = cleaned[cleaned[TRADE_DETAIL_CONTRACT].notna()]
        cleaned = cleaned[cleaned[TRADE_DETAIL_CONTRACT] != "鍚堣"]
        return cleaned

    def _extract_trade_no(self, value: object) -> str | None:
        if value is None or pd.isna(value):
            return None
        digits = "".join(ch for ch in str(value).strip() if ch.isdigit())
        if not digits:
            return None
        return digits

    def _normalize_trade_no(self, value: object) -> str | None:
        digits = self._extract_trade_no(value)
        if not digits:
            return None
        if len(digits) > TRADE_NO_LENGTH:
            return digits
        return digits.zfill(TRADE_NO_LENGTH)

    def _combine_trade_datetime(self, trade_date: object, trade_time: object) -> datetime:
        if trade_date is None or trade_time is None or pd.isna(trade_date) or pd.isna(trade_time):
            raise ValueError("Missing trade date or trade time")
        combined = datetime.strptime(
            f"{str(trade_date).strip()} {str(trade_time).strip()}",
            "%Y-%m-%d %H:%M:%S",
        )
        if combined.hour >= 20:
            combined = combined - timedelta(days=1)
        return combined

    def _resolve_side(self, side_value: object) -> str:
        side = str(side_value).strip()
        if side == "买":
            return SIDE_BUY
        if side == "卖":
            return SIDE_SELL
        raise ValueError(f"Unsupported side: {side}")

    def _resolve_offset(self, offset_value: object) -> str:
        offset = str(offset_value).strip()
        if offset == "开":
            return OFFSET_OPEN
        if offset == "平":
            return OFFSET_CLOSE
        raise ValueError(f"Unsupported offset: {offset}")

    def _resolve_open_direction_from_fill_side(self, side: str) -> str:
        if side == SIDE_BUY:
            return "long"
        if side == SIDE_SELL:
            return "short"
        raise ValueError(f"Unsupported fill side: {side}")

    def _to_decimal(self, value: object) -> Decimal:
        if value is None or pd.isna(value) or str(value).strip() == "--":
            return Decimal("0")
        return Decimal(str(value).strip())

    def _to_int(self, value: object) -> int:
        if value is None or pd.isna(value):
            return 0
        return int(Decimal(str(value).strip()))

    def _allocate_fee(self, total_fee_value: object, matched_lots: int, total_lots: int) -> Decimal:
        total_fee = self._to_decimal(total_fee_value)
        if total_lots <= 0:
            return total_fee
        return (total_fee * Decimal(matched_lots) / Decimal(total_lots)).quantize(Decimal("0.01"))

    def _load_statement_sheet(self, file_bytes: bytes, sheet_index: int) -> pd.DataFrame:
        dataframe = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_index, header=8)
        if dataframe.empty:
            raise ValueError("Statement sheet is empty")

        header_row = dataframe.iloc[0].tolist()
        normalized_headers = [str(value).strip() if not pd.isna(value) else "" for value in header_row]
        normalized_dataframe = dataframe.iloc[1:].copy().reset_index(drop=True)
        normalized_dataframe.columns = normalized_headers
        return normalized_dataframe
