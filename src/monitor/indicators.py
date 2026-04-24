"""
指标计算器

提供各类技术指标的计算功能，包括：
- 价格突破检测
- 成交量异常检测
- 均线（MA）计算
- RSI 计算
- MACD 计算
"""

import logging
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class IndicatorsCalculator:
    """技术指标计算器"""

    def __init__(
        self,
        price_breakout_threshold: float = 3.0,
        volume_spike_ratio: float = 2.0,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
    ):
        """
        初始化指标计算器

        Args:
            price_breakout_threshold: 价格突破阈值（百分比）
            volume_spike_ratio: 成交量异常倍数（相对于均量）
            rsi_overbought: RSI 超买阈值
            rsi_oversold: RSI 超卖阈值
        """
        self.price_breakout_threshold = price_breakout_threshold
        self.volume_spike_ratio = volume_spike_ratio
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

    def calculate_all(
        self, df: pd.DataFrame, current_price: float
    ) -> Dict[str, Any]:
        """
        计算所有技术指标

        Args:
            df: 历史K线数据（需包含 open, high, low, close, volume 列）
            current_price: 当前实时价格

        Returns:
            包含所有指标的字典
        """
        if df.empty or len(df) < 20:
            logger.warning("数据不足，无法计算完整指标")
            return self._empty_indicators(current_price)

        try:
            # 确保数据按日期排序
            df = df.sort_values("date").reset_index(drop=True)

            indicators = {
                "current_price": current_price,
                "ma5": self._calculate_ma(df, 5),
                "ma10": self._calculate_ma(df, 10),
                "ma20": self._calculate_ma(df, 20),
                "volume_ratio": self._calculate_volume_ratio(df),
                "rsi": self._calculate_rsi(df),
                "macd_dif": None,
                "macd_dea": None,
                "price_change_pct": self._calculate_price_change(df),
                # 量能分析指标
                "price_angle": None,
                "momentum_strength": None,
                "volume_power": None,
                # 势能分析指标
                "momentum_3d": None,
                "momentum_5d": None,
                "acceleration": None,
            }

            # 计算 MACD
            macd_result = self._calculate_macd(df)
            indicators["macd_dif"] = macd_result.get("dif")
            indicators["macd_dea"] = macd_result.get("dea")

            # 计算量能分析（上涨/下跌角度、力量强度）
            volume_momentum = self._calculate_volume_momentum(df)
            indicators["price_angle"] = volume_momentum.get("price_angle")
            indicators["momentum_strength"] = volume_momentum.get("momentum_strength")
            indicators["volume_power"] = volume_momentum.get("volume_power")

            # 计算势能分析（动量、加速度）
            momentum_data = self._calculate_momentum(df)
            indicators["momentum_3d"] = momentum_data.get("momentum_3d")
            indicators["momentum_5d"] = momentum_data.get("momentum_5d")
            indicators["acceleration"] = momentum_data.get("acceleration")

            return indicators

        except Exception as e:
            logger.error(f"计算指标失败: {e}", exc_info=True)
            return self._empty_indicators(current_price)

    def _calculate_ma(self, df: pd.DataFrame, period: int) -> Optional[float]:
        """计算移动平均线"""
        if len(df) < period:
            return None
        return round(float(df["close"].tail(period).mean()), 2)

    def _calculate_volume_ratio(self, df: pd.DataFrame) -> Optional[float]:
        """
        计算成交量比率（当前成交量 / 5日均量）

        Returns:
            成交量比率，>1 表示放量，<1 表示缩量
        """
        if len(df) < 6:
            return None

        current_volume = float(df["volume"].iloc[-1])
        avg_volume = float(df["volume"].tail(6).head(5).mean())

        if avg_volume == 0:
            return None

        return round(current_volume / avg_volume, 2)

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        计算 RSI 指标

        Returns:
            RSI 值（0-100）
        """
        if len(df) < period + 1:
            return None

        # 计算价格变化
        delta = df["close"].diff()

        # 分离涨跌
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        # 计算平均涨跌
        avg_gain = gain.tail(period).mean()
        avg_loss = loss.tail(period).mean()

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(float(rsi), 2)

    def _calculate_macd(
        self, df: pd.DataFrame, fast=12, slow=26, signal=9
    ) -> Dict[str, Optional[float]]:
        """
        计算 MACD 指标

        Returns:
            包含 dif, dea, histogram 的字典
        """
        if len(df) < slow:
            return {"dif": None, "dea": None, "histogram": None}

        # 计算 EMA
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

        # 计算 DIF
        dif = ema_fast - ema_slow

        # 计算 DEA（DIF 的 EMA）
        dea = dif.ewm(span=signal, adjust=False).mean()

        # 计算 MACD 柱
        histogram = dif - dea

        return {
            "dif": round(float(dif.iloc[-1]), 4),
            "dea": round(float(dea.iloc[-1]), 4),
            "histogram": round(float(histogram.iloc[-1]), 4),
        }

    def _calculate_price_change(self, df: pd.DataFrame) -> Optional[float]:
        """计算当日涨跌幅"""
        if len(df) < 2:
            return None

        prev_close = float(df["close"].iloc[-2])
        curr_close = float(df["close"].iloc[-1])

        if prev_close == 0:
            return None

        change_pct = ((curr_close - prev_close) / prev_close) * 100
        return round(change_pct, 2)

    def check_price_breakout(
        self, current_price: float, ma20: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """
        检查价格是否突破均线

        Returns:
            如果突破，返回突破信息；否则返回 None
        """
        if ma20 is None or ma20 == 0:
            return None

        deviation_pct = abs((current_price - ma20) / ma20 * 100)

        if deviation_pct >= self.price_breakout_threshold:
            direction = "above" if current_price > ma20 else "below"
            return {
                "direction": direction,
                "deviation_pct": round(deviation_pct, 2),
                "current_price": current_price,
                "reference_price": ma20,
            }

        return None

    def check_volume_spike(
        self, volume_ratio: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """
        检查成交量是否异常放大

        Returns:
            如果异常，返回异常信息；否则返回 None
        """
        if volume_ratio is None:
            return None

        if volume_ratio >= self.volume_spike_ratio:
            return {
                "volume_ratio": volume_ratio,
                "threshold": self.volume_spike_ratio,
            }

        return None

    def check_rsi_signal(self, rsi: Optional[float]) -> Optional[Dict[str, Any]]:
        """
        检查 RSI 是否超买或超卖

        Returns:
            如果超买或超卖，返回信号信息；否则返回 None
        """
        if rsi is None:
            return None

        if rsi >= self.rsi_overbought:
            return {
                "type": "overbought",
                "rsi": rsi,
                "threshold": self.rsi_overbought,
            }
        elif rsi <= self.rsi_oversold:
            return {
                "type": "oversold",
                "rsi": rsi,
                "threshold": self.rsi_oversold,
            }

        return None

    def check_ma_cross(
        self,
        ma5: Optional[float],
        ma10: Optional[float],
        ma20: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        """
        检查均线交叉信号

        Returns:
            如果检测到金叉或死叉，返回信号信息；否则返回 None
        """
        if ma5 is None or ma10 is None or ma20 is None:
            return None

        # 金叉：短均线上穿长均线
        if ma5 > ma10 and ma5 > ma20:
            return {
                "type": "golden_cross",
                "description": "短期均线上穿长期均线，多头排列",
            }

        # 死叉：短均线下穿长均线
        if ma5 < ma10 and ma5 < ma20:
            return {
                "type": "death_cross",
                "description": "短期均线下穿长期均线，空头排列",
            }

        return None

    def _calculate_volume_momentum(
        self, df: pd.DataFrame, period: int = 5
    ) -> Dict[str, Optional[float]]:
        """
        计算量能分析指标

        包括：
        - 价格角度：通过线性回归计算价格上涨/下跌的角度
        - 动量强度：成交量加权的价格变化方向和强度
        - 量能力量：成交量与价格变化的综合力量

        Args:
            df: K线数据
            period: 计算周期

        Returns:
            包含 price_angle, momentum_strength, volume_power 的字典
        """
        if len(df) < period + 1:
            return {
                "price_angle": None,
                "momentum_strength": None,
                "volume_power": None,
            }

        try:
            # 取最近 period+1 天的数据
            recent_data = df.tail(period + 1).reset_index(drop=True)

            # 1. 计算价格角度（通过线性回归）
            x = np.arange(period + 1)
            y = recent_data["close"].values

            # 线性回归计算斜率
            slope, intercept = np.polyfit(x, y, 1)

            # 将斜率转换为角度（度）
            # 需要归一化，因为价格和时间的量纲不同
            price_range = y.max() - y.min()
            if price_range == 0:
                price_angle = 0.0
            else:
                # 归一化斜率：斜率 / (价格范围/时间范围)
                normalized_slope = slope / (price_range / period)
                price_angle = np.degrees(np.arctan(normalized_slope))

            # 2. 计算动量强度（成交量加权的平均价格变化）
            price_changes = recent_data["close"].diff().dropna()
            volumes = recent_data["volume"].iloc[1:].values

            if len(price_changes) > 0 and len(volumes) > 0:
                # 成交量加权的平均价格变化
                weighted_sum = np.sum(price_changes.values * volumes)
                volume_sum = np.sum(volumes)
                avg_volume = np.mean(volumes)

                if volume_sum > 0 and avg_volume > 0:
                    # 归一化的动量强度：-1 到 1
                    momentum_strength = weighted_sum / (volume_sum * recent_data["close"].std())
                    momentum_strength = max(-1.0, min(1.0, momentum_strength))
                else:
                    momentum_strength = 0.0
            else:
                momentum_strength = 0.0

            # 3. 计算量能力量（成交量比率 * 价格变化率）
            current_volume = recent_data["volume"].iloc[-1]
            avg_vol = recent_data["volume"].iloc[:-1].mean()
            price_change_rate = (recent_data["close"].iloc[-1] - recent_data["close"].iloc[0]) / recent_data["close"].iloc[0]

            if avg_vol > 0:
                volume_ratio = current_volume / avg_vol
                volume_power = volume_ratio * price_change_rate * 100  # 转换为百分比
            else:
                volume_power = 0.0

            return {
                "price_angle": round(float(price_angle), 2),
                "momentum_strength": round(float(momentum_strength), 4),
                "volume_power": round(float(volume_power), 4),
            }

        except Exception as e:
            logger.error(f"计算量能分析失败: {e}", exc_info=True)
            return {
                "price_angle": None,
                "momentum_strength": None,
                "volume_power": None,
            }

    def _calculate_momentum(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[float]]:
        """
        计算势能分析指标

        包括：
        - 3日动量：最近3天的价格变化率
        - 5日动量：最近5天的价格变化率
        - 加速度：动量的变化率（二阶导数）

        Args:
            df: K线数据

        Returns:
            包含 momentum_3d, momentum_5d, acceleration 的字典
        """
        if len(df) < 6:
            return {
                "momentum_3d": None,
                "momentum_5d": None,
                "acceleration": None,
            }

        try:
            closes = df["close"].values

            # 1. 计算3日动量（百分比变化）
            if len(closes) >= 4:
                momentum_3d = ((closes[-1] - closes[-4]) / closes[-4]) * 100
            else:
                momentum_3d = None

            # 2. 计算5日动量（百分比变化）
            if len(closes) >= 6:
                momentum_5d = ((closes[-1] - closes[-6]) / closes[-6]) * 100
            else:
                momentum_5d = None

            # 3. 计算加速度（动量的变化率）
            # 使用两个连续的3日动量来计算加速度
            if len(closes) >= 7:
                mom_current = ((closes[-1] - closes[-4]) / closes[-4]) * 100
                mom_previous = ((closes[-4] - closes[-7]) / closes[-7]) * 100
                acceleration = mom_current - mom_previous
            else:
                acceleration = None

            return {
                "momentum_3d": round(float(momentum_3d), 2) if momentum_3d is not None else None,
                "momentum_5d": round(float(momentum_5d), 2) if momentum_5d is not None else None,
                "acceleration": round(float(acceleration), 2) if acceleration is not None else None,
            }

        except Exception as e:
            logger.error(f"计算势能分析失败: {e}", exc_info=True)
            return {
                "momentum_3d": None,
                "momentum_5d": None,
                "acceleration": None,
            }

    def _empty_indicators(self, current_price: float) -> Dict[str, Any]:
        """返回空指标（数据不足时）"""
        return {
            "current_price": current_price,
            "ma5": None,
            "ma10": None,
            "ma20": None,
            "volume_ratio": None,
            "rsi": None,
            "macd_dif": None,
            "macd_dea": None,
            "price_change_pct": None,
            "price_angle": None,
            "momentum_strength": None,
            "volume_power": None,
            "momentum_3d": None,
            "momentum_5d": None,
            "acceleration": None,
        }
