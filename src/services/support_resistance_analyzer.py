# -*- coding: utf-8 -*-
"""
===================================
支撑压力位分析器
===================================

职责：
1. 多维度计算支撑位和压力位
2. 综合均线、布林带、筹码分布、前期高低点、斐波那契回撤等方法
3. 判断当前位置相对于支撑压力的关系
4. 为仓位建议提供技术依据
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class SupportResistanceAnalyzer:
    """
    支撑压力位分析器 - 多方法综合判断

    分析方法：
    1. 均线支撑 (MA5/MA10/MA20/MA60)
    2. 布林带上下轨
    3. 前期高低点密集区
    4. 筹码分布成本区间
    5. 斐波那契回撤位
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def analyze(
        self,
        df: pd.DataFrame,
        current_price: float,
        code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        综合分析支撑位和压力位

        Args:
            df: K线数据DataFrame，需包含 open/high/low/close/volume 列
            current_price: 当前价格
            code: 股票代码（用于获取筹码分布）

        Returns:
            {
                "support_levels": [
                    {"price": 1850.5, "method": "MA5", "strength": "strong", "description": "..."},
                    ...
                ],
                "resistance_levels": [
                    {"price": 1920.0, "method": "recent_high", "strength": "medium", "description": "..."},
                    ...
                ],
                "current_position": "near_support",  # near_support/near_resistance/between
                "nearest_support": 1850.5,
                "nearest_resistance": 1920.0,
                "distance_to_support_pct": 0.5,
                "distance_to_resistance_pct": 3.2
            }
        """
        if df is None or df.empty or len(df) < 20:
            self.logger.warning("数据不足，无法进行支撑压力分析")
            return self._empty_result()

        supports = []
        resistances = []

        # 方法1: 均线支撑
        try:
            ma_supports = self._ma_supports(df, current_price)
            supports.extend(ma_supports)
        except Exception as e:
            self.logger.debug(f"均线支撑计算失败: {e}")

        # 方法2: 布林带
        try:
            bb_supports, bb_resistances = self._bollinger_levels(df, current_price)
            supports.extend(bb_supports)
            resistances.extend(bb_resistances)
        except Exception as e:
            self.logger.debug(f"布林带计算失败: {e}")

        # 方法3: 前期高低点
        try:
            hl_supports, hl_resistances = self._high_low_points(df, current_price)
            supports.extend(hl_supports)
            resistances.extend(hl_resistances)
        except Exception as e:
            self.logger.debug(f"前期高低点计算失败: {e}")

        # 方法4: 筹码分布
        if code:
            try:
                chip_supports, chip_resistances = self._chip_distribution_levels(code, current_price)
                supports.extend(chip_supports)
                resistances.extend(chip_resistances)
            except Exception as e:
                self.logger.debug(f"筹码分布计算失败: {e}")

        # 方法5: 斐波那契回撤
        try:
            fib_supports, fib_resistances = self._fibonacci_retracement(df, current_price)
            supports.extend(fib_supports)
            resistances.extend(fib_resistances)
        except Exception as e:
            self.logger.debug(f"斐波那契回撤计算失败: {e}")

        # 去重并排序
        supports = self._deduplicate_and_sort(supports, current_price, direction="below")
        resistances = self._deduplicate_and_sort(resistances, current_price, direction="above")

        # 判断当前位置
        position = self._judge_current_position(current_price, supports, resistances)

        result = {
            "support_levels": supports[:5],  # 最多返回5个支撑位
            "resistance_levels": resistances[:5],  # 最多返回5个压力位
            "current_position": position["status"],
            "nearest_support": position["nearest_support"],
            "nearest_resistance": position["nearest_resistance"],
            "distance_to_support_pct": position["dist_support_pct"],
            "distance_to_resistance_pct": position["dist_resistance_pct"]
        }

        self.logger.info(
            f"支撑压力分析完成: {code or 'unknown'}, "
            f"支撑位{len(result['support_levels'])}个, 压力位{len(result['resistance_levels'])}个"
        )

        return result

    def _ma_supports(self, df: pd.DataFrame, current_price: float) -> List[Dict]:
        """均线支撑位"""
        supports = []

        # 确保有均线数据
        for period in [5, 10, 20, 60]:
            ma_col = f'MA{period}'
            if ma_col not in df.columns:
                # 尝试计算均线
                if 'close' in df.columns and len(df) >= period:
                    df[ma_col] = df['close'].rolling(window=period).mean()
                else:
                    continue

            ma_value = df[ma_col].iloc[-1]
            if pd.isna(ma_value) or ma_value <= 0:
                continue

            distance_pct = abs(current_price - ma_value) / ma_value * 100

            # 只有价格在均线上方或接近时才视为支撑
            if current_price >= ma_value * 0.98:  # 容忍2%误差
                strength = "strong" if distance_pct < 1 else "medium" if distance_pct < 3 else "weak"
                supports.append({
                    "price": round(float(ma_value), 2),
                    "method": f"MA{period}",
                    "strength": strength,
                    "description": f"{period}日均线支撑"
                })

        return supports

    def _bollinger_levels(self, df: pd.DataFrame, current_price: float) -> Tuple[List, List]:
        """布林带支撑压力位"""
        if 'close' not in df.columns or len(df) < 20:
            return [], []

        # 计算布林带
        middle = df['close'].rolling(window=20).mean().iloc[-1]
        std = df['close'].rolling(window=20).std().iloc[-1]

        if pd.isna(std) or std <= 0:
            return [], []

        upper = middle + 2 * std
        lower = middle - 2 * std

        supports = []
        resistances = []

        # 下轨作为支撑
        if current_price >= lower * 0.98:
            distance_pct = (current_price - lower) / lower * 100
            strength = "strong" if distance_pct < 2 else "medium" if distance_pct < 5 else "weak"
            supports.append({
                "price": round(float(lower), 2),
                "method": "bollinger_lower",
                "strength": strength,
                "description": f"布林带下轨支撑(中轨{round(float(middle), 2)})"
            })

        # 上轨作为压力
        if current_price <= upper * 1.02:
            distance_pct = (upper - current_price) / current_price * 100
            strength = "strong" if distance_pct < 2 else "medium" if distance_pct < 5 else "weak"
            resistances.append({
                "price": round(float(upper), 2),
                "method": "bollinger_upper",
                "strength": strength,
                "description": f"布林带上轨压力(中轨{round(float(middle), 2)})"
            })

        return supports, resistances

    def _high_low_points(self, df: pd.DataFrame, current_price: float) -> Tuple[List, List]:
        """前期高低点密集区"""
        if len(df) < 60:
            return [], []

        recent_data = df.tail(60)

        # 寻找局部低点(支撑)
        support_prices = set()
        for i in range(2, len(recent_data) - 2):
            low = recent_data['low'].iloc[i]
            if (low <= recent_data['low'].iloc[i-1] and
                low <= recent_data['low'].iloc[i-2] and
                low <= recent_data['low'].iloc[i+1] and
                low <= recent_data['low'].iloc[i+2]):
                if low < current_price * 0.98:  # 只取当前价格下方的
                    support_prices.add(round(float(low), 2))

        # 寻找局部高点(压力)
        resistance_prices = set()
        for i in range(2, len(recent_data) - 2):
            high = recent_data['high'].iloc[i]
            if (high >= recent_data['high'].iloc[i-1] and
                high >= recent_data['high'].iloc[i-2] and
                high >= recent_data['high'].iloc[i+1] and
                high >= recent_data['high'].iloc[i+2]):
                if high > current_price * 1.02:  # 只取当前价格上方的
                    resistance_prices.add(round(float(high), 2))

        # 转换为标准格式
        supports = [
            {"price": p, "method": "local_low", "strength": "medium", "description": "前期低点支撑"}
            for p in sorted(support_prices, reverse=True)[:3]
        ]
        resistances = [
            {"price": p, "method": "local_high", "strength": "medium", "description": "前期高点压力"}
            for p in sorted(resistance_prices)[:3]
        ]

        return supports, resistances

    def _chip_distribution_levels(self, code: str, current_price: float) -> Tuple[List, List]:
        """筹码分布支撑压力位"""
        from data_provider.base import DataFetcherManager

        manager = DataFetcherManager()
        chip = manager.get_chip_distribution(code)

        if not chip:
            return [], []

        supports = []
        resistances = []

        # 70%筹码成本区间作为强支撑/压力
        if chip.cost_70_low > 0 and chip.cost_70_low < current_price:
            supports.append({
                "price": round(float(chip.cost_70_low), 2),
                "method": "chip_cost_70_low",
                "strength": "strong",
                "description": f"70%筹码成本下限(集中度{chip.concentration_70*100:.1f}%)"
            })

        if chip.cost_70_high > 0 and chip.cost_70_high > current_price:
            resistances.append({
                "price": round(float(chip.cost_70_high), 2),
                "method": "chip_cost_70_high",
                "strength": "strong",
                "description": f"70%筹码成本上限(集中度{chip.concentration_70*100:.1f}%)"
            })

        # 平均成本作为中性参考
        if chip.avg_cost > 0:
            if chip.avg_cost < current_price:
                supports.append({
                    "price": round(float(chip.avg_cost), 2),
                    "method": "chip_avg_cost",
                    "strength": "medium",
                    "description": f"平均成本线(获利比例{chip.profit_ratio*100:.1f}%)"
                })
            else:
                resistances.append({
                    "price": round(float(chip.avg_cost), 2),
                    "method": "chip_avg_cost",
                    "strength": "medium",
                    "description": f"平均成本线(套牢比例{(1-chip.profit_ratio)*100:.1f}%)"
                })

        return supports, resistances

    def _fibonacci_retracement(self, df: pd.DataFrame, current_price: float) -> Tuple[List, List]:
        """斐波那契回撤位"""
        if len(df) < 60:
            return [], []

        # 找到最近的高点和低点
        recent_data = df.tail(60)
        high = recent_data['high'].max()
        low = recent_data['low'].min()

        if pd.isna(high) or pd.isna(low) or high <= low:
            return [], []

        diff = high - low

        # 斐波那契关键比例
        fib_levels = {
            "23.6%": 0.236,
            "38.2%": 0.382,
            "50.0%": 0.5,
            "61.8%": 0.618,
            "78.6%": 0.786
        }

        supports = []
        resistances = []

        for level_name, ratio in fib_levels.items():
            retracement_price = high - diff * ratio

            if retracement_price < current_price * 0.98:
                supports.append({
                    "price": round(float(retracement_price), 2),
                    "method": f"fib_{level_name}",
                    "strength": "weak",
                    "description": f"斐波那契{level_name}回撤位"
                })
            elif retracement_price > current_price * 1.02:
                resistances.append({
                    "price": round(float(retracement_price), 2),
                    "method": f"fib_{level_name}",
                    "strength": "weak",
                    "description": f"斐波那契{level_name}回撤位"
                })

        return supports, resistances

    def _deduplicate_and_sort(
        self,
        levels: List[Dict],
        current_price: float,
        direction: str = "below"
    ) -> List[Dict]:
        """
        去重并排序支撑/压力位

        Args:
            levels: 原始水平列表
            current_price: 当前价格
            direction: "below"(支撑，从高到低) 或 "above"(压力，从低到高)

        Returns:
            去重排序后的水平列表
        """
        if not levels:
            return []

        # 按价格去重（保留最强的）
        price_map = {}
        for level in levels:
            price = level["price"]
            if price not in price_map:
                price_map[price] = level
            else:
                # 如果已存在，保留强度更高的
                strength_order = {"strong": 3, "medium": 2, "weak": 1}
                existing_strength = strength_order.get(price_map[price]["strength"], 0)
                new_strength = strength_order.get(level["strength"], 0)
                if new_strength > existing_strength:
                    price_map[price] = level

        unique_levels = list(price_map.values())

        # 过滤并排序
        if direction == "below":
            # 支撑位：价格低于当前价，从高到低排序
            filtered = [
                level for level in unique_levels
                if level["price"] < current_price * 0.99
            ]
            filtered.sort(key=lambda x: x["price"], reverse=True)
        else:
            # 压力位：价格高于当前价，从低到高排序
            filtered = [
                level for level in unique_levels
                if level["price"] > current_price * 1.01
            ]
            filtered.sort(key=lambda x: x["price"])

        return filtered

    def _judge_current_position(
        self,
        current_price: float,
        supports: List[Dict],
        resistances: List[Dict]
    ) -> Dict:
        """判断当前位置相对于支撑压力的关系"""
        nearest_support = max([s["price"] for s in supports], default=0)
        nearest_resistance = min([r["price"] for r in resistances], default=float('inf'))

        dist_support_pct = ((current_price - nearest_support) / nearest_support * 100) if nearest_support > 0 else 0
        dist_resistance_pct = ((nearest_resistance - current_price) / current_price * 100) if nearest_resistance != float('inf') else 0

        # 判断状态
        if dist_support_pct < 2:
            status = "near_support"
        elif dist_resistance_pct < 2:
            status = "near_resistance"
        else:
            status = "between"

        return {
            "status": status,
            "nearest_support": nearest_support if nearest_support > 0 else None,
            "nearest_resistance": nearest_resistance if nearest_resistance != float('inf') else None,
            "dist_support_pct": round(dist_support_pct, 2),
            "dist_resistance_pct": round(dist_resistance_pct, 2)
        }

    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            "support_levels": [],
            "resistance_levels": [],
            "current_position": "unknown",
            "nearest_support": None,
            "nearest_resistance": None,
            "distance_to_support_pct": None,
            "distance_to_resistance_pct": None
        }
