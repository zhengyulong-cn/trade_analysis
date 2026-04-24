from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel

from app.schemas.kline_data import KlineBarInput


class SegmentDirection(str, Enum):
    """线段方向枚举。"""

    UP = "up"
    DOWN = "down"


class SegmentStatus(str, Enum):
    """线段状态枚举。"""

    BUILDING = "building"
    CONFIRMED = "confirmed"


class EmaRelation(str, Enum):
    """K 线与 EMA 的相对关系。"""

    ABOVE = "above"
    BELOW = "below"
    ON = "on"


class EmaBuildState(SQLModel):
    """EMA 构建状态。

    这个对象保存的是增量构建过程中与 EMA 相关的辅助状态：
    - period: EMA 周期，当前默认为 20
    - seed_closes: EMA 尚未初始化前，用来累计前 period 根 close
    - last_ema: 上一根 K 线处理完成后的 EMA 值
    - last_relation: 上一根 K 线相对 EMA 的关系
    - warmup_bars: 第一条线段尚未建立前，缓存的预热 K 线
    - recent_kline_amplitudes: 最近若干根 K 线的振幅缓存，用于强波动旁路确认
    """

    period: int = 20
    seed_closes: list[Decimal] = Field(default_factory=list)
    last_ema: Decimal | None = None
    last_relation: EmaRelation | None = None
    warmup_bars: list[KlineBarInput] = Field(default_factory=list)
    recent_kline_amplitudes: list[Decimal] = Field(default_factory=list)


class TrendSegment(SQLModel):
    """单条线段结构。

    字段说明：
    - segment_index: 线段编号，按生成顺序递增
    - direction: 线段方向，上涨或下跌
    - status: 当前是构建中还是已确认
    - trigger_time: 触发这条线段开始构建的时间
    - first_kline_time: 当前线段内部第一根 K 线时间
    - last_kline_time: 当前线段最新处理到的 K 线时间
    - start_time / start_price: 线段起点时间与价格
    - end_time / end_price: 线段终点时间与价格
    - kline_count: 当前线段内部累计经过了多少根 K 线
    - bars_since_end: 距离当前终点极值已经过去多少根 K 线
    - confirmed_at: 若已确认，记录确认时间
    """

    segment_index: int
    direction: SegmentDirection
    status: SegmentStatus = SegmentStatus.BUILDING
    trigger_time: datetime
    first_kline_time: datetime
    last_kline_time: datetime
    start_time: datetime
    start_price: Decimal
    end_time: datetime
    end_price: Decimal
    kline_count: int = 1
    bars_since_end: int = 0
    confirmed_at: datetime | None = None


class IntervalStrategy(SQLModel):
    """单个周期的策略状态。

    一个周期（例如 5F、30F、4H）在构建过程中需要保存的完整状态都在这里：
    - interval / interval_name: 周期信息
    - ema_state: EMA 增量构建状态
    - confirmed_segments: 已确认的线段列表
    - current_segment: 当前正在延展的线段
    - pending_segment: 当前正在观察中的反向候选线段
    - processed_kline_count: 已经处理过多少根 K 线
    - last_processed_at: 最后一根处理完成的 K 线时间
    """

    interval: int
    interval_name: str | None = None
    ema_state: EmaBuildState = Field(default_factory=EmaBuildState)
    confirmed_segments: list[TrendSegment] = Field(default_factory=list)
    current_segment: TrendSegment | None = None
    pending_segment: TrendSegment | None = None
    processed_kline_count: int = 0
    last_processed_at: datetime | None = None


class StrategyContent(SQLModel):
    """整份策略 JSON 内容。

    intervals 的 key 一般是周期秒数的字符串，例如：
    - "300" -> 5F
    - "1800" -> 30F
    - "14400" -> 4H
    """

    intervals: dict[str, IntervalStrategy] = Field(default_factory=dict)


class SegmentBuildRequest(SQLModel):
    """单周期线段构建请求。"""

    symbol: str
    interval: int
    reset: bool = False


class SegmentBuildResult(SQLModel):
    """单周期线段构建结果。

    - strategy: 整份跨周期策略结果
    - interval_strategy: 本次构建的单周期结果，便于前端直接使用
    """

    strategy_id: int
    contract_id: int
    symbol: str
    exchange: str
    contract_name: str
    interval: int
    interval_name: str | None = None
    strategy: StrategyContent
    interval_strategy: IntervalStrategy


class ManagedSegmentRole(str, Enum):
    """线段管理角色。"""

    CONFIRMED = "confirmed"
    CURRENT = "current"
    PENDING = "pending"


class ManagedTrendSegment(TrendSegment):
    """线段管理视图对象。"""

    segment_role: ManagedSegmentRole


class SegmentListResult(SQLModel):
    """单周期线段列表。"""

    strategy_id: int | None = None
    contract_id: int
    symbol: str
    exchange: str
    contract_name: str
    interval: int
    interval_name: str | None = None
    items: list[ManagedTrendSegment] = Field(default_factory=list)


class SegmentBase(SQLModel):
    """线段新增/编辑基础字段。"""

    symbol: str
    interval: int
    segment_role: ManagedSegmentRole
    direction: SegmentDirection
    start_time: datetime
    start_price: Decimal
    end_time: datetime
    end_price: Decimal


class SegmentCreateRequest(SegmentBase):
    """线段新增请求。"""


class SegmentUpdateRequest(SegmentBase):
    """线段编辑请求。"""

    original_segment_role: ManagedSegmentRole
    original_segment_index: int = Field(ge=1)


class SegmentDeleteItem(SQLModel):
    """线段删除项。"""

    segment_role: ManagedSegmentRole
    segment_index: int = Field(ge=1)


class SegmentBatchDeleteRequest(SQLModel):
    """线段批量删除请求。"""

    symbol: str
    interval: int
    items: list[SegmentDeleteItem] = Field(default_factory=list)


class SegmentBatchDeleteResult(SQLModel):
    """线段批量删除结果。"""

    symbol: str
    interval: int
    deleted: int
    remaining: int


class StrategyAnalysisRead(SQLModel):
    """数据库策略记录的基础读取模型。"""

    model_config = ConfigDict(from_attributes=True)

    strategy_id: int
    contract_id: int
    strategy: str


class StrategyAnalysisDetail(SQLModel):
    """策略详情返回模型。"""

    strategy_id: int
    contract_id: int
    symbol: str
    exchange: str
    contract_name: str
    strategy: StrategyContent
