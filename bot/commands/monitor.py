# -*- coding: utf-8 -*-
"""
===================================
盯盘监控命令
===================================

实时监控指定股票的技术指标和交易信号。
"""

import re
import logging
from typing import List, Optional

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse
from data_provider.base import canonical_stock_code

logger = logging.getLogger(__name__)


class MonitorCommand(BotCommand):
    """
    盯盘监控命令

    实时监控指定股票的技术指标和交易信号，支持持仓集成分析。

    用法：
        /monitor 600519                    - 监控单只股票（默认指标）
        /monitor 600519,AAPL               - 监控多只股票
        /monitor 600519 --indicators price,volume,rsi  - 指定监控指标
        /monitor 600519 --with-portfolio   - 包含持仓分析
        /monitor 600519 --account-id 1     - 指定持仓账户
    """

    @property
    def name(self) -> str:
        return "monitor"

    @property
    def aliases(self) -> List[str]:
        return ["m", "盯盘", "监控"]

    @property
    def description(self) -> str:
        return "实时监控指定股票的指标信号"

    @property
    def usage(self) -> str:
        return "/monitor <股票代码> [--indicators price,volume,rsi] [--with-portfolio]"

    def validate_args(self, args: List[str]) -> Optional[str]:
        """验证参数"""
        if not args:
            return "请输入股票代码\n用法: /monitor 600519,AAPL [--indicators price,volume] [--with-portfolio]"

        # 提取股票代码（第一个非选项参数）
        stock_codes_str = None
        for arg in args:
            if not arg.startswith("--"):
                stock_codes_str = arg
                break

        if not stock_codes_str:
            return "请提供股票代码"

        # 验证股票代码格式
        codes = [c.strip().upper() for c in stock_codes_str.split(",")]
        for code in codes:
            is_a_stock = re.match(r"^\d{6}$", code)
            is_hk_stock = re.match(r"^HK\d{5}$", code)
            is_us_stock = re.match(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?$", code)

            if not (is_a_stock or is_hk_stock or is_us_stock):
                return f"无效的股票代码: {code}"

        return None

    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """执行监控命令"""
        try:
            # 解析参数
            stock_codes_str, options = self._parse_args(args)

            if not stock_codes_str:
                return BotResponse.text_response(
                    "❌ 请指定股票代码\n用法: /monitor 600519,AAPL [--indicators price,volume] [--with-portfolio]"
                )

            # 标准化股票代码
            raw_codes = [c.strip() for c in stock_codes_str.split(",") if c.strip()]
            stock_codes = [canonical_stock_code(code) for code in raw_codes]

            # 解析指标
            indicators = self._parse_indicators(options.get("indicators", ""))

            # 检查是否包含持仓
            with_portfolio = "--with-portfolio" in args
            account_id = self._parse_account_id(options.get("account-id"))

            logger.info(
                f"[MonitorCommand] 监控请求: {len(stock_codes)} 只股票, "
                f"指标: {[i.value for i in indicators]}, "
                f"持仓: {with_portfolio}, 账户: {account_id}"
            )

            # 异步执行监控（避免阻塞 Bot）
            import asyncio

            asyncio.create_task(
                self._execute_monitor(
                    message=message,
                    stock_codes=stock_codes,
                    indicators=indicators,
                    with_portfolio=with_portfolio,
                    account_id=account_id,
                )
            )

            # 立即返回确认消息
            indicator_names = ", ".join([i.value for i in indicators[:3]])
            if len(indicators) > 3:
                indicator_names += f" 等{len(indicators)}个指标"

            portfolio_text = "（含持仓分析）" if with_portfolio else ""
            return BotResponse.text_response(
                f"📊 已开始监控 {len(stock_codes)} 只股票{portfolio_text}\n"
                f"指标: {indicator_names}\n"
                f"结果将稍后推送..."
            )

        except Exception as e:
            logger.error(f"[MonitorCommand] 执行失败: {e}", exc_info=True)
            return BotResponse.text_response(f"❌ 监控失败: {str(e)}")

    async def _execute_monitor(
        self,
        message: BotMessage,
        stock_codes: List[str],
        indicators,
        with_portfolio: bool,
        account_id: Optional[int],
    ):
        """异步执行监控任务"""
        try:
            from src.monitor.core import MonitorEngine

            engine = MonitorEngine()
            results = await engine.run(
                stock_codes=stock_codes,
                indicators=indicators,
                with_portfolio=with_portfolio,
                account_id=account_id,
                notify=True,  # 总是发送通知
                save_history=True,
            )

            if not results:
                await self._reply(message, "⚠️ 未获取到监控结果")
                return

            # 构建回复消息
            reply = self._format_results(results)
            await self._reply(message, reply)

        except Exception as e:
            logger.error(f"[MonitorCommand] 监控执行失败: {e}", exc_info=True)
            await self._reply(message, f"❌ 监控执行失败: {str(e)}")

    def _parse_args(self, args: List[str]):
        """
        解析命令行参数

        Returns:
            (stock_codes_str, options_dict)
        """
        stock_codes_str = None
        options = {}

        i = 0
        while i < len(args):
            arg = args[i]

            if arg.startswith("--"):
                key = arg[2:]
                # 检查是否有值
                if i + 1 < len(args) and not args[i + 1].startswith("--"):
                    options[key] = args[i + 1]
                    i += 2
                else:
                    options[key] = True
                    i += 1
            else:
                if stock_codes_str is None:
                    stock_codes_str = arg
                i += 1

        return stock_codes_str, options

    def _parse_indicators(self, indicators_str: str):
        """解析指标字符串"""
        from src.monitor.schemas import IndicatorType

        if not indicators_str or indicators_str is True:
            # 默认指标
            return [IndicatorType.PRICE_BREAKOUT, IndicatorType.VOLUME_SPIKE]

        # 映射关系
        indicator_map = {
            "price": IndicatorType.PRICE_BREAKOUT,
            "volume": IndicatorType.VOLUME_SPIKE,
            "ma": IndicatorType.MA_CROSS,
            "rsi": IndicatorType.RSI_SIGNAL,
            "macd": IndicatorType.MACD_SIGNAL,
        }

        indicators = []
        for name in indicators_str.split(","):
            name = name.strip().lower()
            if name in indicator_map:
                indicators.append(indicator_map[name])

        # 如果没有有效指标，使用默认
        if not indicators:
            indicators = [IndicatorType.PRICE_BREAKOUT, IndicatorType.VOLUME_SPIKE]

        return indicators

    def _parse_account_id(self, account_id_value) -> Optional[int]:
        """解析账户ID"""
        if account_id_value and account_id_value is not True:
            try:
                return int(account_id_value)
            except (ValueError, TypeError):
                return None
        return None

    def _format_results(self, results) -> str:
        """格式化监控结果为回复消息"""
        lines = ["📊 监控结果汇总\n"]

        for result in results:
            change_symbol = "+" if result.change_pct >= 0 else ""
            lines.append(f"**{result.stock_name} ({result.stock_code})**")
            lines.append(f"当前价: ¥{result.current_price:.2f} ({change_symbol}{result.change_pct:.2f}%)")

            if result.signals:
                lines.append(f"✅ 检测到 {len(result.signals)} 个信号:")
                for sig in result.signals[:3]:  # 最多显示3个信号
                    lines.append(f"  - {sig.description}")
            else:
                lines.append("✅ 无明显信号")

            if result.llm_summary:
                summary = result.llm_summary[:100]
                lines.append(f"💡 {summary}")

            lines.append("")

        lines.append(f"⏰ {results[0].timestamp.strftime('%Y-%m-%d %H:%M')}")

        return "\n".join(lines)

    async def _reply(self, message: BotMessage, text: str):
        """通过 dispatcher 回复消息"""
        try:
            from bot.dispatcher import get_dispatcher

            dispatcher = get_dispatcher()
            await dispatcher.reply_to_message(message, text)
        except Exception as e:
            logger.error(f"[MonitorCommand] 回复消息失败: {e}", exc_info=True)
