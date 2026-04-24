"""
监控模块的 API 端点

提供实时监控、历史查询和规则管理接口。
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from api.v1.schemas.monitor import (
    MonitorRequest,
    MonitorResponse,
    MonitorHistoryQuery,
    MonitorRuleCreate,
    MonitorRuleUpdate,
    MonitorRuleResponse,
)
from src.monitor.core import MonitorEngine
from src.monitor.history_manager import HistoryManager
from src.monitor.schemas import IndicatorType
from src.storage import DatabaseManager, MonitorRules

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/monitor",
    tags=["monitor"],
    responses={404: {"description": "Not found"}},
)


@router.post("/analyze", response_model=MonitorResponse)
async def analyze_monitor(request: MonitorRequest):
    """
    执行实时监控分析

    - 同步返回分析结果
    - 自动推送到所有配置的通知渠道
    - 保存历史记录到数据库

    **示例请求:**
    ```json
    {
      "stock_codes": ["600519", "AAPL"],
      "indicators": ["price_breakout", "volume_spike"],
      "with_portfolio": true,
      "account_id": 1
    }
    ```
    """
    try:
        logger.info(
            f"收到监控请求: {len(request.stock_codes)} 只股票, "
            f"指标: {[i.value for i in request.indicators]}"
        )

        # 创建监控引擎
        engine = MonitorEngine()

        # 执行监控
        results = await engine.run(
            stock_codes=request.stock_codes,
            indicators=request.indicators,
            with_portfolio=request.with_portfolio,
            account_id=request.account_id,
            notify=True,
            save_history=True,
        )

        if not results:
            return MonitorResponse(
                status="completed",
                results=[],
                error="未获取到任何监控结果",
            )

        return MonitorResponse(
            status="completed",
            results=results,
        )

    except Exception as e:
        logger.error(f"监控分析失败: {e}", exc_info=True)
        return MonitorResponse(
            status="failed",
            error=str(e),
        )


@router.get("/history", response_model=List[dict])
async def get_monitor_history(
    stock_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数量"),
    days: int = Query(7, ge=1, le=90, description="查询最近 N 天"),
):
    """
    查询监控历史记录

    - 支持按股票代码过滤
    - 支持时间范围查询
    - 返回最近的监控信号和分析摘要

    **示例:**
    - `/api/v1/monitor/history?stock_code=600519&days=7&limit=10`
    - `/api/v1/monitor/history?days=30&limit=50`
    """
    try:
        manager = HistoryManager()
        records = manager.get_recent_signals(
            stock_code=stock_code,
            limit=limit,
            days=days,
        )

        # 转换为字典列表
        return [record.model_dump() for record in records]

    except Exception as e:
        logger.error(f"查询监控历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{record_id}")
async def get_monitor_history_detail(record_id: int):
    """
    获取监控历史详情

    - 根据记录 ID 获取完整的监控报告（包含 report_json）
    - 返回解析后的完整数据

    **示例:**
    - `/api/v1/monitor/history/123`
    """
    try:
        # 直接从数据库查询指定 ID 的记录
        from src.storage import get_db, MonitorHistory
        db = get_db()
        
        with db.session_scope() as session:
            db_record = session.query(MonitorHistory).filter(
                MonitorHistory.id == record_id
            ).first()

            if not db_record:
                raise HTTPException(status_code=404, detail="监控历史记录不存在")

            # 解析 signal_types
            signal_types = json.loads(db_record.signal_types) if db_record.signal_types else []
            
            # 解析 report_json
            report_data = None
            if db_record.report_json:
                try:
                    report_data = json.loads(db_record.report_json)
                except json.JSONDecodeError:
                    logger.warning(f"无法解析记录 {record_id} 的 report_json")

            return {
                "id": db_record.id,
                "stock_code": db_record.stock_code,
                "triggered_at": db_record.triggered_at.isoformat(),
                "signal_types": signal_types,
                "summary": db_record.summary or "",
                "notified": db_record.notified,
                "created_at": db_record.created_at.isoformat(),
                "report_data": report_data,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询监控历史详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{record_id}")
async def delete_monitor_history(record_id: int):
    """
    删除单条监控历史记录

    - 根据记录 ID 删除
    - 删除后无法恢复

    **示例:**
    - `DELETE /api/v1/monitor/history/123`
    """
    try:
        from src.storage import get_db
        db = get_db()

        with db.session_scope() as session:
            from src.storage import MonitorHistory
            record = session.query(MonitorHistory).filter(
                MonitorHistory.id == record_id
            ).first()

            if not record:
                raise HTTPException(status_code=404, detail="监控历史记录不存在")

            session.delete(record)
            session.commit()

            return {"message": "记录已删除", "record_id": record_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除监控历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/batch-delete")
async def batch_delete_monitor_history(record_ids: List[int]):
    """
    批量删除监控历史记录

    - 一次性删除多条记录
    - 返回实际删除的数量

    **示例请求:**
    ```json
    [1, 2, 3, 4, 5]
    ```
    """
    try:
        from src.storage import get_db
        db = get_db()

        with db.session_scope() as session:
            from src.storage import MonitorHistory
            deleted_count = (
                session.query(MonitorHistory)
                .filter(MonitorHistory.id.in_(record_ids))
                .delete(synchronize_session=False)
            )
            session.commit()

            return {
                "message": f"已删除 {deleted_count} 条记录",
                "deleted_count": deleted_count,
            }

    except Exception as e:
        logger.error(f"批量删除监控历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """监控模块健康检查"""
    return {"status": "healthy", "module": "monitor"}


# === 监控规则管理 API ===

def _parse_rule(rule: MonitorRules) -> MonitorRuleResponse:
    """将 ORM 对象转换为响应模型"""
    indicators = json.loads(rule.indicators) if rule.indicators else []
    custom_rules = json.loads(rule.custom_rules) if rule.custom_rules else None

    return MonitorRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        stock_code=rule.stock_code,
        indicators=indicators,
        custom_rules=custom_rules,
        is_active=rule.is_active,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


@router.get("/rules", response_model=List[MonitorRuleResponse])
async def list_monitor_rules(
    user_id: Optional[str] = Query(None, description="用户ID（可选）"),
    stock_code: Optional[str] = Query(None, description="股票代码过滤"),
    is_active: Optional[bool] = Query(None, description="是否启用过滤"),
):
    """
    查询监控规则列表

    - 支持按用户ID、股票代码、启用状态过滤
    - 返回所有匹配的监控规则
    """
    try:
        db_manager = DatabaseManager()
        with db_manager.get_session() as session:
            query = session.query(MonitorRules)

            if user_id:
                query = query.filter(MonitorRules.user_id == user_id)
            if stock_code:
                query = query.filter(MonitorRules.stock_code == stock_code)
            if is_active is not None:
                query = query.filter(MonitorRules.is_active == is_active)

            rules = query.order_by(MonitorRules.updated_at.desc()).all()
            return [_parse_rule(r) for r in rules]

    except Exception as e:
        logger.error(f"查询监控规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}", response_model=MonitorRuleResponse)
async def get_monitor_rule(rule_id: int):
    """
    获取单个监控规则详情

    - 根据规则 ID 查询
    """
    try:
        db_manager = DatabaseManager()
        with db_manager.get_session() as session:
            rule = session.query(MonitorRules).filter(MonitorRules.id == rule_id).first()

            if not rule:
                raise HTTPException(status_code=404, detail="规则不存在")

            return _parse_rule(rule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询监控规则详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules", response_model=MonitorRuleResponse, status_code=201)
async def create_monitor_rule(request: MonitorRuleCreate):
    """
    创建监控规则

    - 为指定股票添加监控规则
    - 如果已存在相同股票的规则，将更新现有规则
    """
    try:
        db_manager = DatabaseManager()
        with db_manager.get_session() as session:
            # 检查是否已存在
            existing = (
                session.query(MonitorRules)
                .filter(
                    MonitorRules.stock_code == request.stock_code,
                    MonitorRules.user_id.is_(None),  # 暂时不支持多用户
                )
                .first()
            )

            if existing:
                # 更新现有规则
                existing.indicators = json.dumps([i.value for i in request.indicators])
                if request.custom_rules:
                    existing.custom_rules = json.dumps(request.custom_rules)
                existing.is_active = request.is_active
                session.commit()
                session.refresh(existing)
                rule = existing
            else:
                # 创建新规则
                rule = MonitorRules(
                    user_id=None,
                    stock_code=request.stock_code,
                    indicators=json.dumps([i.value for i in request.indicators]),
                    custom_rules=(
                        json.dumps(request.custom_rules) if request.custom_rules else None
                    ),
                    is_active=request.is_active,
                )
                session.add(rule)
                session.commit()
                session.refresh(rule)

            return _parse_rule(rule)

    except Exception as e:
        logger.error(f"创建监控规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}", response_model=MonitorRuleResponse)
async def update_monitor_rule(rule_id: int, request: MonitorRuleUpdate):
    """
    更新监控规则

    - 支持部分更新
    - 可以修改指标、自定义规则、启用状态
    """
    try:
        db_manager = DatabaseManager()
        with db_manager.get_session() as session:
            rule = session.query(MonitorRules).filter(MonitorRules.id == rule_id).first()

            if not rule:
                raise HTTPException(status_code=404, detail="规则不存在")

            # 更新字段
            if request.indicators is not None:
                rule.indicators = json.dumps([i.value for i in request.indicators])
            if request.custom_rules is not None:
                rule.custom_rules = json.dumps(request.custom_rules)
            if request.is_active is not None:
                rule.is_active = request.is_active

            session.commit()
            session.refresh(rule)

            return _parse_rule(rule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新监控规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_monitor_rule(rule_id: int):
    """
    删除监控规则

    - 根据规则 ID 删除
    - 删除后无法恢复
    """
    try:
        db_manager = DatabaseManager()
        with db_manager.get_session() as session:
            rule = session.query(MonitorRules).filter(MonitorRules.id == rule_id).first()

            if not rule:
                raise HTTPException(status_code=404, detail="规则不存在")

            session.delete(rule)
            session.commit()

            return {"message": "规则已删除", "rule_id": rule_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除监控规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/batch-delete")
async def batch_delete_monitor_rules(rule_ids: List[int]):
    """
    批量删除监控规则

    - 一次性删除多个规则
    """
    try:
        db_manager = DatabaseManager()
        with db_manager.get_session() as session:
            deleted_count = (
                session.query(MonitorRules)
                .filter(MonitorRules.id.in_(rule_ids))
                .delete(synchronize_session=False)
            )
            session.commit()

            return {
                "message": f"已删除 {deleted_count} 条规则",
                "deleted_count": deleted_count,
            }

    except Exception as e:
        logger.error(f"批量删除监控规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
