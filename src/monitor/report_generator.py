"""
报告生成器

将监控结果格式化为可读的通知文本，支持有信号和无信号两种场景。
"""

import logging
from datetime import datetime
from typing import Optional

from src.monitor.schemas import MonitorResult, SignalType

logger = logging.getLogger(__name__)


class ReportGenerator:
    """监控报告生成器"""

    def generate_report(self, result: MonitorResult) -> str:
        """
        生成监控报告文本

        Args:
            result: 监控结果

        Returns:
            格式化的报告文本（Markdown 格式）
        """
        # 判断是否有信号
        has_signals = len(result.signals) > 0

        if has_signals:
            return self._generate_signal_report(result)
        else:
            return self._generate_no_signal_report(result)

    def _generate_signal_report(self, result: MonitorResult) -> str:
        """生成有信号的报告"""
        lines = []

        # 标题
        signal_emojis = {
            SignalType.BUY: "🟢",
            SignalType.SELL: "🔴",
            SignalType.HOLD: "🟡",
            SignalType.WATCH: "⚪",
        }

        # 获取最高优先级的信号类型
        primary_signal = result.signals[0] if result.signals else None
        emoji = signal_emojis.get(primary_signal.signal_type, "📊") if primary_signal else "📊"

        lines.append(f"{emoji} 盯盘信号 | {result.stock_name} ({result.stock_code})")
        lines.append("")

        # 信号详情
        lines.append(f"**{self._get_signal_title(primary_signal)} detected**")
        for sig in result.signals:
            lines.append(f"- {sig.description}")
        lines.append("")

        # 当前行情
        change_symbol = "+" if result.change_pct >= 0 else ""
        lines.append(f"- 当前价：¥{result.current_price:.2f} ({change_symbol}{result.change_pct:.2f}%)")
        lines.append("")

        # 技术指标
        tech_lines = []
        if result.ma5 is not None:
            tech_lines.append(f"MA5: {result.ma5:.2f}")
        if result.ma20 is not None:
            tech_lines.append(f"MA20: {result.ma20:.2f}")
        if result.rsi is not None:
            tech_lines.append(f"RSI: {result.rsi:.1f}")
        if result.volume_ratio is not None:
            tech_lines.append(f"量比: {result.volume_ratio:.1f}x")

        if tech_lines:
            lines.append("**技术指标:**")
            lines.append(", ".join(tech_lines))
            lines.append("")

        # 持仓情况
        if result.portfolio and result.portfolio.has_position:
            pnl_symbol = "+" if result.portfolio.pnl_pct >= 0 else ""
            lines.append("**💼 持仓情况**")
            lines.append(f"- 持仓：{result.portfolio.quantity:.0f}股 | 成本：¥{result.portfolio.avg_cost:.2f}")
            lines.append(f"- 浮盈：¥{result.portfolio.unrealized_pnl:+,.0f} ({pnl_symbol}{result.portfolio.pnl_pct:.2f}%)")
            lines.append("")

        # AI 分析
        if result.llm_summary:
            lines.append("**🤖 AI 分析**")
            lines.append(result.llm_summary)
            if result.llm_advice:
                lines.append(f"- 建议：**{result.llm_advice}**")
            if result.llm_confidence:
                lines.append(f"- 置信度：{result.llm_confidence}")
            lines.append("")

        # 时间戳
        lines.append(f"⏰ {result.timestamp.strftime('%Y-%m-%d %H:%M')}")

        return "\n".join(lines)

    def _generate_no_signal_report(self, result: MonitorResult) -> str:
        """生成无信号的报告"""
        lines = []

        # 标题
        change_symbol = "+" if result.change_pct >= 0 else ""
        lines.append(f"📊 盯盘报告 | {result.stock_name} ({result.stock_code})")
        lines.append("")

        # 状态
        lines.append("✅ 无明显交易信号")
        lines.append(f"- 当前价：¥{result.current_price:.2f} ({change_symbol}{result.change_pct:.2f}%)")
        lines.append("")

        # 技术指标
        tech_lines = []
        if result.ma5 is not None:
            tech_lines.append(f"MA5: {result.ma5:.2f}")
        if result.ma20 is not None:
            tech_lines.append(f"MA20: {result.ma20:.2f}")
        if result.rsi is not None:
            rsi_status = "超买" if result.rsi > 70 else ("超卖" if result.rsi < 30 else "中性")
            tech_lines.append(f"RSI: {result.rsi:.1f} ({rsi_status})")

        if tech_lines:
            lines.append("**技术指标:**")
            lines.append(", ".join(tech_lines))
            lines.append("")

        # 持仓情况
        if result.portfolio and result.portfolio.has_position:
            pnl_symbol = "+" if result.portfolio.pnl_pct >= 0 else ""
            lines.append("**💼 持仓情况**")
            lines.append(f"- 持仓：{result.portfolio.quantity:.0f}股 | 成本：¥{result.portfolio.avg_cost:.2f}")
            lines.append(f"- 浮盈：¥{result.portfolio.unrealized_pnl:+,.0f} ({pnl_symbol}{result.portfolio.pnl_pct:.2f}%)")
            lines.append("")

        # 建议
        lines.append("- 建议：继续观望")
        lines.append("")

        # AI 分析（如果有）
        if result.llm_summary:
            lines.append("**🤖 AI 分析**")
            lines.append(result.llm_summary)
            lines.append("")

        # 时间戳
        lines.append(f"⏰ {result.timestamp.strftime('%Y-%m-%d %H:%M')}")

        return "\n".join(lines)

    def _get_signal_title(self, signal) -> str:
        """获取信号标题"""
        if not signal:
            return "交易信号"

        titles = {
            SignalType.BUY: "买入信号",
            SignalType.SELL: "卖出信号",
            SignalType.HOLD: "持有信号",
            SignalType.WATCH: "关注信号",
        }
        return titles.get(signal.signal_type, "交易信号")
