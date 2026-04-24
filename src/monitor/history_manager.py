"""
历史记录管理器

负责监控历史的持久化存储和查询。
"""

import logging
import json
from typing import List, Optional
from datetime import datetime, timedelta

from src.monitor.schemas import MonitorResult, MonitorHistoryRecord
from src.storage import get_db

logger = logging.getLogger(__name__)


class HistoryManager:
    """监控历史记录管理器"""

    def __init__(self):
        self.db = get_db()

    def save_report(self, result: MonitorResult) -> int:
        """
        保存监控报告到数据库

        Args:
            result: 监控结果

        Returns:
            新记录的 ID
        """
        try:
            # 序列化信号类型
            signal_types = [s.indicator.value for s in result.signals]

            # 构建摘要
            summary = result.llm_summary or ""
            if not summary and result.signals:
                # 如果没有 LLM 摘要，用信号描述作为摘要
                summary = "; ".join([s.description for s in result.signals[:3]])

            # 序列化为 JSON
            report_json = result.model_dump_json()

            # 保存到数据库
            record_id = self.db.save_monitor_history(
                stock_code=result.stock_code,
                triggered_at=result.timestamp,
                signal_types=signal_types,
                summary=summary,
                report_json=report_json,
                notified=True,  # 每次都通知
            )

            logger.debug(f"[{result.stock_code}] 监控历史已保存，ID: {record_id}")
            return record_id

        except Exception as e:
            logger.error(
                f"[{result.stock_code}] 保存监控历史失败: {e}", exc_info=True
            )
            raise

    def get_recent_signals(
        self,
        stock_code: Optional[str] = None,
        limit: int = 20,
        days: int = 7,
    ) -> List[MonitorHistoryRecord]:
        """
        获取最近的监控历史

        Args:
            stock_code: 股票代码（可选）
            limit: 返回记录数量
            days: 查询最近 N 天

        Returns:
            历史记录列表
        """
        try:
            records = self.db.get_monitor_history(
                stock_code=stock_code,
                limit=limit,
                days=days,
            )

            # 转换为 Pydantic 模型
            result = []
            for record in records:
                try:
                    # 解析 signal_types JSON
                    signal_types = json.loads(record.signal_types) if record.signal_types else []

                    result.append(
                        MonitorHistoryRecord(
                            id=record.id,
                            stock_code=record.stock_code,
                            triggered_at=record.triggered_at,
                            signal_types=signal_types,
                            summary=record.summary or "",
                            report_json=record.report_json,
                            notified=record.notified,
                            created_at=record.created_at,
                        )
                    )
                except Exception as e:
                    logger.warning(f"解析监控历史记录失败 (ID={record.id}): {e}")
                    continue

            return result

        except Exception as e:
            logger.error(f"查询监控历史失败: {e}", exc_info=True)
            return []

    def cleanup_old_records(self, retention_days: int = 90) -> int:
        """
        清理过期的监控历史记录

        Args:
            retention_days: 保留天数

        Returns:
            删除的记录数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            with self.db.session_scope() as session:
                from src.storage import MonitorHistory
                from sqlalchemy import delete

                result = session.execute(
                    delete(MonitorHistory).where(
                        MonitorHistory.triggered_at < cutoff_date
                    )
                )
                deleted_count = result.rowcount or 0
                session.commit()

                if deleted_count > 0:
                    logger.info(f"清理了 {deleted_count} 条过期监控历史记录")

                return deleted_count

        except Exception as e:
            logger.error(f"清理过期记录失败: {e}", exc_info=True)
            return 0
