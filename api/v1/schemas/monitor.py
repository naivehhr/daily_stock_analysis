"""
监控模块的 API Schema

定义用于 Web API 的请求和响应模型。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from src.monitor.schemas import IndicatorType, MonitorResult, MonitorHistoryRecord


class MonitorRequest(BaseModel):
    """监控分析请求"""

    stock_codes: List[str] = Field(
        ..., min_length=1, max_length=50, description="股票代码列表"
    )
    indicators: List[IndicatorType] = Field(
        default=[
            IndicatorType.PRICE_BREAKOUT,
            IndicatorType.VOLUME_SPIKE,
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


class MonitorHistoryQuery(BaseModel):
    """监控历史查询请求"""

    stock_code: Optional[str] = Field(None, description="股票代码（可选）")
    limit: int = Field(default=20, ge=1, le=100, description="返回记录数量")
    days: int = Field(default=7, ge=1, le=90, description="查询最近 N 天")


# === 监控规则管理 Schema ===

class MonitorRuleCreate(BaseModel):
    """创建监控规则请求"""

    stock_code: str = Field(..., min_length=1, max_length=16, description="股票代码")
    indicators: List[IndicatorType] = Field(
        default=[
            IndicatorType.PRICE_BREAKOUT,
            IndicatorType.VOLUME_SPIKE,
        ],
        description="要监控的指标类型",
    )
    custom_rules: Optional[Dict[str, Any]] = Field(
        None, description="自定义规则配置（预留）"
    )
    is_active: bool = Field(default=True, description="是否启用")


class MonitorRuleUpdate(BaseModel):
    """更新监控规则请求"""

    indicators: Optional[List[IndicatorType]] = Field(
        None, description="要监控的指标类型"
    )
    custom_rules: Optional[Dict[str, Any]] = Field(
        None, description="自定义规则配置（预留）"
    )
    is_active: Optional[bool] = Field(None, description="是否启用")


class MonitorRuleResponse(BaseModel):
    """监控规则响应"""

    id: int
    user_id: Optional[str] = None
    stock_code: str
    indicators: List[IndicatorType]
    custom_rules: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
