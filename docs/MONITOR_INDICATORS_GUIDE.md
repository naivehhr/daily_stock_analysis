# 监控模块指标详细说明

## 📊 概述

监控模块提供 **7 种核心技术指标**，用于实时监控股票交易信号。每个指标都有独立的检测逻辑、触发条件和置信度计算方式。

本文档详细说明每个指标的计算方法、触发条件、参考价值和实战应用。

---

## 🎯 指标总览

| 指标名称 | 类型标识 | 核心功能 | 默认状态 |
|---------|---------|---------|---------|
| 价格突破 | `price_breakout` | 检测价格相对均线的突破 | ✅ 启用 |
| 成交量异常 | `volume_spike` | 检测成交量异常放大 | ✅ 启用 |
| 均线交叉 | `ma_cross` | 检测金叉/死叉信号 | ⚪ 可选 |
| RSI 信号 | `rsi_signal` | 检测超买/超卖状态 | ⚪ 可选 |
| MACD 信号 | `macd_signal` | 检测MACD金叉/死叉 | ⚪ 可选 |
| 势能分析 | `momentum` | 分析动量和加速度 | ✅ 启用 |
| 量能分析 | `volume_momentum` | 分析价格角度和力量强度 | ✅ 启用 |

---

## 1️⃣ 价格突破 (Price Breakout)

### 指标标识
```python
IndicatorType.PRICE_BREAKOUT = "price_breakout"
```

### 计算方法

检测当前价格相对于 **20日均线（MA20）** 的偏离程度：

```python
deviation_pct = abs((current_price - ma20) / ma20 * 100)

if deviation_pct >= threshold:  # 默认阈值 3.0%
    direction = "above" if current_price > ma20 else "below"
```

### 触发条件

- **向上突破**: 价格 > MA20 且偏离 ≥ 3%
- **向下突破**: 价格 < MA20 且偏离 ≥ 3%

### 信号类型

| 突破方向 | 信号类型 | 置信度计算 |
|---------|---------|-----------|
| 向上突破 | BUY (买入) | `min(0.9, 0.5 + deviation/100)` |
| 向下突破 | SELL (卖出) | `min(0.9, 0.5 + deviation/100)` |

### 参考价值

- **趋势确认**: 突破均线通常意味着趋势的开始或加速
- **支撑阻力**: MA20 是重要的中期支撑/阻力位
- **止损参考**: 跌破MA20可作为止损信号

### 实战案例

**贵州茅台 (600519)**
- 当前价: ¥1409.50
- MA20: ¥1437.82
- 偏离度: -1.97%
- 结果: 未达到3%阈值，未触发信号

### 可调参数

```python
price_breakout_threshold = 3.0  # 突破阈值（百分比）
```

**建议调整**:
- 短线交易: 2.0%（更敏感）
- 中线交易: 3.0%（默认）
- 长线交易: 5.0%（更稳定）

---

## 2️⃣ 成交量异常 (Volume Spike)

### 指标标识
```python
IndicatorType.VOLUME_SPIKE = "volume_spike"
```

### 计算方法

检测当前成交量相对于 **5日平均成交量** 的放大倍数：

```python
volume_ratio = current_volume / avg_volume_5d

if volume_ratio >= threshold:  # 默认阈值 2.0倍
    # 触发异常信号
```

### 触发条件

- 成交量 ≥ 5日均量的 **2.0 倍**

### 信号类型

根据价格变化方向判断信号类型：

| 量价配合 | 信号类型 | 置信度计算 |
|---------|---------|-----------|
| 放量上涨 | BUY (买入) | `min(0.85, 0.6 + (ratio-2)/10)` |
| 放量下跌 | SELL (卖出) | `min(0.85, 0.6 + (ratio-2)/10)` |

### 参考价值

- **资金动向**: 放量代表资金活跃度高
- **突破确认**: 放量突破比缩量突破更可靠
- **反转预警**: 高位放量可能是出货信号

### 典型场景

#### 场景1: 放量上涨（健康）
- 成交量: 5日均量的3倍
- 价格变化: +2.5%
- 信号: BUY，置信度 0.61
- 解读: 资金积极入场，趋势健康

#### 场景2: 放量下跌（危险）
- 成交量: 5日均量的4倍
- 价格变化: -3.2%
- 信号: SELL，置信度 0.62
- 解读: 恐慌性抛售，风险极大

#### 场景3: 缩量上涨（背离）
- 成交量: 5日均量的0.8倍
- 价格变化: +1.5%
- 结果: 未触发（需要≥2倍）
- 解读: 动能不足，警惕回调

### 可调参数

```python
volume_spike_ratio = 2.0  # 成交量异常倍数
```

**建议调整**:
- 高波动股票: 2.5倍（减少误报）
- 低波动股票: 1.5倍（提高灵敏度）

---

## 3️⃣ 均线交叉 (MA Cross)

### 指标标识
```python
IndicatorType.MA_CROSS = "ma_cross"
```

### 计算方法

检测 **MA5、MA10、MA20** 三条均线的排列关系：

```python
# 金叉：短均线上穿长均线
if ma5 > ma10 and ma5 > ma20:
    return {"type": "golden_cross", ...}

# 死叉：短均线下穿长均线
if ma5 < ma10 and ma5 < ma20:
    return {"type": "death_cross", ...}
```

### 触发条件

- **金叉**: MA5 > MA10 且 MA5 > MA20（多头排列）
- **死叉**: MA5 < MA10 且 MA5 < MA20（空头排列）

### 信号类型

| 交叉类型 | 信号类型 | 置信度 |
|---------|---------|-------|
| 金叉 | BUY (买入) | 0.75 |
| 死叉 | SELL (卖出) | 0.75 |

### 参考价值

- **趋势转折**: 金叉/死叉通常预示趋势反转
- **持仓决策**: 金叉可考虑建仓，死叉应考虑减仓
- **过滤震荡**: 均线缠绕时不产生信号

### 实战技巧

#### 金叉的可靠性排序
1. **三重金叉**: MA5上穿MA10，同时MA10上穿MA20 → 最可靠
2. **双重金叉**: MA5同时上穿MA10和MA20 → 较可靠
3. **单一金叉**: 仅MA5上穿MA10 → 需观察确认

#### 死叉的危险程度
1. **高位死叉**: 股价大幅上涨后出现 → 极度危险
2. **中位死叉**: 横盘后出现 → 中等风险
3. **低位死叉**: 已经下跌很多 → 可能见底

### 注意事项

- **滞后性**: 均线交叉有滞后，适合中长线
- **假信号**: 震荡市中容易产生假金叉/死叉
- **配合使用**: 需结合成交量和其他指标确认

---

## 4️⃣ RSI 信号 (RSI Signal)

### 指标标识
```python
IndicatorType.RSI_SIGNAL = "rsi_signal"
```

### 计算方法

RSI（相对强弱指标）计算公式：

```python
# 计算平均涨跌幅
avg_gain = rolling_mean(gains, period=14)
avg_loss = rolling_mean(losses, period=14)

# 计算RSI
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))
```

系统使用默认的 **14日周期** 计算RSI。

### 触发条件

- **超买**: RSI ≥ 70
- **超卖**: RSI ≤ 30

### 信号类型

| RSI 状态 | 信号类型 | 置信度计算 |
|---------|---------|-----------|
| 超买 (≥70) | SELL (卖出) | `min(0.85, 0.6 + (rsi-70)/100)` |
| 超卖 (≤30) | BUY (买入) | `min(0.85, 0.6 + (30-rsi)/100)` |

### 参考价值

- **超买预警**: RSI>70 表示市场过热，可能回调
- **超卖机会**: RSI<30 表示市场过度悲观，可能反弹
- **背离信号**: 价格创新高但RSI未创新高 → 顶背离

### RSI 区间解读

| RSI 范围 | 市场状态 | 操作建议 |
|---------|---------|---------|
| 80-100 | 极度超买 | 强烈卖出信号 |
| 70-80 | 超买 | 谨慎持有，准备减仓 |
| 50-70 | 强势区 | 持有多头仓位 |
| 30-50 | 弱势区 | 观望或轻仓 |
| 20-30 | 超卖 | 关注反弹机会 |
| 0-20 | 极度超卖 | 强烈买入信号 |

### 实战案例

**案例1: 超卖反弹**
- RSI: 25.3
- 信号: BUY，置信度 0.65
- 解读: 市场过度悲观，可能存在反弹机会

**案例2: 超买回调**
- RSI: 78.5
- 信号: SELL，置信度 0.69
- 解读: 市场过热，警惕回调风险

### 高级用法

#### RSI 背离
- **顶背离**: 价格创新高，RSI未创新高 → 看跌
- **底背离**: 价格创新低，RSI未创新低 → 看涨

#### RSI 双重穿越
- RSI 从下方穿越50后再次回踩50不破 → 强势确认
- RSI 从上方穿越50后再次反弹50不过 → 弱势确认

### 可调参数

```python
rsi_overbought = 70.0   # 超买阈值
rsi_oversold = 30.0     # 超卖阈值
```

**建议调整**:
- 保守策略: 超买75/超卖25（减少交易频率）
- 激进策略: 超买65/超卖35（增加交易机会）

---

## 5️⃣ MACD 信号 (MACD Signal)

### 指标标识
```python
IndicatorType.MACD_SIGNAL = "macd_signal"
```

### 计算方法

MACD（指数平滑异同移动平均线）由三部分组成：

```python
# 快线 DIF = EMA(12) - EMA(26)
dif = ema(close, 12) - ema(close, 26)

# 慢线 DEA = EMA(DIF, 9)
dea = ema(dif, 9)

# 柱状图 MACD = (DIF - DEA) * 2
macd_bar = (dif - dea) * 2
```

### 触发条件

- **金叉**: DIF > DEA 且 DIF > 0
- **死叉**: DIF < DEA 且 DIF < 0

### 信号类型

| 交叉类型 | 信号类型 | 置信度 |
|---------|---------|-------|
| 金叉 (零轴上方) | BUY (买入) | 0.70 |
| 死叉 (零轴下方) | SELL (卖出) | 0.70 |

### 参考价值

- **趋势强度**: MACD在零轴上方表示多头市场
- **买卖时机**: 金叉买入，死叉卖出
- **背离信号**: MACD与价格背离预示反转

### MACD 形态解读

#### 1. 零轴上方金叉（最强买入信号）
- DIF 和 DEA 都在零轴上方
- DIF 上穿 DEA
- 解读: 强势市场中的二次启动

#### 2. 零轴下方金叉（弱势反弹）
- DIF 和 DEA 都在零轴下方
- DIF 上穿 DEA
- 解读: 超跌反弹，持续性待观察

#### 3. 零轴上方死叉（高位回调）
- DIF 和 DEA 都在零轴上方
- DIF 下穿 DEA
- 解读: 上升趋势中的正常回调

#### 4. 零轴下方死叉（最弱卖出信号）
- DIF 和 DEA 都在零轴下方
- DIF 下穿 DEA
- 解读: 弱势市场继续下行

### MACD 柱状图应用

- **红柱放大**: 多头力量增强
- **红柱缩小**: 多头力量减弱
- **绿柱放大**: 空头力量增强
- **绿柱缩小**: 空头力量减弱

### 实战技巧

#### MACD 空中加油
- DIF 回调接近 DEA 但不死叉，然后再次向上发散
- 解读: 强势整理后的继续上涨

#### MACD 水下金叉
- 在零轴下方的金叉，如果伴随放量，可能是底部信号
- 需等待DIF突破零轴确认

### 注意事项

- **滞后性**: MACD是滞后指标，适合趋势跟踪
- **震荡市失效**: 横盘时频繁金叉死叉，产生假信号
- **配合使用**: 需结合K线形态和成交量

---

## 6️⃣ 势能分析 (Momentum)

### 指标标识
```python
IndicatorType.MOMENTUM = "momentum"
```

### 计算方法

势能分析包含三个维度：

#### 1. 3日动量 (momentum_3d)
```python
momentum_3d = ((close[-1] - close[-4]) / close[-4]) * 100
```

#### 2. 5日动量 (momentum_5d)
```python
momentum_5d = ((close[-1] - close[-6]) / close[-6]) * 100
```

#### 3. 加速度 (acceleration)
```python
acceleration = momentum_3d - momentum_5d
```

### 触发条件

#### A. 强势动量信号

**强势上涨**:
- momentum_3d > 3.0% 且 momentum_5d > 5.0%
- 置信度: `min(0.85, 0.6 + momentum_3d/100 + momentum_5d/100)`

**强势下跌**:
- momentum_3d < -3.0% 且 momentum_5d < -5.0%
- 置信度: `min(0.85, 0.6 + |momentum_3d|/100 + |momentum_5d|/100)`

#### B. 加速度信号

**加速上涨**:
- acceleration > 2.0% 且 momentum_3d > 0
- 置信度: `min(0.8, 0.6 + acceleration/20)`

**加速下跌**:
- acceleration < -2.0% 且 momentum_3d < 0
- 置信度: `min(0.8, 0.6 + |acceleration|/20)`

**减速反转**:
- |acceleration| > 3.0%
- 信号类型与动量方向相反（警示反转）
- 置信度: 0.65

### 信号类型

| 动量状态 | 信号类型 | 示例描述 |
|---------|---------|---------|
| 强势上涨 | BUY | "强势上涨动量：3日+4.2%, 5日+6.8%" |
| 强势下跌 | SELL | "强势下跌动量：3日-4.5%, 5日-7.2%" |
| 加速上涨 | BUY | "加速上涨：加速度+2.5%，动能增强" |
| 加速下跌 | SELL | "加速下跌：加速度-3.1%，动能减弱" |
| 上涨减速 | SELL | "上涨减速：加速度-3.5%，警惕趋势反转" |
| 下跌减速 | BUY | "下跌减速：加速度+4.2%，警惕趋势反转" |

### 参考价值

- **趋势强度**: 动量大小反映趋势的强弱
- **趋势延续**: 加速度为正表示趋势在加强
- **反转预警**: 加速度为负且绝对值大，预示可能反转

### 实战应用

#### 场景1: 强势上涨
- 3日动量: +5.2%
- 5日动量: +8.1%
- 加速度: -2.9%
- 信号: BUY（强势）+ WATCH（减速警示）
- 解读: 虽然仍在上涨，但动能开始减弱，警惕回调

#### 场景2: 加速下跌
- 3日动量: -4.8%
- 5日动量: -6.5%
- 加速度: +1.7%
- 信号: SELL（强势下跌）
- 解读: 下跌趋势明确，但加速度为正，可能即将企稳

#### 场景3: 底部反转
- 3日动量: -1.2%
- 5日动量: -3.5%
- 加速度: +2.3%
- 信号: BUY（下跌减速）
- 解读: 下跌动能明显减弱，可能见底

### 动量矩阵

| 3日动量 | 5日动量 | 加速度 | 市场状态 | 操作建议 |
|--------|--------|-------|---------|---------|
| >3% | >5% | >0 | 加速上涨 | 持有/加仓 |
| >3% | >5% | <0 | 上涨减速 | 分批止盈 |
| <-3% | <-5% | <0 | 加速下跌 | 止损/空仓 |
| <-3% | <-5% | >0 | 下跌减速 | 关注反弹 |
| -1~1% | -2~2% | ±小 | 横盘震荡 | 观望 |

---

## 7️⃣ 量能分析 (Volume Momentum)

### 指标标识
```python
IndicatorType.VOLUME_MOMENTUM = "volume_momentum"
```

> 💡 **详细说明**: 量能分析的完整技术文档请参见 [VOLUME_MOMENTUM_ANALYSIS.md](./VOLUME_MOMENTUM_ANALYSIS.md)

### 计算方法

量能分析包含三个核心指标：

#### 1. 价格角度 (price_angle)
通过线性回归计算最近5天价格走势的角度（-90° ~ +90°）

```python
slope, intercept = np.polyfit(x, y, 1)
normalized_slope = slope / (price_range / period)
price_angle = np.degrees(np.arctan(normalized_slope))
```

#### 2. 动量强度 (momentum_strength)
成交量加权的价格变化方向和强度（-1 ~ +1）

```python
weighted_sum = sum(price_changes * volumes)
momentum_strength = weighted_sum / (volume_sum * price_std)
```

#### 3. 量能力量 (volume_power)
成交量倍数与价格变化率的乘积

```python
volume_ratio = current_volume / avg_volume
price_change_rate = (close[-1] - close[0]) / close[0]
volume_power = volume_ratio * price_change_rate * 100
```

### 触发条件

#### A. 价格角度信号

**陡峭上涨**:
- price_angle > 30°
- 置信度: `min(0.85, 0.6 + price_angle/200)`

**陡峭下跌**:
- price_angle < -30°
- 置信度: `min(0.85, 0.6 + |price_angle|/200)`

#### B. 动量强度信号

**强上涨力量**:
- momentum_strength > 0.5
- 置信度: `min(0.85, 0.6 + momentum_strength/4)`

**强下跌力量**:
- momentum_strength < -0.5
- 置信度: `min(0.85, 0.6 + |momentum_strength|/4)`

#### C. 量能力量信号

**量价齐升**:
- volume_power > 5.0
- 置信度: `min(0.8, 0.6 + volume_power/50)`

**量增价跌**:
- volume_power < -5.0
- 置信度: `min(0.8, 0.6 + |volume_power|/50)`

**缩量上涨** (警示):
- 0 < volume_power < 2.0 且 momentum_strength > 0.3
- 信号类型: WATCH
- 置信度: 0.6

**缩量下跌** (可能见底):
- -2.0 < volume_power < 0 且 momentum_strength < -0.3
- 信号类型: WATCH
- 置信度: 0.6

### 信号类型

| 指标 | 条件 | 信号类型 | 示例描述 |
|-----|------|---------|---------|
| 价格角度 | >30° | BUY | "陡峭上涨角度：45.2°，上升力量强劲" |
| 价格角度 | <-30° | SELL | "陡峭下跌角度：-46.1°，下降压力巨大" |
| 动量强度 | >0.5 | BUY | "强上涨力量：动量强度0.72，买方主导" |
| 动量强度 | <-0.5 | SELL | "强下跌力量：动量强度-0.92，卖方主导" |
| 量能力量 | >5.0 | BUY | "量价齐升：量能力量8.5，资金积极入场" |
| 量能力量 | <-5.0 | SELL | "量增价跌：量能力量-12.3，抛压沉重" |
| 量能力量 | 0~2 | WATCH | "缩量上涨：量能力量1.2，量价背离需警惕" |
| 量能力量 | -2~0 | WATCH | "缩量下跌：量能力量-0.8，抛压减弱或见底" |

### 参考价值

- **趋势质量**: 角度越陡，趋势越强
- **资金态度**: 动量强度反映买卖双方的力量对比
- **量价配合**: 量能力量揭示成交量与价格的协调性

### 三指标共振系统

#### 强烈买入信号
✅ 价格角度 > 30°  
✅ 动量强度 > 0.5  
✅ 量能力量 > 5  

**示例**: 角度45° + 强度0.7 + 力量8.5 = 高置信度买入

#### 强烈卖出信号
❌ 价格角度 < -30°  
❌ 动量强度 < -0.5  
❌ 量能力量 < -5  

**示例**: 角度-46° + 强度-0.92 + 力量-2.48 = 高置信度卖出

### 实战案例

**贵州茅台 (600519)** - 2026-04-22
- 价格角度: **-46.1°** （陡峭下跌）
- 动量强度: **-0.92** （极强下跌力量）
- 量能力量: **-2.48** （温和放量下跌）
- 触发信号: 
  - SELL: "陡峭下跌角度：-46.1°，下降压力巨大" (置信度83%)
  - SELL: "强下跌力量：动量强度-0.92，卖方主导" (置信度83%)
- AI建议: "技术面显示明显下跌压力，建议观望等待企稳信号"

### 背离预警

#### 顶背离（看跌）
- 价格创新高，但角度减小、强度减弱
- 操作: 逐步减仓，准备止盈

#### 底背离（看涨）
- 价格创新低，但角度趋缓、强度改善
- 操作: 分批建仓，等待确认

### 与其他指标配合

- **均线系统**: 角度向上 + 多头排列 = 强势上涨
- **RSI指标**: 角度向上 + RSI<70 = 健康上涨；角度向上 + RSI>80 = 超买风险
- **MACD指标**: 角度向上 + MACD金叉 = 双重买入确认

---

## 🎯 综合应用策略

### 1. 指标组合推荐

#### 保守型配置（低频高质）
```python
indicators = [
    IndicatorType.PRICE_BREAKOUT,  # 价格突破
    IndicatorType.VOLUME_SPIKE,    # 成交量异常
    IndicatorType.MA_CROSS,        # 均线交叉
]
```
**特点**: 信号少但可靠性高，适合中长线

#### 平衡型配置（默认推荐）
```python
indicators = [
    IndicatorType.PRICE_BREAKOUT,      # 价格突破
    IndicatorType.VOLUME_SPIKE,        # 成交量异常
    IndicatorType.MOMENTUM,            # 势能分析
    IndicatorType.VOLUME_MOMENTUM,     # 量能分析
]
```
**特点**: 兼顾灵敏度和稳定性，适合大多数场景

#### 激进型配置（高频全面）
```python
indicators = [
    IndicatorType.PRICE_BREAKOUT,      # 价格突破
    IndicatorType.VOLUME_SPIKE,        # 成交量异常
    IndicatorType.MA_CROSS,            # 均线交叉
    IndicatorType.RSI_SIGNAL,          # RSI 信号
    IndicatorType.MACD_SIGNAL,         # MACD 信号
    IndicatorType.MOMENTUM,            # 势能分析
    IndicatorType.VOLUME_MOMENTUM,     # 量能分析
]
```
**特点**: 信号多覆盖全，适合短线交易

### 2. 信号优先级

当多个指标同时触发时，按以下优先级处理：

1. **量能分析** (volume_momentum) - 最高优先级
   - 综合了价格、成交量、动量三个维度
   - 信号最全面，置信度计算最科学

2. **势能分析** (momentum) - 高优先级
   - 反映短期动能变化
   - 对趋势反转敏感

3. **价格突破** (price_breakout) - 中高优先级
   - 直接反映价格相对位置
   - 简单有效

4. **成交量异常** (volume_spike) - 中优先级
   - 反映资金活跃度
   - 需配合价格方向

5. **MACD 信号** (macd_signal) - 中低优先级
   - 趋势跟踪指标
   - 有一定滞后性

6. **均线交叉** (ma_cross) - 低优先级
   - 滞后性较强
   - 适合确认趋势

7. **RSI 信号** (rsi_signal) - 辅助优先级
   - 超买超卖参考
   - 单独使用可靠性较低

### 3. 置信度融合

当同一方向有多个信号时，可以融合置信度：

```python
# 简单平均
final_confidence = mean([sig.confidence for sig in buy_signals])

# 加权平均（高优先级指标权重更高）
weights = {
    "volume_momentum": 0.3,
    "momentum": 0.25,
    "price_breakout": 0.2,
    "volume_spike": 0.15,
    "macd_signal": 0.05,
    "ma_cross": 0.03,
    "rsi_signal": 0.02,
}
```

### 4. 风险控制

#### 止损策略
- **固定止损**: 亏损达到5%立即止损
- **技术止损**: 跌破关键均线（如MA20）止损
- **信号止损**: 出现反向高置信度信号止损

#### 仓位管理
- **单信号**: 轻仓试探（10-20%仓位）
- **双信号共振**: 标准仓位（30-50%）
- **三信号以上**: 重仓出击（60-80%）

#### 止盈策略
- **目标止盈**: 达到预设收益目标（如10%）
- **信号止盈**: 出现反向信号时止盈
- **移动止盈**: 随价格上涨提高止损位

---

## 🔧 技术实现

### 代码结构

```
src/monitor/
├── schemas.py              # 指标类型定义
├── indicators.py           # 指标计算器
├── signal_detector.py      # 信号检测器
├── core.py                 # 监控引擎
└── report_generator.py     # 报告生成器
```

### 关键类和方法

#### IndicatorsCalculator
```python
class IndicatorsCalculator:
    def calculate_all(df, current_price) -> Dict[str, Any]
    def check_price_breakout(current_price, ma20) -> Optional[Dict]
    def check_volume_spike(volume_ratio) -> Optional[Dict]
    def check_rsi_signal(rsi) -> Optional[Dict]
    def check_ma_cross(ma5, ma10, ma20) -> Optional[Dict]
    def _calculate_volume_momentum(df) -> Dict[str, float]
    def _calculate_momentum(df) -> Dict[str, float]
```

#### SignalDetector
```python
class SignalDetector:
    def detect_signals(indicators, enabled_indicators) -> List[MonitorSignal]
    def _detect_price_breakout(indicators) -> List[MonitorSignal]
    def _detect_volume_spike(indicators) -> List[MonitorSignal]
    def _detect_ma_cross(indicators) -> List[MonitorSignal]
    def _detect_rsi_signal(indicators) -> List[MonitorSignal]
    def _detect_macd_signal(indicators) -> List[MonitorSignal]
    def _detect_momentum_signal(indicators) -> List[MonitorSignal]
    def _detect_volume_momentum_signal(indicators) -> List[MonitorSignal]
```

### 数据流

```
历史K线数据 + 实时行情
       ↓
IndicatorsCalculator.calculate_all()
       ↓
技术指标字典 (indicators)
       ↓
SignalDetector.detect_signals()
       ↓
MonitorSignal 列表
       ↓
MonitorAgent (LLM 分析)
       ↓
分析报告 + 通知推送
```

---

## 📈 性能优化

### 1. 并发处理

监控引擎支持并发处理多只股票：

```python
results = await asyncio.gather(
    *[analyze_stock(code) for code in stock_codes]
)
```

### 2. 缓存机制

- 历史数据缓存：避免重复获取
- 指标计算缓存：相同参数不重复计算
- LLM响应缓存：相似问题复用答案

### 3. 异步通知

通知推送采用异步方式，不阻塞主流程：

```python
asyncio.create_task(notifier.send(report))
```

---

## 📚 相关文档

- [量能分析详细说明](./VOLUME_MOMENTUM_ANALYSIS.md)
- [监控系统使用指南](./monitor_guide.md)
- [API 接口文档](../api/README.md)
- [Bot 命令说明](./bot-command.md)

---

## ❓ 常见问题

### Q1: 为什么有些指标没有触发信号？
**A**: 每个指标都有严格的触发条件，只有满足条件才会产生信号。这是为了避免噪音和假信号。

### Q2: 如何选择适合的指标组合？
**A**: 
- 新手: 使用默认的平衡型配置
- 短线交易者: 使用激进型配置
- 长线投资者: 使用保守型配置

### Q3: 信号的置信度可信吗？
**A**: 置信度是基于历史数据统计得出的经验值，仅供参考。实际交易中还需结合市场环境和个人判断。

### Q4: 如何调整指标的灵敏度？
**A**: 可以在初始化 `MonitorEngine` 时传入自定义参数：
```python
engine = MonitorEngine(
    price_breakout_threshold=2.0,  # 降低阈值提高灵敏度
    volume_spike_ratio=1.5,
    rsi_overbought=65,
    rsi_oversold=35,
)
```

### Q5: 监控模块会自动运行吗？
**A**: 不会。监控模块需要通过 API 或 Bot 命令手动触发，或者配置定时任务自动执行。

---

**最后更新**: 2026-04-22  
**维护者**: DSA 开发团队  
**版本**: v1.0
