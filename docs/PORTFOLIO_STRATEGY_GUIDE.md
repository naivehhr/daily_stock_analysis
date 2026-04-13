# 持仓策略定制指南 / Portfolio Strategy Customization Guide

本文档详细说明如何基于持仓信息，使用自定义策略生成每日交易建议。

## 📋 目录

- [快速开始](#快速开始)
- [第1步：配置持仓信息](#第1步配置持仓信息)
- [第2步：选择或创建策略](#第2步选择或创建策略)
- [第3步：运行分析](#第3步运行分析)
- [第4步：查看交易建议](#第4步查看交易建议)
- [高级用法](#高级用法)
- [常见问题](#常见问题)

---

## 🚀 快速开始

### 前置条件

1. ✅ 已配置 AI 模型（Gemini/DeepSeek/OpenAI 等）
2. ✅ 已安装依赖：`pip install -r requirements.txt`
3. ✅ 已配置通知渠道（企业微信/飞书/邮件等，可选）

### 5分钟快速体验

```bash
# 1. 启用 Agent 模式并选择策略
echo "AGENT_MODE=true" >> .env
echo "AGENT_SKILLS=ma_golden_cross" >> .env

# 2. 添加要分析的股票
echo "STOCK_LIST=600519,300750" >> .env

# 3. 运行分析
python main.py --stocks 600519

# 4. 查看生成的交易建议（包含买卖点位）
```

---

## 第1步：配置持仓信息

### 方式 A：通过 Web 界面（推荐）

1. **启动 Web 服务**
   ```bash
   python main.py --serve
   # 或
   python webui.py
   ```

2. **访问持仓管理页面**
   - 打开浏览器访问：`http://localhost:8000/portfolio`
   - 首次使用需登录（如启用了认证）

3. **创建账户**
   - 点击"新建账户"
   - 填写账户名称（如"我的主账户"）
   - 选择基础货币（CNY/USD/HKD）

4. **添加持仓**
   - 点击"添加持仓"或"记录交易"
   - 填写以下信息：
     - **股票代码**：如 `600519`（A股）、`AAPL`（美股）、`00700`（港股）
     - **买入日期**：实际买入日期
     - **买入数量**：持仓股数
     - **买入价格**：成本价
     - **市场类型**：cn（A股）/ us（美股）/ hk（港股）

5. **查看持仓概览**
   - 系统自动计算：
     - 当前市值
     - 浮动盈亏
     - 持仓占比
     - 风险预警

### 方式 B：通过 Python API 导入

创建脚本 `import_portfolio.py`：

```python
#!/usr/bin/env python3
"""批量导入持仓示例"""

from datetime import date
from src.services.portfolio_service import PortfolioService

def import_my_portfolio():
    service = PortfolioService()
    
    # 1. 创建账户
    account_id = service.create_account(
        account_name="我的主账户",
        base_currency="CNY",
        description="个人投资账户"
    )
    print(f"✅ 创建账户成功，ID: {account_id}")
    
    # 2. 记录初始资金
    service.record_cash_ledger(
        account_id=account_id,
        event_date=date(2024, 1, 1),
        direction="in",
        amount=500000,  # 入金50万
        currency="CNY",
        note="初始资金"
    )
    
    # 3. 批量添加持仓
    positions = [
        {
            "symbol": "600519",
            "market": "cn",
            "currency": "CNY",
            "trade_date": date(2024, 6, 15),
            "side": "buy",
            "quantity": 100,
            "price": 1750.0,
            "fee": 50.0,
        },
        {
            "symbol": "300750",
            "market": "cn",
            "currency": "CNY",
            "trade_date": date(2024, 7, 20),
            "side": "buy",
            "quantity": 200,
            "price": 280.0,
            "fee": 30.0,
        },
        {
            "symbol": "AAPL",
            "market": "us",
            "currency": "USD",
            "trade_date": date(2024, 8, 10),
            "side": "buy",
            "quantity": 50,
            "price": 220.0,
            "fee": 5.0,
        },
    ]
    
    for pos in positions:
        service.record_trade(
            account_id=account_id,
            symbol=pos["symbol"],
            trade_date=pos["trade_date"],
            side=pos["side"],
            quantity=pos["quantity"],
            price=pos["price"],
            fee=pos.get("fee", 0),
            tax=0,
            market=pos["market"],
            currency=pos["currency"],
            note=f"建仓 {pos['symbol']}"
        )
        print(f"✅ 添加持仓: {pos['symbol']} x {pos['quantity']} @ {pos['price']}")
    
    print("\n🎉 持仓导入完成！")
    print(f"账户ID: {account_id}")
    print(f"总持仓数: {len(positions)}")

if __name__ == "__main__":
    import_my_portfolio()
```

运行导入：
```bash
python import_portfolio.py
```

### 方式 C：直接从 CSV 导入

准备 `portfolio.csv` 文件：

```csv
symbol,market,currency,trade_date,side,quantity,price,fee
600519,cn,CNY,2024-06-15,buy,100,1750.0,50.0
300750,cn,CNY,2024-07-20,buy,200,280.0,30.0
AAPL,us,USD,2024-08-10,buy,50,220.0,5.0
```

创建导入脚本 `import_from_csv.py`：

```python
#!/usr/bin/env python3
"""从 CSV 导入持仓"""

import csv
from datetime import date
from src.services.portfolio_service import PortfolioService

def import_from_csv(csv_file="portfolio.csv"):
    service = PortfolioService()
    
    # 创建账户
    account_id = service.create_account(
        account_name="CSV导入账户",
        base_currency="CNY"
    )
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            service.record_trade(
                account_id=account_id,
                symbol=row['symbol'],
                trade_date=date.fromisoformat(row['trade_date']),
                side=row['side'],
                quantity=float(row['quantity']),
                price=float(row['price']),
                fee=float(row.get('fee', 0)),
                tax=0,
                market=row['market'],
                currency=row['currency']
            )
            print(f"✅ {row['symbol']}: {row['quantity']}股 @ {row['price']}")
    
    print(f"\n✅ 从 {csv_file} 导入完成")

if __name__ == "__main__":
    import_from_csv()
```

---

## 第2步：选择或创建策略

### 内置策略列表

系统提供以下内置策略（位于 `strategies/` 目录）：

| 策略名称 | 标识符 | 适用场景 | 核心逻辑 |
|---------|--------|---------|---------|
| 多头趋势 | `bull_trend` | 上升趋势中的股票 | MA5>MA10>MA20 + 低乖离率 |
| 均线金叉 | `ma_golden_cross` | 趋势反转/延续 | MA5上穿MA10/MA20 + 量能确认 |
| 放量突破 | `volume_breakout` | 接近阻力位的股票 | 价格突破 + 成交量>2倍均量 |
| 缩量回踩 | `shrink_pullback` | 回调低吸机会 | 回踩均线 + 量能萎缩 |
| 底部放量 | `bottom_volume` | 超跌反弹信号 | 地量见地价 + 底部放量 |
| 龙头策略 | `dragon_head` | 强势龙头股 | 板块领涨 + 趋势延续 |
| 一阳夹三阴 | `one_yang_three_yin` | 洗盘后反包 | 主力洗盘形态识别 |
| 箱体震荡 | `box_oscillation` | 区间震荡股票 | 高抛低吸策略 |
| 缠论 | `chan_theory` | 技术分析爱好者 | 笔/线段/中枢理论 |
| 波浪理论 | `wave_theory` | 周期分析 | 艾略特波浪计数 |
| 情绪周期 | `emotion_cycle` | 短线交易者 | 市场情绪高低点轮动 |

### 配置单一策略

在 `.env` 文件中：

```bash
# 只使用均线金叉策略
AGENT_MODE=true
AGENT_SKILLS=ma_golden_cross
```

### 组合多个策略

```bash
# 组合使用3个策略
AGENT_MODE=true
AGENT_SKILLS=ma_golden_cross,volume_breakout,shrink_pullback
```

### 启用所有策略

```bash
# 方式1：使用 all 关键字
AGENT_SKILLS=all

# 方式2：显式列出所有策略
AGENT_SKILLS=bull_trend,ma_golden_cross,volume_breakout,shrink_pullback,bottom_volume,dragon_head,one_yang_three_yin,box_oscillation,chan_theory,wave_theory,emotion_cycle
```

### 创建自定义策略

#### 最简模板

创建文件 `strategies/my_strategy.yaml`：

```yaml
name: my_strategy              # 唯一标识（英文，下划线连接）
display_name: 我的策略          # 显示名称（中文）
description: 简短描述策略用途

instructions: |
  你的策略描述...
  用自然语言写出判断标准、入场条件、出场条件等。
  可以引用工具名称（如 get_daily_history、analyze_trend）来指导 AI 使用哪些数据。
```

#### 完整模板

创建文件 `strategies/my_custom_strategy.yaml`：

```yaml
# ============================================
# 自定义持仓策略示例
# ============================================

name: my_portfolio_strategy
display_name: 我的持仓专属策略
description: 针对我当前持仓的个性化交易策略

# 策略分类：trend（趋势）、pattern（形态）、reversal（反转）、framework（框架）
category: trend

# 关联的核心交易理念编号（1-7）
# 1: 严进策略  2: 趋势交易  3: 效率优先
# 4: 买点偏好  5: 风险排查  6: 量价配合  7: 强势股放宽
core_rules: [1, 2, 3]

# 策略需要使用的工具列表
required_tools:
  - get_daily_history      # 获取历史K线
  - analyze_trend          # 技术趋势分析
  - get_realtime_quote     # 实时行情

# 可选别名（用于自然语言选择）
aliases: [我的战法, 持仓策略]

# 元数据配置
default_active: true           # 是否默认激活
default_router: false          # 是否参与路由fallback
default_priority: 50           # 优先级（数值越小越靠前）
market_regimes: [trending_up]  # 适配的市场状态

# ============================================
# 策略详细说明（核心部分）
# ============================================
instructions: |
  **我的持仓专属策略**

  ### 适用场景
  
  本策略专门针对我已持有的股票进行日常监控和操作建议生成。

  ### 判断标准

  #### 1. 持仓超过7天的股票
  
  - 使用 `analyze_trend` 检查当前趋势状态
  - 若出现放量突破信号（`volume_breakout`），上调 sentiment_score +15
  - 若跌破MA20且无量能支撑，建议减仓或止损

  #### 2. 亏损超过10%的持仓
  
  - 检查是否出现 `shrink_pullback` 止跌信号
  - 若有止跌信号：建议持有等待反弹
  - 若无止跌信号：建议减仓50%控制风险
  - 使用 `search_stock_news` 检查是否有重大利空

  #### 3. 盈利超过20%的持仓
  
  - 检查乖离率是否超过8%
  - 若乖离率过大：建议部分止盈（卖出30%-50%）
  - 设置移动止损位：最高价回撤5%即止损
  - 使用 `get_realtime_quote` 监控实时价格

  #### 4. 新买入股票（持仓<3天）
  
  - 严格遵循 `ma_golden_cross` 金叉标准
  - 乖离率必须 < 5%（关联理念1：严进策略）
  - 必须有量能确认（关联理念3：效率优先）

  ### 评分调整规则

  - 满足持仓7天+趋势向好：sentiment_score +10
  - 出现放量突破：sentiment_score +15
  - 亏损>10%且无止跌信号：sentiment_score -20
  - 盈利>20%且乖离率>8%：sentiment_score +5（但建议止盈）
  - 出现重大利空新闻：sentiment_score -30，一票否决

  ### 输出要求

  在生成的报告中必须注明：
  - 在 `buy_reason` 中注明"持仓专属策略评估"
  - 在 `battle_plan.sniper_points` 中给出明确的买卖点位
  - 在 `position_advice.has_position` 中给出持仓者专属建议
  - 在 `risk_warning` 中强调止损位

  ### 风险控制

  - 单只股票最大仓位不超过总资金的30%
  - 总持仓不超过5只股票
  - 任何情况下都要设置明确止损位
  - 止损位一般设在关键支撑位下方2%-3%
```

#### 策略编写要点

1. **使用自然语言**：不需要编程，用清晰的中文描述你的交易逻辑
2. **引用工具**：明确指出应该调用哪些工具获取数据
3. **量化标准**：尽量给出具体的数值阈值（如"乖离率<5%"）
4. **评分规则**：说明什么情况下加分/减分
5. **输出要求**：指定报告应包含哪些内容

### 测试自定义策略

```bash
# 1. 启用你的自定义策略
echo "AGENT_SKILLS=my_portfolio_strategy" >> .env

# 2. 运行分析
python main.py --stocks 600519

# 3. 查看生成的报告是否符合预期
# 检查 reports/ 目录下的最新报告
ls -lt reports/ | head -5
```

---

## 第3步：运行分析

### 手动触发分析

```bash
# 分析所有 STOCK_LIST 中的股票
python main.py

# 分析指定股票
python main.py --stocks 600519,300750

# 仅分析持仓股票（需要先配置持仓）
python main.py --portfolio

# 调试模式（查看详细日志）
python main.py --debug --stocks 600519

# 模拟运行（不发送通知）
python main.py --dry-run --stocks 600519
```

### 定时任务自动分析

在 `.env` 中配置：

```bash
# 启用定时任务
SCHEDULE_ENABLED=true

# 每天执行时间（24小时制）
# 建议在收盘后执行，如 15:30-18:00 之间
SCHEDULE_TIME=16:00

# 启动时立即执行一次（用于测试）
SCHEDULE_RUN_IMMEDIATELY=true

# 启用大盘复盘
MARKET_REVIEW_ENABLED=true
```

启动定时任务：

```bash
python main.py --schedule
```

程序会：
1. 立即执行一次分析（因为 `SCHEDULE_RUN_IMMEDIATELY=true`）
2. 每天 16:00 自动执行分析
3. 将结果推送到配置的通知渠道

### Docker 环境定时任务

```bash
# 使用 docker-compose
docker-compose up -d

# 查看日志
docker-compose logs -f
```

---

## 第4步：查看交易建议

### 通知推送内容

系统会根据你配置的通知渠道推送报告，典型内容如下：

#### 企业微信/飞书消息

```
📊 股票分析报告 - 2024-01-15

━━━━━━━━━━━━━━━━━━━━━━━

📌 贵州茅台 (600519)

🟡持有观望 | 看多 | 置信度: 高

> **一句话总结**: 均线金叉确认，趋势向好但乖离率偏高，建议持有观察

⏰ **时间敏感性**: 本周内

| 持仓状态 | 操作建议 |
|---------|---------|
| 🆕 **空仓者** | 暂不追高，等待回踩MA5至1780附近再考虑 |
| 💼 **持仓者** | 继续持有，止损位1750，目标位1900 |

🎯 狙击点位
━━━━━━━━━━━━━━━
• 理想买点: 1780元 (MA5支撑)
• 次要买点: 1750元 (MA10强支撑)
• 止损价位: 1720元 (跌破MA20)
• 止盈目标: 1900元 (前期高点)

📈 技术面
━━━━━━━━━━━━━━━
• 均线系统: MA5>MA10>MA20 多头排列 ✓
• MACD: 零轴上方金叉 ✓
• 成交量: 量比1.3，温和放量 ✓
• 乖离率: 0.55% (安全区间)

⚠️ 风险提示
━━━━━━━━━━━━━━━
• 若跌破1720坚决止损
• 关注板块整体走势
• 留意是否有减持公告

━━━━━━━━━━━━━━━━━━━━━━━

📊 宁德时代 (300750)
...（类似格式）
```

#### 邮件报告

邮件会包含更详细的 Markdown 格式报告，包括：
- 完整的技术分析图表
- K线形态说明
- 基本面数据
- 新闻资讯摘要
- 历史对比分析

### Web 界面查看

访问 `http://localhost:8000` 查看：

1. **决策仪表盘**
   - 可视化展示买卖点位
   - 趋势预测图表
   - 风险评估雷达图

2. **持仓概览**
   - 总体盈亏统计
   - 持仓分布饼图
   - 风险预警列表

3. **历史报告**
   - 查看往日的分析报告
   - 对比策略效果
   - 导出PDF/Excel

### 查看原始 JSON 数据

API 返回的完整数据结构：

```bash
curl http://localhost:8000/api/v1/analysis/600519
```

```json
{
  "stock_code": "600519",
  "stock_name": "贵州茅台",
  "sentiment_score": 75,
  "trend_prediction": "看多",
  "operation_advice": "持有",
  "decision_type": "hold",
  "confidence_level": "高",
  
  "dashboard": {
    "core_conclusion": {
      "one_sentence": "均线金叉确认，趋势向好但乖离率偏高",
      "signal_type": "🟡持有观望",
      "time_sensitivity": "本周内",
      "position_advice": {
        "no_position": "暂不追高，等待回踩MA5至1780附近再考虑",
        "has_position": "继续持有，止损位1750，目标位1900"
      }
    },
    
    "data_perspective": {
      "trend_status": {
        "ma_alignment": "MA5>MA10>MA20",
        "is_bullish": true,
        "trend_score": 85
      },
      "price_position": {
        "current_price": 1820.0,
        "ma5": 1810.0,
        "ma10": 1795.0,
        "ma20": 1780.0,
        "bias_ma5": 0.55,
        "bias_status": "安全",
        "support_level": 1780.0,
        "resistance_level": 1850.0
      },
      "volume_analysis": {
        "volume_ratio": 1.3,
        "volume_status": "温和放量",
        "turnover_rate": 0.5
      }
    },
    
    "battle_plan": {
      "sniper_points": {
        "ideal_buy": "1780元(MA5支撑位)",
        "secondary_buy": "1750元(MA10强支撑)",
        "stop_loss": "1720元(跌破MA20止损)",
        "take_profit": "1900元(前期高点阻力)"
      },
      "position_strategy": {
        "suggested_position": "现有仓位保持不变",
        "entry_plan": "若回调至1780可加仓10%",
        "risk_control": "跌破1720坚决止损"
      },
      "action_checklist": [
        "监控MA5支撑有效性",
        "关注成交量变化",
        "设置1720止损提醒"
      ]
    }
  },
  
  "analysis_summary": "综合技术分析...",
  "key_points": "均线金叉,量能配合,乖离率安全",
  "risk_warning": "若跌破MA20需警惕趋势反转",
  "buy_reason": "均线金叉策略确认 + 持仓专属策略评估"
}
```

---

## 高级用法

### 1. 为不同持仓设置不同策略

#### 场景：对不同类型的股票使用不同策略

创建多个策略文件：

**策略1：稳健型持仓策略** (`strategies/conservative_strategy.yaml`)

```yaml
name: conservative_strategy
display_name: 稳健型持仓策略
description: 适用于蓝筹股和长期持仓

instructions: |
  **稳健型持仓策略**
  
  适用对象：贵州茅台、中国平安等蓝筹股
  
  核心原则：
  - 以持有为主，减少频繁交易
  - 只在极端情况（偏离MA20超过10%）才考虑调仓
  - 重点关注基本面变化和分红政策
  
  操作建议：
  - 正常波动：坚定持有
  - 大幅下跌（>15%）：检查基本面，若无问题可加仓
  - 大幅上涨（>30%）：可部分止盈锁定利润
```

**策略2：激进型交易策略** (`strategies/aggressive_strategy.yaml`)

```yaml
name: aggressive_strategy
display_name: 激进型交易策略
description: 适用于题材股和短线交易

instructions: |
  **激进型交易策略**
  
  适用对象：题材股、小盘股、短线交易
  
  核心原则：
  - 快进快出，严格止损
  - 重点关注量能和情绪
  - 不设长期目标，见好就收
  
  操作建议：
  - 出现放量突破：立即跟进
  - 跌破5日线：果断止损
  - 获利超过10%：分批止盈
```

#### 根据股票类型动态选择策略

创建智能路由脚本 `smart_strategy_router.py`：

```python
#!/usr/bin/env python3
"""根据股票特征自动选择策略"""

import os
from src.config import get_config

# 定义股票与策略的映射
STRATEGY_MAPPING = {
    # 蓝筹股 -> 稳健策略
    "600519": "conservative_strategy",  # 贵州茅台
    "601318": "conservative_strategy",  # 中国平安
    "000858": "conservative_strategy",  # 五粮液
    
    # 科技股 -> 激进策略
    "300750": "aggressive_strategy",    # 宁德时代
    "002594": "aggressive_strategy",    # 比亚迪
    
    # 默认策略
    "default": "ma_golden_cross"
}

def get_strategy_for_stock(stock_code):
    """根据股票代码返回应使用的策略"""
    return STRATEGY_MAPPING.get(stock_code, STRATEGY_MAPPING["default"])

def update_env_with_strategy(stock_code):
    """更新 .env 文件中的策略配置"""
    strategy = get_strategy_for_stock(stock_code)
    
    # 读取现有 .env
    env_path = ".env"
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 更新 AGENT_SKILLS
    new_lines = []
    for line in lines:
        if line.startswith("AGENT_SKILLS="):
            new_lines.append(f"AGENT_SKILLS={strategy}\n")
        else:
            new_lines.append(line)
    
    # 写回 .env
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"✅ 已为 {stock_code} 设置策略: {strategy}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
        update_env_with_strategy(stock_code)
    else:
        print("用法: python smart_strategy_router.py <股票代码>")
```

使用：
```bash
# 为贵州茅台设置稳健策略
python smart_strategy_router.py 600519

# 为宁德时代设置激进策略
python smart_strategy_router.py 300750

# 然后运行分析
python main.py --stocks 600519
```

### 2. 结合基本面数据增强策略

创建增强策略 `strategies/fundamental_enhanced.yaml`：

```yaml
name: fundamental_enhanced
display_name: 基本面增强策略
description: 结合技术面和基本面的综合策略

required_tools:
  - get_daily_history
  - analyze_trend
  - search_stock_news

instructions: |
  **基本面增强策略**
  
  ### 分析流程
  
  1. **技术面分析**（权重60%）
     - 使用 `analyze_trend` 获取技术指标
     - 检查均线排列、MACD、KDJ等
     - 评分范围：0-60分
  
  2. **基本面分析**（权重40%）
     - 使用 `search_stock_news` 搜索最新财报、业绩预告
     - 检查PE/PB估值是否合理
     - 关注股东减持、监管处罚等负面新闻
     - 评分范围：0-40分
  
  ### 综合评分规则
  
  - 技术面优秀(>50) + 基本面良好(>30) = 强烈买入 (80-100分)
  - 技术面良好(>40) + 基本面一般(>20) = 买入/持有 (60-79分)
  - 技术面一般(>30) + 基本面较差(<20) = 观望 (40-59分)
  - 任一维度很差 = 卖出/回避 (<40分)
  
  ### 特殊规则
  
  - 若出现重大利空（业绩暴雷、立案调查）：直接降至20分以下
  - 若出现重大利好（业绩超预期、重大合同）：额外+10分
  - PE>50且无高增长支撑：-15分
  - 连续3年ROE>15%：+10分
  
  ### 输出要求
  
  在报告中必须包含：
  - 技术面评分和基本面评分
  - 主要风险因素（至少列出3条）
  - 估值合理性判断
  - 明确的买卖建议
```

### 3. 回测策略效果

#### 查看历史回测数据

```bash
# 回测过去30天的均线金叉策略
python -c "
from src.services.backtest_service import BacktestService
service = BacktestService()
result = service.run_backtest(
    strategy_name='ma_golden_cross',
    days=30,
    stock_codes=['600519']
)
print(f'胜率: {result.win_rate:.2%}')
print(f'平均收益: {result.avg_return:.2%}')
print(f'最大回撤: {result.max_drawdown:.2%}')
"
```

#### 对比多个策略

```python
#!/usr/bin/env python3
"""策略对比分析"""

from src.services.backtest_service import BacktestService

def compare_strategies():
    service = BacktestService()
    stock_code = "600519"
    days = 60
    
    strategies = [
        "ma_golden_cross",
        "volume_breakout",
        "shrink_pullback",
        "bull_trend"
    ]
    
    print(f"{'策略':<20} {'胜率':<10} {'平均收益':<10} {'最大回撤':<10} {'交易次数'}")
    print("-" * 70)
    
    for strategy in strategies:
        result = service.run_backtest(
            strategy_name=strategy,
            days=days,
            stock_codes=[stock_code]
        )
        print(f"{strategy:<20} {result.win_rate:>8.2%} {result.avg_return:>9.2%} "
              f"{result.max_drawdown:>9.2%} {result.trade_count:>8}")

if __name__ == "__main__":
    compare_strategies()
```

输出示例：
```
策略                 胜率       平均收益     最大回撤     交易次数
----------------------------------------------------------------------
ma_golden_cross       65.00%     3.20%     -2.10%       12
volume_breakout       58.00%     4.50%     -3.80%       15
shrink_pullback       72.00%     2.80%     -1.50%        8
bull_trend            60.00%     3.50%     -2.50%       10
```

### 4. 设置止损止盈提醒

创建监控脚本 `monitor_positions.py`：

```python
#!/usr/bin/env python3
"""实时监控持仓，触发止损止盈时发送提醒"""

import time
from datetime import datetime
from src.services.portfolio_service import PortfolioService
from src.data_provider import DataFetcherManager
from src.notification import NotificationService

def check_stop_loss_take_profit():
    """检查是否触发止损止盈"""
    portfolio_service = PortfolioService()
    fetcher = DataFetcherManager()
    notifier = NotificationService()
    
    # 获取持仓快照
    snapshot = portfolio_service.get_portfolio_snapshot()
    
    alerts = []
    
    for account in snapshot.get('accounts', []):
        for position in account.get('positions', []):
            symbol = position['symbol']
            current_price = position['last_price']
            avg_cost = position['avg_cost']
            quantity = position['quantity']
            
            # 计算盈亏比例
            pnl_pct = (current_price - avg_cost) / avg_cost * 100
            
            # 获取今日分析结果中的止损止盈位
            # （这里简化处理，实际应从最近的分析报告读取）
            stop_loss = avg_cost * 0.95  # 默认-5%止损
            take_profit = avg_cost * 1.15  # 默认+15%止盈
            
            # 检查止损
            if current_price <= stop_loss:
                alerts.append(f"🔴 止损预警: {symbol} 现价{current_price:.2f} "
                            f"已跌破止损位{stop_loss:.2f}，亏损{pnl_pct:.2f}%")
            
            # 检查止盈
            elif current_price >= take_profit:
                alerts.append(f"🟢 止盈提醒: {symbol} 现价{current_price:.2f} "
                            f"已达到止盈位{take_profit:.2f}，盈利{pnl_pct:.2f}%")
    
    # 发送提醒
    if alerts:
        message = "⚠️ 持仓监控提醒\n\n" + "\n\n".join(alerts)
        notifier.send_text(message)
        print(f"已发送 {len(alerts)} 条提醒")
    else:
        print("✅ 无需提醒")

if __name__ == "__main__":
    # 每5分钟检查一次
    while True:
        try:
            check_stop_loss_take_profit()
        except Exception as e:
            print(f"❌ 检查失败: {e}")
        
        time.sleep(300)  # 5分钟
```

后台运行：
```bash
nohup python monitor_positions.py > monitor.log 2>&1 &
```

### 5. 生成每日交易计划

创建脚本 `generate_daily_plan.py`：

```python
#!/usr/bin/env python3
"""生成每日交易计划"""

import json
from datetime import date
from src.core.pipeline import StockAnalysisPipeline
from src.config import get_config

def generate_trading_plan():
    """生成今日交易计划"""
    config = get_config()
    pipeline = StockAnalysisPipeline(config=config)
    
    # 获取持仓列表
    from src.services.portfolio_service import PortfolioService
    portfolio = PortfolioService()
    snapshot = portfolio.get_portfolio_snapshot()
    
    stock_codes = []
    for account in snapshot.get('accounts', []):
        for position in account.get('positions', []):
            stock_codes.append(position['symbol'])
    
    if not stock_codes:
        print("⚠️ 暂无持仓")
        return
    
    print(f"📅 今日交易计划 - {date.today()}\n")
    print("=" * 60)
    
    for code in stock_codes:
        try:
            # 分析股票
            result = pipeline.analyze_single_stock(code)
            
            if result:
                dashboard = result.dashboard or {}
                core = dashboard.get('core_conclusion', {})
                sniper = dashboard.get('battle_plan', {}).get('sniper_points', {})
                
                print(f"\n📊 {result.stock_name} ({code})")
                print(f"   信号: {core.get('signal_type', 'N/A')}")
                print(f"   建议: {core.get('position_advice', {}).get('has_position', 'N/A')}")
                print(f"   理想买点: {sniper.get('ideal_buy', 'N/A')}")
                print(f"   止损位: {sniper.get('stop_loss', 'N/A')}")
                print(f"   止盈位: {sniper.get('take_profit', 'N/A')}")
                
        except Exception as e:
            print(f"\n❌ {code} 分析失败: {e}")
    
    print("\n" + "=" * 60)
    print("💡 提示: 以上建议仅供参考，请结合实际情况决策")

if __name__ == "__main__":
    generate_trading_plan()
```

每天早上运行：
```bash
python generate_daily_plan.py
```

输出示例：
```
📅 今日交易计划 - 2024-01-15

============================================================

📊 贵州茅台 (600519)
   信号: 🟡持有观望
   建议: 继续持有，止损位1750，目标位1900
   理想买点: 1780元(MA5支撑位)
   止损位: 1720元(跌破MA20止损)
   止盈位: 1900元(前期高点阻力)

📊 宁德时代 (300750)
   信号: 🟢买入信号
   建议: 可逢低加仓，注意控制仓位
   理想买点: 275元(箱体下沿)
   止损位: 265元
   止盈位: 300元

============================================================
💡 提示: 以上建议仅供参考，请结合实际情况决策
```

---

## 常见问题

### Q1: 如何验证策略是否生效？

**A:** 查看分析报告中的 `buy_reason` 字段，应该包含你策略的名称。

```bash
# 查看最新报告的 buy_reason
grep -A 2 "buy_reason" reports/report_$(date +%Y%m%d).md
```

或在 Web 界面的"决策依据"部分查看。

### Q2: 策略建议不准确怎么办？

**A:** 
1. **优化策略描述**：在 YAML 的 `instructions` 中补充更多判断细节
2. **调整评分规则**：修改加分/减分的数值
3. **更换策略**：尝试其他内置策略
4. **组合策略**：使用多个策略互相验证

### Q3: 如何让策略只针对特定股票生效？

**A:** 创建多个策略文件，然后在运行时动态切换：

```bash
# 为股票A使用策略1
AGENT_SKILLS=strategy_for_stock_a python main.py --stocks 600519

# 为股票B使用策略2
AGENT_SKILLS=strategy_for_stock_b python main.py --stocks 300750
```

或使用前面提到的智能路由脚本。

### Q4: 能否同时使用多个策略分析同一只股票？

**A:** 可以！在 `.env` 中配置：

```bash
AGENT_SKILLS=ma_golden_cross,volume_breakout,shrink_pullback
```

AI 会综合考虑所有策略的意见，生成综合判断。

### Q5: 如何查看策略的历史表现？

**A:** 
1. **Web 界面**：访问 `/portfolio` 查看持仓历史和分析记录
2. **API 查询**：
   ```bash
   curl http://localhost:8000/api/v1/backtest/results?strategy=ma_golden_cross
   ```
3. **数据库查询**：
   ```sql
   SELECT * FROM backtest_results 
   WHERE strategy_name = 'ma_golden_cross' 
   ORDER BY analysis_date DESC 
   LIMIT 10;
   ```

### Q6: 定时任务没有执行怎么办？

**A:** 检查以下几点：

1. **确认配置正确**
   ```bash
   grep SCHEDULE .env
   # 应该看到:
   # SCHEDULE_ENABLED=true
   # SCHEDULE_TIME=16:00
   ```

2. **检查进程是否在运行**
   ```bash
   ps aux | grep "main.py --schedule"
   ```

3. **查看日志**
   ```bash
   tail -f logs/stock_analysis_*.log
   ```

4. **手动测试**
   ```bash
   python main.py  # 手动执行一次，确认能正常运行
   ```

### Q7: 通知推送失败怎么办？

**A:** 

1. **检查 Webhook 配置**
   ```bash
   # 测试企业微信
   curl -X POST "YOUR_WEBHOOK_URL" \
     -H "Content-Type: application/json" \
     -d '{"msgtype":"text","text":{"content":"测试"}}'
   ```

2. **检查网络连接**
   ```bash
   ping qyapi.weixin.qq.com  # 企业微信
   ping open.feishu.cn       # 飞书
   ```

3. **查看详细错误日志**
   ```bash
   grep "notification" logs/stock_analysis_*.log | tail -20
   ```

### Q8: 如何备份和恢复持仓数据？

**A:** 

**备份：**
```bash
# 备份整个数据库
cp data/stock_analysis.db data/stock_analysis.db.backup.$(date +%Y%m%d)

# 或导出为 SQL
sqlite3 data/stock_analysis.db ".dump" > backup.sql
```

**恢复：**
```bash
# 从备份恢复
cp data/stock_analysis.db.backup.20240115 data/stock_analysis.db

# 或从 SQL 恢复
sqlite3 data/stock_analysis.db < backup.sql
```

### Q9: 策略文件放在哪里？

**A:** 
- **内置策略**：`strategies/` 目录
- **自定义策略**：可通过 `AGENT_SKILL_DIR` 环境变量指定其他目录

```bash
# 使用自定义策略目录
AGENT_SKILL_DIR=./my_custom_strategies
```

### Q10: 如何贡献自己的策略到社区？

**A:** 
1. 确保策略经过充分测试
2. 编写清晰的策略说明
3. 提交 PR 到 GitHub 仓库的 `strategies/` 目录
4. 在 PR 描述中说明策略的适用场景和回测结果

---

## 📚 相关文档

- [策略文件README](../strategies/README.md) - 策略编写规范
- [LLM配置指南](../docs/LLM_CONFIG_GUIDE.md) - AI模型配置
- [部署指南](../docs/DEPLOY.md) - 服务器部署
- [完整使用手册](../docs/full-guide.md) - 系统全面介绍

---

## 🔄 更新日志

- **2024-01-15**: 初始版本，涵盖持仓策略定制完整流程
- 后续将根据用户反馈持续完善

---

## 💬 获取帮助

如遇到问题：

1. 查看日志文件：`logs/stock_analysis_*.log`
2. 查阅 FAQ：`docs/FAQ.md`
3. 提交 Issue：https://github.com/your-repo/issues
4. 加入社区讨论群

---

**祝投资顺利！** 📈💰
