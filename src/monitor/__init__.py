"""
盯盘监控模块

提供实时监控股票技术指标和交易信号的功能，支持：
- 多指标监控（价格突破、成交量异常、技术指标等）
- 持仓集成分析
- LLM Agent 智能分析
- 多渠道通知推送
- 历史记录持久化
"""

from src.monitor.schemas import (
    IndicatorType,
    SignalType,
    MonitorSignal,
    PortfolioContext,
    MonitorResult,
    MonitorHistoryRecord,
)
from src.monitor.core import MonitorEngine

__all__ = [
    "IndicatorType",
    "SignalType",
    "MonitorSignal",
    "PortfolioContext",
    "MonitorResult",
    "MonitorHistoryRecord",
    "MonitorEngine",
]
