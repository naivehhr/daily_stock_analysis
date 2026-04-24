"""
MonitorEngine - 盯盘监控核心引擎

协调整个监控流程：
1. 获取实时行情和历史数据
2. 计算技术指标
3. 检测交易信号
4. 调用 LLM Agent 分析
5. 生成报告并推送通知
6. 保存历史记录
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

from src.monitor.schemas import (
    IndicatorType,
    MonitorSignal,
    PortfolioContext,
    MonitorResult,
)
from src.monitor.indicators import IndicatorsCalculator
from src.monitor.signal_detector import SignalDetector
from src.monitor.report_generator import ReportGenerator
from src.monitor.history_manager import HistoryManager
from src.storage import get_db
from data_provider.base import DataFetcherManager
from src.notification import NotificationService

logger = logging.getLogger(__name__)


class MonitorEngine:
    """
    盯盘监控核心引擎

    职责：
    - 协调数据获取、指标计算、信号检测、LLM 分析全流程
    - 支持并发处理多只股票
    - 集成通知推送和历史记录保存
    """

    def __init__(
        self,
        price_breakout_threshold: float = 3.0,
        volume_spike_ratio: float = 2.0,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
    ):
        """
        初始化监控引擎

        Args:
            price_breakout_threshold: 价格突破阈值（百分比）
            volume_spike_ratio: 成交量异常倍数
            rsi_overbought: RSI 超买阈值
            rsi_oversold: RSI 超卖阈值
        """
        # 初始化各组件
        self.fetcher = DataFetcherManager()
        self.db = get_db()
        self.calculator = IndicatorsCalculator(
            price_breakout_threshold=price_breakout_threshold,
            volume_spike_ratio=volume_spike_ratio,
            rsi_overbought=rsi_overbought,
            rsi_oversold=rsi_oversold,
        )
        self.signal_detector = SignalDetector(self.calculator)
        self.report_generator = ReportGenerator()
        self.history_manager = HistoryManager()
        self.notifier = NotificationService()

    async def run(
        self,
        stock_codes: List[str],
        indicators: List[IndicatorType],
        with_portfolio: bool = False,
        account_id: Optional[int] = None,
        notify: bool = True,
        save_history: bool = True,
    ) -> List[MonitorResult]:
        """
        执行监控分析

        Args:
            stock_codes: 股票代码列表
            indicators: 要监控的指标类型
            with_portfolio: 是否包含持仓分析
            account_id: 持仓账户ID
            notify: 是否发送通知
            save_history: 是否保存历史记录

        Returns:
            监控结果列表
        """
        logger.info(
            f"开始监控 {len(stock_codes)} 只股票，指标: {[i.value for i in indicators]}"
        )

        start_time = time.time()

        # 1. 获取持仓信息（如果需要）
        portfolio_map = {}
        if with_portfolio and account_id:
            try:
                from src.services.portfolio_service import PortfolioService

                portfolio_svc = PortfolioService()
                snapshot = portfolio_svc.get_portfolio_snapshot(
                    account_id=account_id,
                    as_of=datetime.now().date(),
                )

                # 提取持仓信息
                if snapshot and "accounts" in snapshot:
                    for account in snapshot["accounts"]:
                        for pos in account.get("positions", []):
                            symbol = pos.get("symbol", "")
                            if symbol:
                                portfolio_map[symbol] = pos

                logger.info(f"加载了 {len(portfolio_map)} 只持仓股票")
            except Exception as e:
                logger.error(f"获取持仓信息失败: {e}", exc_info=True)

        # 2. 并发处理每只股票
        tasks = [
            self._analyze_single(
                code,
                indicators,
                portfolio_map.get(code),
            )
            for code in stock_codes
        ]

        results_with_exceptions = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 过滤有效结果
        results = []
        for item in results_with_exceptions:
            if isinstance(item, Exception):
                logger.error(f"监控任务执行出错: {item}", exc_info=True)
            elif isinstance(item, MonitorResult):
                results.append(item)

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"监控完成，成功 {len(results)}/{len(stock_codes)} 只，耗时 {duration_ms}ms"
        )

        # 4. 发送通知（如果需要）
        if notify and results:
            try:
                self._send_notifications(results)
            except Exception as e:
                logger.error(f"发送通知失败: {e}", exc_info=True)

        # 5. 保存历史（如果需要）
        if save_history and results:
            try:
                for result in results:
                    self.history_manager.save_report(result)
            except Exception as e:
                logger.error(f"保存历史记录失败: {e}", exc_info=True)

        return results

    async def _analyze_single(
        self,
        stock_code: str,
        indicators: List[IndicatorType],
        portfolio_info: Optional[Dict],
    ) -> MonitorResult:
        """
        分析单只股票

        Args:
            stock_code: 股票代码
            indicators: 监控指标列表
            portfolio_info: 持仓信息（可选）

        Returns:
            监控结果
        """
        start_time = time.time()
        data_sources = []

        try:
            # Step 1: 获取实时行情
            logger.debug(f"[{stock_code}] 获取实时行情...")
            quote = self.fetcher.get_realtime_quote(stock_code)
            if not quote:
                raise ValueError(f"无法获取 {stock_code} 的实时行情")

            current_price = quote.price or 0.0
            stock_name = quote.name or stock_code
            change_pct = quote.change_pct or 0.0
            data_sources.append("realtime")

            # Step 2: 获取历史K线数据
            logger.debug(f"[{stock_code}] 获取历史数据...")
            historical_data = self.fetcher.get_daily_data(stock_code, days=60)
            if historical_data is None:
                df = pd.DataFrame()
            else:
                df = historical_data[0] if isinstance(historical_data, tuple) else historical_data
            if df.empty:
                logger.warning(f"[{stock_code}] 无历史数据，使用空指标")
                indicators_data = self.calculator._empty_indicators(current_price)
            else:
                indicators_data = self.calculator.calculate_all(df, current_price)
                data_sources.append("historical")

            # Step 3: 检测信号
            logger.debug(f"[{stock_code}] 检测信号...")
            signals = self.signal_detector.detect_signals(indicators_data, indicators)

            # Step 4: 构建持仓上下文
            portfolio_ctx = None
            if portfolio_info:
                portfolio_ctx = self._build_portfolio_context(
                    portfolio_info, current_price
                )

            # Step 5: LLM 分析（仅在检测到信号或有持仓时）
            llm_summary = None
            llm_advice = None
            llm_confidence = None

            if signals or (portfolio_ctx and portfolio_ctx.has_position):
                logger.info(
                    f"[{stock_code}] 触发 LLM 分析条件: "
                    f"信号数={len(signals)}, "
                    f"有持仓={portfolio_ctx.has_position if portfolio_ctx else False}"
                )
                try:
                    llm_result = await self._call_llm_analysis(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        current_price=current_price,
                        change_pct=change_pct,
                        indicators=indicators_data,
                        signals=signals,
                        portfolio=portfolio_ctx,
                    )
                    llm_summary = llm_result.get("core_conclusion")
                    llm_advice = llm_result.get("action_plan", {}).get("recommendation")
                    llm_confidence = llm_result.get("confidence")
                    logger.info(
                        f"[{stock_code}] LLM 分析完成: "
                        f"结论={llm_summary}, 建议={llm_advice}, 置信度={llm_confidence}"
                    )
                except Exception as e:
                    logger.error(f"[{stock_code}] LLM 分析失败: {e}", exc_info=True)
            else:
                logger.info(
                    f"[{stock_code}] 未触发 LLM 分析: "
                    f"信号数={len(signals)}, 持仓={portfolio_ctx is not None}"
                )

            duration_ms = int((time.time() - start_time) * 1000)

            # Step 6: 构建结果
            result = MonitorResult(
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                change_pct=change_pct,
                ma5=indicators_data.get("ma5"),
                ma10=indicators_data.get("ma10"),
                ma20=indicators_data.get("ma20"),
                volume_ratio=indicators_data.get("volume_ratio"),
                rsi=indicators_data.get("rsi"),
                macd_dif=indicators_data.get("macd_dif"),
                macd_dea=indicators_data.get("macd_dea"),
                # 量能分析指标
                price_angle=indicators_data.get("price_angle"),
                momentum_strength=indicators_data.get("momentum_strength"),
                volume_power=indicators_data.get("volume_power"),
                # 势能分析指标
                momentum_3d=indicators_data.get("momentum_3d"),
                momentum_5d=indicators_data.get("momentum_5d"),
                acceleration=indicators_data.get("acceleration"),
                signals=signals,
                llm_summary=llm_summary,
                llm_advice=llm_advice,
                llm_confidence=llm_confidence,
                portfolio=portfolio_ctx,
                timestamp=datetime.now(),
                analysis_duration_ms=duration_ms,
                data_sources=data_sources,
            )

            logger.info(
                f"[{stock_code}] 分析完成，检测到 {len(signals)} 个信号，耗时 {duration_ms}ms"
            )
            return result

        except Exception as e:
            logger.error(f"[{stock_code}] 分析失败: {e}", exc_info=True)
            # 返回一个错误结果
            return MonitorResult(
                stock_code=stock_code,
                stock_name=stock_code,
                current_price=0.0,
                change_pct=0.0,
                signals=[],
                llm_summary=f"分析失败: {str(e)}",
                timestamp=datetime.now(),
                analysis_duration_ms=int((time.time() - start_time) * 1000),
            )

    def _build_portfolio_context(
        self, portfolio_info: Dict, current_price: float
    ) -> PortfolioContext:
        """构建持仓上下文"""
        quantity = portfolio_info.get("quantity", 0)
        avg_cost = portfolio_info.get("avg_cost", 0)
        unrealized_pnl = portfolio_info.get("unrealized_pnl", 0)

        # 计算盈亏百分比
        pnl_pct = 0.0
        if avg_cost > 0 and quantity > 0:
            total_cost = avg_cost * quantity
            pnl_pct = (unrealized_pnl / total_cost) * 100 if total_cost > 0 else 0.0

        # 仓位占比（简化计算，实际应该从账户总资产计算）
        position_ratio = portfolio_info.get("position_ratio", 0)

        return PortfolioContext(
            has_position=quantity > 0,
            quantity=quantity,
            avg_cost=avg_cost,
            current_price=current_price,
            unrealized_pnl=unrealized_pnl,
            pnl_pct=pnl_pct,
            position_ratio=position_ratio,
        )

    async def _call_llm_analysis(
        self,
        stock_code: str,
        stock_name: str,
        current_price: float,
        change_pct: float,
        indicators: Dict[str, Any],
        signals: List[MonitorSignal],
        portfolio: Optional[PortfolioContext],
    ) -> Dict[str, Any]:
        """
        调用 LLM 进行分析

        使用 MonitorAgent 进行智能分析
        """
        # 记录 LLM 输入
        signal_lines = "\n".join([f"  - {s.indicator.value}/{s.signal_type.value}: {s.description}" for s in signals]) if signals else "  无"
        portfolio_info = portfolio.dict() if portfolio else "无"

        logger.info(
            f"[{stock_code}] === LLM 分析输入 ===\n"
            f"股票: {stock_name} ({stock_code})\n"
            f"价格: ¥{current_price:.2f} ({change_pct:+.2f}%)\n"
            f"技术指标: MA5={indicators.get('ma5')}, MA10={indicators.get('ma10')}, "
            f"MA20={indicators.get('ma20')}, RSI={indicators.get('rsi')}, "
            f"MACD_DIF={indicators.get('macd_dif')}, MACD_DEA={indicators.get('macd_dea')}, "
            f"VOL_RATIO={indicators.get('volume_ratio')}\n"
            f"量能分析: 价格角度={indicators.get('price_angle')}°, "
            f"动量强度={indicators.get('momentum_strength')}, "
            f"量能力量={indicators.get('volume_power')}\n"
            f"势能分析: 3日动量={indicators.get('momentum_3d')}%, "
            f"5日动量={indicators.get('momentum_5d')}%, "
            f"加速度={indicators.get('acceleration')}%\n"
            f"检测信号: {len(signals)} 个\n"
            f"{signal_lines}\n"
            f"持仓信息: {portfolio_info}"
        )

        try:
            # 尝试使用 MonitorAgent
            from src.agent.agents.monitor_agent import MonitorAgent
            from src.agent.llm_adapter import LLMToolAdapter
            from src.agent.tools.registry import ToolRegistry
            from src.agent.protocols import AgentContext

            # 创建工具注册表（简化版，暂不注册实际工具）
            tool_registry = ToolRegistry()

            # 创建 LLM 适配器
            llm_adapter = LLMToolAdapter()

            # 创建 MonitorAgent
            agent = MonitorAgent(
                tool_registry=tool_registry,
                llm_adapter=llm_adapter,
            )

            # 构建上下文
            ctx = AgentContext(
                data={
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "current_price": current_price,
                    "change_pct": change_pct,
                    "indicators": indicators,
                    "signals": [s.dict() for s in signals],
                    "portfolio": portfolio.dict() if portfolio else None,
                }
            )

            logger.debug(f"[{stock_code}] 调用 MonitorAgent.run()...")
            # 运行 Agent
            result = agent.run(ctx)

            # 提取分析结果
            if result and result.opinion:
                llm_output = result.opinion.raw_data or {}
                logger.info(
                    f"[{stock_code}] === LLM 分析输出 (MonitorAgent) ===\n"
                    f"核心结论: {llm_output.get('core_conclusion', 'N/A')}\n"
                    f"操作建议: {llm_output.get('action_plan', {}).get('recommendation', 'N/A')}\n"
                    f"置信度: {llm_output.get('confidence', 'N/A')}\n"
                    f"完整输出: {llm_output}"
                )
                return llm_output
            else:
                logger.warning(f"[{stock_code}] MonitorAgent 未返回有效结果，使用 fallback")
                # Fallback: 使用简单文本分析
                return await self._fallback_llm_analysis(
                    stock_code, stock_name, current_price, change_pct,
                    indicators, signals, portfolio
                )

        except ImportError as e:
            logger.warning(f"[{stock_code}] MonitorAgent 不可用，使用 fallback: {e}")
            return await self._fallback_llm_analysis(
                stock_code, stock_name, current_price, change_pct,
                indicators, signals, portfolio
            )
        except Exception as e:
            logger.error(f"[{stock_code}] LLM 分析异常: {e}", exc_info=True)
            return await self._fallback_llm_analysis(
                stock_code, stock_name, current_price, change_pct,
                indicators, signals, portfolio
            )

    async def _fallback_llm_analysis(
        self,
        stock_code: str,
        stock_name: str,
        current_price: float,
        change_pct: float,
        indicators: Dict[str, Any],
        signals: List[MonitorSignal],
        portfolio: Optional[PortfolioContext],
    ) -> Dict[str, Any]:
        """
        Fallback LLM 分析（当 MonitorAgent 不可用时）

        直接使用 GeminiAnalyzer 生成简要分析
        """
        try:
            from src.analyzer import GeminiAnalyzer

            analyzer = GeminiAnalyzer()

            # 构建简化的 prompt
            signal_desc = "\n".join([f"- {s.description}" for s in signals]) if signals else "无明显信号"

            portfolio_desc = ""
            if portfolio and portfolio.has_position:
                portfolio_desc = f"""
持仓情况:
- 数量: {portfolio.quantity} 股
- 成本: ¥{portfolio.avg_cost:.2f}
- 浮盈: ¥{portfolio.unrealized_pnl:.2f} ({portfolio.pnl_pct:+.2f}%)
"""

            prompt = f"""
请对 {stock_name}({stock_code}) 进行简要分析：

当前价格: ¥{current_price:.2f} ({change_pct:+.2f}%)
技术指标: MA5={indicators.get('ma5', 'N/A')}, MA20={indicators.get('ma20', 'N/A')}, RSI={indicators.get('rsi', 'N/A')}
量能分析: 价格角度={indicators.get('price_angle', 'N/A')}°, 动量强度={indicators.get('momentum_strength', 'N/A')}, 量能力量={indicators.get('volume_power', 'N/A')}
势能分析: 3日动量={indicators.get('momentum_3d', 'N/A')}%, 5日动量={indicators.get('momentum_5d', 'N/A')}%, 加速度={indicators.get('acceleration', 'N/A')}%
检测信号:
{signal_desc}
{portfolio_desc}

请结合量能和势能分析，给出：
1. 核心结论（一句话）
2. 操作建议（买入/持有/卖出/观望）
3. 风险提示（特别关注量价背离和动能变化）
"""

            # 记录 Fallback LLM 输入
            logger.info(
                f"[{stock_code}] === Fallback LLM 分析输入 ===\n"
                f"Prompt:\n{prompt}"
            )

            # 调用 LLM
            result = analyzer.generate_text(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3,
            )

            # 记录 Fallback LLM 输出
            logger.info(
                f"[{stock_code}] === Fallback LLM 分析输出 ===\n"
                f"原始响应: {result}\n"
                f"截取后: {result[:100] if result else 'N/A'}"
            )

            llm_output = {
                "core_conclusion": result[:100] if result else "分析完成",
                "action_plan": {
                    "recommendation": "观望",
                    "reasoning": result[:200] if result else "基于技术指标分析",
                },
                "confidence": "中",
            }

            logger.info(
                f"[{stock_code}] Fallback LLM 结构化输出: {llm_output}"
            )

            return llm_output

        except Exception as e:
            logger.error(f"[{stock_code}] Fallback LLM 分析失败: {e}", exc_info=True)
            return {
                "core_conclusion": f"分析失败: {str(e)}",
                "action_plan": {
                    "recommendation": "观望",
                    "reasoning": "系统异常，建议手动分析",
                },
                "confidence": "低",
            }

    def _send_notifications(self, results: List[MonitorResult]) -> None:
        """
        发送通知

        为每个结果生成报告并推送到所有配置的渠道
        """
        for result in results:
            try:
                # 生成报告文本
                report_text = self.report_generator.generate_report(result)

                # 发送通知
                success = self.notifier.send(report_text)

                if success:
                    logger.info(f"[{result.stock_code}] 通知发送成功")
                else:
                    logger.warning(f"[{result.stock_code}] 通知发送失败")

            except Exception as e:
                logger.error(
                    f"[{result.stock_code}] 发送通知异常: {e}", exc_info=True
                )
