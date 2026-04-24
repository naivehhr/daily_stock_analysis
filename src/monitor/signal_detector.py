"""
信号检测器

根据技术指标检测结果，生成交易信号。
支持多种指标类型的信号检测。
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.monitor.schemas import (
    IndicatorType,
    SignalType,
    MonitorSignal,
)
from src.monitor.indicators import IndicatorsCalculator

logger = logging.getLogger(__name__)


class SignalDetector:
    """交易信号检测器"""

    def __init__(self, calculator: IndicatorsCalculator):
        """
        初始化信号检测器

        Args:
            calculator: 指标计算器实例
        """
        self.calculator = calculator

    def detect_signals(
        self,
        indicators: Dict[str, Any],
        enabled_indicators: List[IndicatorType],
    ) -> List[MonitorSignal]:
        """
        检测所有启用的指标信号

        Args:
            indicators: 技术指标字典（来自 IndicatorsCalculator）
            enabled_indicators: 启用的指标类型列表

        Returns:
            检测到的信号列表
        """
        signals = []

        for indicator_type in enabled_indicators:
            try:
                detected = self._detect_single_indicator(
                    indicator_type, indicators
                )
                if detected:
                    signals.extend(detected)
            except Exception as e:
                logger.error(
                    f"检测指标 {indicator_type.value} 信号失败: {e}",
                    exc_info=True,
                )

        return signals

    def _detect_single_indicator(
        self,
        indicator_type: IndicatorType,
        indicators: Dict[str, Any],
    ) -> List[MonitorSignal]:
        """检测单个指标的信号"""

        if indicator_type == IndicatorType.PRICE_BREAKOUT:
            return self._detect_price_breakout(indicators)

        elif indicator_type == IndicatorType.VOLUME_SPIKE:
            return self._detect_volume_spike(indicators)

        elif indicator_type == IndicatorType.MA_CROSS:
            return self._detect_ma_cross(indicators)

        elif indicator_type == IndicatorType.RSI_SIGNAL:
            return self._detect_rsi_signal(indicators)

        elif indicator_type == IndicatorType.MACD_SIGNAL:
            return self._detect_macd_signal(indicators)

        elif indicator_type == IndicatorType.MOMENTUM:
            return self._detect_momentum_signal(indicators)

        elif indicator_type == IndicatorType.VOLUME_MOMENTUM:
            return self._detect_volume_momentum_signal(indicators)

        elif indicator_type == IndicatorType.CUSTOM:
            # 自定义指标暂不实现
            return []

        else:
            logger.warning(f"未知的指标类型: {indicator_type}")
            return []

    def _detect_price_breakout(
        self, indicators: Dict[str, Any]
    ) -> List[MonitorSignal]:
        """检测价格突破信号"""
        signals = []

        current_price = indicators.get("current_price", 0)
        ma20 = indicators.get("ma20")

        breakout_info = self.calculator.check_price_breakout(
            current_price, ma20
        )

        if breakout_info:
            direction = breakout_info["direction"]
            deviation = breakout_info["deviation_pct"]

            # 向上突破 -> 买入信号
            if direction == "above":
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.PRICE_BREAKOUT,
                        signal_type=SignalType.BUY,
                        confidence=min(0.9, 0.5 + deviation / 100),
                        value=current_price,
                        threshold=ma20,
                        description=f"价格向上突破20日均线 {deviation}%（当前:{current_price:.2f}, MA20:{ma20:.2f}）",
                    )
                )
            # 向下突破 -> 卖出信号
            else:
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.PRICE_BREAKOUT,
                        signal_type=SignalType.SELL,
                        confidence=min(0.9, 0.5 + deviation / 100),
                        value=current_price,
                        threshold=ma20,
                        description=f"价格向下跌破20日均线 {deviation}%（当前:{current_price:.2f}, MA20:{ma20:.2f}）",
                    )
                )

        return signals

    def _detect_volume_spike(
        self, indicators: Dict[str, Any]
    ) -> List[MonitorSignal]:
        """检测成交量异常信号"""
        signals = []

        volume_ratio = indicators.get("volume_ratio")
        spike_info = self.calculator.check_volume_spike(volume_ratio)

        if spike_info:
            ratio = spike_info["volume_ratio"]
            # 放量通常伴随价格上涨时为买入信号，下跌时为卖出信号
            price_change = indicators.get("price_change_pct", 0)

            if price_change and price_change > 0:
                signal_type = SignalType.BUY
                desc_prefix = "放量上涨"
            else:
                signal_type = SignalType.SELL
                desc_prefix = "放量下跌"

            signals.append(
                MonitorSignal(
                    indicator=IndicatorType.VOLUME_SPIKE,
                    signal_type=signal_type,
                    confidence=min(0.85, 0.6 + (ratio - 2) / 10),
                    value=volume_ratio,
                    threshold=spike_info["threshold"],
                    description=f"{desc_prefix}，成交量为5日均量的 {ratio:.1f} 倍",
                )
            )

        return signals

    def _detect_ma_cross(self, indicators: Dict[str, Any]) -> List[MonitorSignal]:
        """检测均线交叉信号"""
        signals = []

        ma5 = indicators.get("ma5")
        ma10 = indicators.get("ma10")
        ma20 = indicators.get("ma20")

        cross_info = self.calculator.check_ma_cross(ma5, ma10, ma20)

        if cross_info:
            cross_type = cross_info["type"]

            if cross_type == "golden_cross":
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.MA_CROSS,
                        signal_type=SignalType.BUY,
                        confidence=0.75,
                        description=f"金叉信号：{cross_info['description']}",
                    )
                )
            else:  # death_cross
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.MA_CROSS,
                        signal_type=SignalType.SELL,
                        confidence=0.75,
                        description=f"死叉信号：{cross_info['description']}",
                    )
                )

        return signals

    def _detect_rsi_signal(self, indicators: Dict[str, Any]) -> List[MonitorSignal]:
        """检测 RSI 信号"""
        signals = []

        rsi = indicators.get("rsi")
        rsi_info = self.calculator.check_rsi_signal(rsi)

        if rsi_info:
            rsi_type = rsi_info["type"]

            if rsi_type == "overbought":
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.RSI_SIGNAL,
                        signal_type=SignalType.SELL,
                        confidence=min(0.85, 0.6 + (rsi - 70) / 100),
                        value=rsi,
                        threshold=rsi_info["threshold"],
                        description=f"RSI 超买 ({rsi:.1f})，警惕回调风险",
                    )
                )
            else:  # oversold
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.RSI_SIGNAL,
                        signal_type=SignalType.BUY,
                        confidence=min(0.85, 0.6 + (30 - rsi) / 100),
                        value=rsi,
                        threshold=rsi_info["threshold"],
                        description=f"RSI 超卖 ({rsi:.1f})，可能存在反弹机会",
                    )
                )

        return signals

    def _detect_macd_signal(self, indicators: Dict[str, Any]) -> List[MonitorSignal]:
        """检测 MACD 信号"""
        signals = []

        dif = indicators.get("macd_dif")
        dea = indicators.get("macd_dea")

        if dif is None or dea is None:
            return signals

        # 金叉：DIF 上穿 DEA
        if dif > dea and dif > 0:
            signals.append(
                MonitorSignal(
                    indicator=IndicatorType.MACD_SIGNAL,
                    signal_type=SignalType.BUY,
                    confidence=0.7,
                    value=dif,
                    threshold=dea,
                    description=f"MACD 金叉（DIF:{dif:.4f} > DEA:{dea:.4f}）",
                )
            )
        # 死叉：DIF 下穿 DEA
        elif dif < dea and dif < 0:
            signals.append(
                MonitorSignal(
                    indicator=IndicatorType.MACD_SIGNAL,
                    signal_type=SignalType.SELL,
                    confidence=0.7,
                    value=dif,
                    threshold=dea,
                    description=f"MACD 死叉（DIF:{dif:.4f} < DEA:{dea:.4f}）",
                )
            )

        return signals

    def _detect_momentum_signal(
        self, indicators: Dict[str, Any]
    ) -> List[MonitorSignal]:
        """检测势能信号（动量、加速度）"""
        signals = []

        momentum_3d = indicators.get("momentum_3d")
        momentum_5d = indicators.get("momentum_5d")
        acceleration = indicators.get("acceleration")

        if momentum_3d is None or momentum_5d is None:
            return signals

        # 1. 基于动量大小的信号
        # 强势上涨动量
        if momentum_3d > 3.0 and momentum_5d > 5.0:
            confidence = min(0.85, 0.6 + (momentum_3d / 100) + (momentum_5d / 100))
            signals.append(
                MonitorSignal(
                    indicator=IndicatorType.MOMENTUM,
                    signal_type=SignalType.BUY,
                    confidence=confidence,
                    value=momentum_3d,
                    description=f"强势上涨动量：3日{momentum_3d:+.2f}%, 5日{momentum_5d:+.2f}%",
                )
            )
        # 强势下跌动量
        elif momentum_3d < -3.0 and momentum_5d < -5.0:
            confidence = min(0.85, 0.6 + (abs(momentum_3d) / 100) + (abs(momentum_5d) / 100))
            signals.append(
                MonitorSignal(
                    indicator=IndicatorType.MOMENTUM,
                    signal_type=SignalType.SELL,
                    confidence=confidence,
                    value=momentum_3d,
                    description=f"强势下跌动量：3日{momentum_3d:+.2f}%, 5日{momentum_5d:+.2f}%",
                )
            )

        # 2. 基于加速度的信号（动量变化）
        if acceleration is not None:
            # 加速上涨
            if acceleration > 2.0 and momentum_3d > 0:
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.MOMENTUM,
                        signal_type=SignalType.BUY,
                        confidence=min(0.8, 0.6 + acceleration / 20),
                        value=acceleration,
                        description=f"加速上涨：加速度{acceleration:+.2f}%，动能增强",
                    )
                )
            # 加速下跌
            elif acceleration < -2.0 and momentum_3d < 0:
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.MOMENTUM,
                        signal_type=SignalType.SELL,
                        confidence=min(0.8, 0.6 + abs(acceleration) / 20),
                        value=acceleration,
                        description=f"加速下跌：加速度{acceleration:+.2f}%，动能减弱",
                    )
                )
            # 减速（可能反转）
            elif abs(acceleration) > 3.0:
                signal_type = SignalType.SELL if momentum_3d > 0 else SignalType.BUY
                direction = "上涨" if momentum_3d > 0 else "下跌"
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.MOMENTUM,
                        signal_type=signal_type,
                        confidence=0.65,
                        value=acceleration,
                        description=f"{direction}减速：加速度{acceleration:+.2f}%，警惕趋势反转",
                    )
                )

        return signals

    def _detect_volume_momentum_signal(
        self, indicators: Dict[str, Any]
    ) -> List[MonitorSignal]:
        """检测量能信号（价格角度、力量强度）"""
        signals = []

        price_angle = indicators.get("price_angle")
        momentum_strength = indicators.get("momentum_strength")
        volume_power = indicators.get("volume_power")

        if price_angle is None or momentum_strength is None:
            return signals

        # 1. 基于价格角度的信号
        # 陡峭上涨角度（>30度表示强势）
        if price_angle > 30:
            signals.append(
                MonitorSignal(
                    indicator=IndicatorType.VOLUME_MOMENTUM,
                    signal_type=SignalType.BUY,
                    confidence=min(0.85, 0.6 + price_angle / 200),
                    value=price_angle,
                    description=f"陡峭上涨角度：{price_angle:.1f}°，上升力量强劲",
                )
            )
        # 陡峭下跌角度（<-30度表示弱势）
        elif price_angle < -30:
            signals.append(
                MonitorSignal(
                    indicator=IndicatorType.VOLUME_MOMENTUM,
                    signal_type=SignalType.SELL,
                    confidence=min(0.85, 0.6 + abs(price_angle) / 200),
                    value=price_angle,
                    description=f"陡峭下跌角度：{price_angle:.1f}°，下降压力巨大",
                )
            )

        # 2. 基于动量强度的信号
        # 强上涨力量（>0.5）
        if momentum_strength > 0.5:
            signals.append(
                MonitorSignal(
                    indicator=IndicatorType.VOLUME_MOMENTUM,
                    signal_type=SignalType.BUY,
                    confidence=min(0.85, 0.6 + momentum_strength / 4),
                    value=momentum_strength,
                    description=f"强上涨力量：动量强度{momentum_strength:.2f}，买方主导",
                )
            )
        # 强下跌力量（<-0.5）
        elif momentum_strength < -0.5:
            signals.append(
                MonitorSignal(
                    indicator=IndicatorType.VOLUME_MOMENTUM,
                    signal_type=SignalType.SELL,
                    confidence=min(0.85, 0.6 + abs(momentum_strength) / 4),
                    value=momentum_strength,
                    description=f"强下跌力量：动量强度{momentum_strength:.2f}，卖方主导",
                )
            )

        # 3. 基于量能力量的信号（成交量加权的价格变化）
        if volume_power is not None:
            # 放量上涨（量价齐升）
            if volume_power > 5.0:
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.VOLUME_MOMENTUM,
                        signal_type=SignalType.BUY,
                        confidence=min(0.8, 0.6 + volume_power / 50),
                        value=volume_power,
                        description=f"量价齐升：量能力量{volume_power:.2f}，资金积极入场",
                    )
                )
            # 放量下跌（量增价跌）
            elif volume_power < -5.0:
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.VOLUME_MOMENTUM,
                        signal_type=SignalType.SELL,
                        confidence=min(0.8, 0.6 + abs(volume_power) / 50),
                        value=volume_power,
                        description=f"量增价跌：量能力量{volume_power:.2f}，抛压沉重",
                    )
                )
            # 缩量上涨（量价背离，警惕）
            elif 0 < volume_power < 2.0 and momentum_strength > 0.3:
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.VOLUME_MOMENTUM,
                        signal_type=SignalType.WATCH,
                        confidence=0.6,
                        value=volume_power,
                        description=f"缩量上涨：量能力量{volume_power:.2f}，量价背离需警惕",
                    )
                )
            # 缩量下跌（可能见底）
            elif -2.0 < volume_power < 0 and momentum_strength < -0.3:
                signals.append(
                    MonitorSignal(
                        indicator=IndicatorType.VOLUME_MOMENTUM,
                        signal_type=SignalType.WATCH,
                        confidence=0.6,
                        value=volume_power,
                        description=f"缩量下跌：量能力量{volume_power:.2f}，抛压减弱或见底",
                    )
                )

        return signals
