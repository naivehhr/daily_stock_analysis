"""
盯盘监控模块的 Schema 定义

定义所有用于监控功能的 Pydantic 模型，包括：
- 指标类型枚举
- 信号类型枚举
- 监控信号
- 持仓上下文
- 监控结果
- 历史记录
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class IndicatorType(str, Enum):
    """监控指标类型"""

    PRICE_BREAKOUT = "price_breakout"  # 价格突破
    VOLUME_SPIKE = "volume_spike"  # 成交量异常
    MA_CROSS = "ma_cross"  # 均线交叉
    RSI_SIGNAL = "rsi_signal"  # RSI 超买超卖
    MACD_SIGNAL = "macd_signal"  # MACD 信号
    MOMENTUM = "momentum"  # 势能分析（动量、加速度）
    VOLUME_MOMENTUM = "volume_momentum"  # 量能分析（上涨/下跌角度、力量强度）
    CUSTOM = "custom"  # 自定义指标


class SignalType(str, Enum):
    """信号类型"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"


class MonitorSignal(BaseModel):
    """监控信号"""

    indicator: IndicatorType = Field(..., description="触发信号的指标类型")
    signal_type: SignalType = Field(..., description="信号类型（买入/卖出/持有/观望）")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="置信度 0-1"
    )
    value: Optional[float] = Field(None, description="指标当前值")
    threshold: Optional[float] = Field(None, description="触发阈值")
    description: str = Field(..., description="人类可读的信号描述")
    triggered_at: datetime = Field(
        default_factory=datetime.now, description="信号触发时间"
    )


class PortfolioContext(BaseModel):
    """持仓上下文信息"""

    has_position: bool = Field(default=False, description="是否持有该股票")
    quantity: float = Field(default=0.0, description="持仓数量")
    avg_cost: float = Field(default=0.0, description="平均成本价")
    current_price: float = Field(default=0.0, description="当前价格")
    unrealized_pnl: float = Field(default=0.0, description="未实现盈亏")
    pnl_pct: float = Field(default=0.0, description="盈亏百分比")
    position_ratio: float = Field(
        default=0.0, description="占仓位比例（0-1）"
    )


class MonitorResult(BaseModel):
    """单次监控分析结果"""

    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    current_price: float = Field(..., description="当前价格")
    change_pct: float = Field(..., description="涨跌幅百分比")

    # 技术指标快照
    ma5: Optional[float] = Field(None, description="5日均线")
    ma10: Optional[float] = Field(None, description="10日均线")
    ma20: Optional[float] = Field(None, description="20日均线")
    volume_ratio: Optional[float] = Field(
        None, description="成交量比率（当前/5日均量）"
    )
    rsi: Optional[float] = Field(None, description="RSI指标")
    macd_dif: Optional[float] = Field(None, description="MACD DIF")
    macd_dea: Optional[float] = Field(None, description="MACD DEA")

    # 量能分析指标
    price_angle: Optional[float] = Field(
        None, description="价格角度（上涨/下跌角度，度）"
    )
    momentum_strength: Optional[float] = Field(
        None, description="动量强度（-1到1，正为上涨力量，负为下跌力量）"
    )
    volume_power: Optional[float] = Field(
        None, description="量能力量（成交量加权的价格变化率）"
    )

    # 势能分析指标
    momentum_3d: Optional[float] = Field(
        None, description="3日动量"
    )
    momentum_5d: Optional[float] = Field(
        None, description="5日动量"
    )
    acceleration: Optional[float] = Field(
        None, description="加速度（动量变化率）"
    )

    # 检测到的信号
    signals: List[MonitorSignal] = Field(
        default_factory=list, description="检测到的交易信号列表"
    )

    # LLM 分析结果
    llm_summary: Optional[str] = Field(None, description="LLM 分析摘要")
    llm_advice: Optional[str] = Field(None, description="LLM 操作建议")
    llm_confidence: Optional[str] = Field(None, description="LLM 置信度")

    # 持仓信息
    portfolio: Optional[PortfolioContext] = Field(
        None, description="持仓上下文（如果启用持仓集成）"
    )

    # 元数据
    timestamp: datetime = Field(
        default_factory=datetime.now, description="分析时间戳"
    )
    analysis_duration_ms: int = Field(
        default=0, description="分析耗时（毫秒）"
    )
    data_sources: List[str] = Field(
        default_factory=list, description="使用的数据源列表"
    )


class MonitorHistoryRecord(BaseModel):
    """监控历史记录（用于数据库存储）"""

    id: Optional[int] = Field(None, description="记录ID")
    stock_code: str = Field(..., description="股票代码")
    triggered_at: datetime = Field(..., description="触发时间")
    signal_types: List[str] = Field(
        default_factory=list, description="信号类型列表"
    )
    summary: str = Field(default="", description="分析摘要")
    report_json: str = Field(..., description="完整的 MonitorResult JSON")
    notified: bool = Field(
        default=False, description="是否已发送通知"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )


# API 请求/响应 Schema

class MonitorRequest(BaseModel):
    """监控分析请求"""

    stock_codes: List[str] = Field(
        ..., min_length=1, max_length=50, description="股票代码列表"
    )
    indicators: List[IndicatorType] = Field(
        default=[
            IndicatorType.PRICE_BREAKOUT,
            IndicatorType.VOLUME_SPIKE,
            IndicatorType.MOMENTUM,
            IndicatorType.VOLUME_MOMENTUM,
        ],
        description="要监控的指标类型",
    )
    with_portfolio: bool = Field(
        default=False, description="是否包含持仓分析"
    )
    account_id: Optional[int] = Field(
        None, description="持仓账户ID（with_portfolio=True时必填）"
    )
    custom_rules: Optional[Dict[str, Any]] = Field(
        None, description="自定义规则配置"
    )


class MonitorResponse(BaseModel):
    """监控分析响应"""

    status: str = Field(..., description="任务状态")
    results: Optional[List[MonitorResult]] = Field(
        None, description="分析结果列表"
    )
    error: Optional[str] = Field(None, description="错误信息")
    task_id: Optional[str] = Field(None, description="任务ID（异步模式）")
