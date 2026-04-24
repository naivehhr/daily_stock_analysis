# -*- coding: utf-8 -*-
"""
===================================
仓位建议 Agent
===================================

职责：
1. 基于技术分析和支撑压力位给出专业仓位建议
2. 制定突破策略（向上突破压力位/向下击穿支撑位）
3. 提供风险管理建议（止损/止盈价位）
4. 输出结构化的仓位管理方案
"""

import logging
from typing import Optional, Dict, Any

from src.agent.agents.base_agent import BaseAgent
from src.agent.protocols import AgentContext, AgentOpinion
from src.agent.runner import try_parse_json

logger = logging.getLogger(__name__)


class PositionAdvisorAgent(BaseAgent):
    """
    仓位建议 Agent - 基于技术分析和支撑压力位给出专业建议

    分析维度：
    1. 趋势判断（多头/空头/震荡）
    2. 支撑压力位强度和距离
    3. 筹码分布健康度
    4. 风险收益比评估
    5. 突破策略制定
    """

    agent_name = "position_advisor"
    max_steps = 3  # 最多调用3次工具

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tool_names = ["get_daily_history", "analyze_trend", "get_chip_distribution"]
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def system_prompt(self, ctx: AgentContext) -> str:
        """构建 system prompt"""
        return """\
You are a **Position Advisory Specialist** providing professional position management advice for stock trading.

## Your Role
Analyze the stock's technical indicators, support/resistance levels, and chip distribution to provide actionable position sizing recommendations.

## Analysis Framework

### 1. Position Sizing Logic
Recommend one of five position levels based on risk-reward assessment:

- **Full Position (100%)**: 
  - Strong bullish trend (MA5>MA10>MA20, trend_score>75)
  - Price near strong support (<2% distance)
  - High chip profit ratio (>70%) with concentrated chips
  - Clear upward breakout confirmed by volume
  
- **Heavy Position (75%)**: 
  - Bullish trend with good entry point
  - Moderate support strength
  - Positive momentum indicators
  
- **Half Position (50%)**: 
  - Neutral trend or uncertain direction
  - Price between support and resistance
  - Mixed signals from indicators
  
- **Light Position (25%)**: 
  - Bearish trend but potential reversal signs
  - Near support but weak confirmation
  - Defensive stance with upside potential
  
- **Empty Position (0%)**: 
  - Strong bearish trend (MA5<MA10<MA20, trend_score<25)
  - Price breaking below key support
  - High risk environment

### 2. Support/Resistance Assessment
Evaluate each level's strength:
- **Strong**: Multiple methods confirm (e.g., MA + chip cost + previous low)
- **Medium**: Single reliable method (e.g., Bollinger band)
- **Weak**: Only one weak signal (e.g., Fibonacci alone)

Key methods to consider:
- Moving averages (MA5/MA10/MA20/MA60)
- Bollinger Bands (upper/lower rails)
- Previous highs/lows (local extrema)
- Chip distribution cost zones (70% range)
- Fibonacci retracement levels

### 3. Breakout Strategy Formulation

**Upward Breakout (Resistance Breakthrough)**:
- Confirmation criteria: Volume > 20% above average + close above resistance
- Action: Add 25% position if already holding, or enter with 50% if empty
- Target: Next resistance level or 1.5x risk-reward ratio
- False breakout protection: If price falls back below resistance within 2 days, reduce position

**Downward Breakdown (Support Breach)**:
- Immediate action: Reduce to light position or exit completely
- Stop-loss: 2-3% below broken support level
- Re-entry: Wait for stabilization (3+ days above new support) + volume confirmation
- Avoid: Catching falling knife without clear reversal signals

### 4. Risk-Reward Calculation
Calculate before recommending position:
- Upside potential: Distance to next resistance
- Downside risk: Distance to next support
- Only recommend positions if reward/risk ratio >= 1.5
- Adjust position size inversely with risk level

### 5. Market Context Integration
Consider broader factors:
- Overall market trend (bull/bear/sideways)
- Sector rotation and hot themes
- Volume trends (increasing/decreasing)
- Chip concentration changes

## Output Format
Return **ONLY** a valid JSON object (no markdown, no code blocks):

{
  "position_advice": "half",
  "confidence": 0.75,
  "reasoning": "Concise 2-3 sentence explanation of position sizing logic, referencing key technical factors",
  
  "support_levels": [
    {"price": 1850.5, "method": "MA5", "strength": "strong", "description": "5-day moving average support with price hovering within 1%"},
    {"price": 1780.0, "method": "chip_cost_70_low", "strength": "strong", "description": "70% chip cost lower bound indicating strong institutional support"}
  ],
  "resistance_levels": [
    {"price": 1920.0, "method": "recent_high", "strength": "medium", "description": "Recent 20-day high acting as immediate resistance"},
    {"price": 1950.0, "method": "bollinger_upper", "strength": "medium", "description": "Bollinger upper band suggesting overbought territory"}
  ],
  
  "breakout_strategy": {
    "upward_breakout": "If price breaks above 1920 with volume surge (>20% above 5-day avg), add 25% position. First target: 1950 (Bollinger upper). Stop-loss: 1890 (below breakout level).",
    "downward_breakdown": "If price drops below 1850 (MA5), immediately reduce to 25% position. Critical support at 1820 (MA10). If 1820 breaks, exit completely. Wait for 3-day consolidation above new support before re-entry."
  },
  
  "risk_management": {
    "stop_loss_price": 1820.0,
    "take_profit_price": 1950.0,
    "risk_reward_ratio": 2.5,
    "max_position_size": 0.75,
    "notes": "Reduce position if volume decreases for 3 consecutive days"
  },
  
  "market_context": {
    "trend_status": "bullish",
    "volume_status": "normal",
    "chip_profit_ratio": 0.67,
    "key_observation": "Price consolidating near MA5 support with healthy chip distribution"
  }
}

## Important Rules
1. **Be conservative**: When uncertain, recommend lighter positions
2. **Always calculate risk-reward**: Never recommend positions without favorable R/R ratio
3. **Provide specific prices**: Use exact numbers, not vague ranges
4. **Explain logic clearly**: Connect technical signals to position recommendation
5. **Consider multiple timeframes**: Balance short-term signals with medium-term trend
6. **Account for chip distribution**: High profit ratio + concentration = stronger support
7. **Volume confirmation matters**: Breakouts without volume are suspect

## Language
Respond in Chinese (简体中文) to match user's language preference.
"""

    def build_user_message(self, ctx: AgentContext) -> str:
        """构建用户消息"""
        stock_code = getattr(ctx, 'stock_code', 'unknown')
        current_price = getattr(ctx, 'current_price', 0)
        
        # 获取技术分析数据
        technical_data = getattr(ctx, 'technical_data', {})
        sr_data = getattr(ctx, 'sr_data', {})
        chip_data = getattr(ctx, 'chip_data', {})
        strategy_context = getattr(ctx, 'strategy_context', {})
        
        message_parts = [
            f"# 股票分析请求: {stock_code}",
            f"\n当前价格: {current_price:.2f}元",
        ]
        
        # 技术指标
        if technical_data:
            message_parts.append("\n## 技术指标")
            if 'trend_status' in technical_data:
                message_parts.append(f"- 趋势状态: {technical_data['trend_status']}")
            if 'ma_alignment' in technical_data:
                message_parts.append(f"- 均线排列: {technical_data['ma_alignment']}")
            if 'signal_score' in technical_data:
                message_parts.append(f"- 信号评分: {technical_data['signal_score']}/100")
            if 'macd_status' in technical_data:
                message_parts.append(f"- MACD状态: {technical_data['macd_status']}")
            if 'rsi_status' in technical_data:
                message_parts.append(f"- RSI状态: {technical_data['rsi_status']}")
        
        # 支撑压力位
        if sr_data:
            message_parts.append("\n## 支撑压力位分析")
            supports = sr_data.get('support_levels', [])
            resistances = sr_data.get('resistance_levels', [])
            
            if supports:
                message_parts.append(f"\n### 支撑位 ({len(supports)}个)")
                for i, s in enumerate(supports[:3], 1):
                    message_parts.append(
                        f"{i}. {s['price']:.2f}元 ({s['method']}, 强度:{s['strength']}) - {s.get('description', '')}"
                    )
            
            if resistances:
                message_parts.append(f"\n### 压力位 ({len(resistances)}个)")
                for i, r in enumerate(resistances[:3], 1):
                    message_parts.append(
                        f"{i}. {r['price']:.2f}元 ({r['method']}, 强度:{r['strength']}) - {r.get('description', '')}"
                    )
            
            position = sr_data.get('current_position', 'unknown')
            dist_support = sr_data.get('distance_to_support_pct')
            dist_resistance = sr_data.get('distance_to_resistance_pct')
            
            if position:
                message_parts.append(f"\n当前位置: {position}")
            if dist_support is not None:
                message_parts.append(f"距离最近支撑: {dist_support:.2f}%")
            if dist_resistance is not None:
                message_parts.append(f"距离最近压力: {dist_resistance:.2f}%")
        
        # 筹码分布
        if chip_data:
            message_parts.append("\n## 筹码分布")
            if 'profit_ratio' in chip_data:
                message_parts.append(f"- 获利比例: {chip_data['profit_ratio']*100:.1f}%")
            if 'avg_cost' in chip_data:
                message_parts.append(f"- 平均成本: {chip_data['avg_cost']:.2f}元")
            if 'concentration_70' in chip_data:
                message_parts.append(f"- 70%筹码集中度: {chip_data['concentration_70']*100:.1f}%")
        
        # 策略上下文
        if strategy_context:
            message_parts.append("\n## 策略触发情况")
            if strategy_context.get('buy_signal'):
                message_parts.append("- ⚠️ 买入条件已触发")
            if strategy_context.get('sell_signal'):
                message_parts.append("- ⚠️ 卖出条件已触发")
            if strategy_context.get('position_advice'):
                message_parts.append(f"- 策略建议仓位: {strategy_context['position_advice']}")
        
        message_parts.append(
            "\n\n请根据以上信息，提供专业的仓位建议和突破策略。"
        )
        
        return "\n".join(message_parts)

    def post_process(self, ctx: AgentContext, raw_text: str) -> Optional[AgentOpinion]:
        """解析 LLM 输出"""
        try:
            parsed = try_parse_json(raw_text)
            if not parsed:
                self.logger.warning(f"无法解析JSON: {raw_text[:200]}")
                return None
            
            # 验证必需字段
            required_fields = ['position_advice', 'confidence', 'reasoning']
            for field in required_fields:
                if field not in parsed:
                    self.logger.warning(f"缺少必需字段: {field}")
                    return None
            
            # 验证 position_advice 的有效性
            valid_positions = ['empty', 'light', 'half', 'heavy', 'full']
            if parsed['position_advice'] not in valid_positions:
                self.logger.warning(f"无效的仓位建议: {parsed['position_advice']}")
                return None
            
            # 验证 confidence 范围
            confidence = float(parsed.get('confidence', 0.5))
            if not (0 <= confidence <= 1):
                confidence = max(0, min(1, confidence))
                parsed['confidence'] = confidence
            
            return AgentOpinion(
                agent_name=self.agent_name,
                signal=parsed['position_advice'],
                confidence=confidence,
                reasoning=parsed.get('reasoning', ''),
                raw_data=parsed
            )
        except Exception as e:
            self.logger.error(f"后处理失败: {e}")
            return None
