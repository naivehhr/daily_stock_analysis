# 盯盘监控模块使用指南

## 概述

盯盘监控模块提供实时监控股票技术指标和交易信号的功能，支持：

- **多指标监控**：价格突破、成交量异常、均线交叉、RSI、MACD 等
- **持仓集成分析**：结合持仓成本和盈亏情况给出专业建议
- **AI 智能分析**：基于 Agent 架构的多轮推理，生成交易建议
- **多渠道通知**：自动推送到钉钉、飞书、Telegram 等所有配置的渠道
- **历史记录查询**：保存每次监控结果，支持回溯分析

## 快速开始

### 1. 通过 Web API 触发

```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519", "AAPL"],
    "indicators": ["price_breakout", "volume_spike"],
    "with_portfolio": true,
    "account_id": 1
  }'
```

**响应示例：**
```json
{
  "status": "completed",
  "results": [
    {
      "stock_code": "600519",
      "stock_name": "贵州茅台",
      "current_price": 1850.00,
      "change_pct": -2.3,
      "signals": [...],
      "llm_summary": "短期回调压力较大...",
      "portfolio": {...}
    }
  ]
}
```

### 2. 通过 Bot 命令触发

在钉钉/飞书机器人中发送：

```
/monitor 600519
/monitor 600519,AAPL --indicators price,volume,rsi
/monitor 600519 --with-portfolio --account-id 1
```

**命令参数说明：**
- `<股票代码>`：必填，支持多只股票用逗号分隔
- `--indicators`：可选，指定监控指标（默认：price,volume）
  - 可用值：`price`, `volume`, `ma`, `rsi`, `macd`
- `--with-portfolio`：可选，包含持仓分析
- `--account-id`：可选，指定持仓账户 ID

### 3. 查询监控历史

```bash
# 查询最近 7 天的所有监控记录
curl http://localhost:8000/api/v1/monitor/history?days=7&limit=20

# 查询特定股票的监控历史
curl http://localhost:8000/api/v1/monitor/history?stock_code=600519&days=30
```

## 监控指标说明

### 价格突破 (price_breakout)
- **检测逻辑**：当前价格相对于 MA20 的偏离度超过阈值（默认 3%）
- **向上突破**：生成买入信号
- **向下突破**：生成卖出信号

### 成交量异常 (volume_spike)
- **检测逻辑**：当前成交量相对于 5 日均量的倍数超过阈值（默认 2 倍）
- **放量上涨**：生成买入信号
- **放量下跌**：生成卖出信号

### 均线交叉 (ma_cross)
- **金叉**：MA5 > MA10 且 MA5 > MA20，生成买入信号
- **死叉**：MA5 < MA10 且 MA5 < MA20，生成卖出信号

### RSI 信号 (rsi_signal)
- **超买**：RSI > 70（可配置），生成卖出信号
- **超卖**：RSI < 30（可配置），生成买入信号

### MACD 信号 (macd_signal)
- **金叉**：DIF 上穿 DEA 且 DIF > 0，生成买入信号
- **死叉**：DIF 下穿 DEA 且 DIF < 0，生成卖出信号

## 配置项说明

在 `.env` 文件中配置（从 `.env.example` 复制）：

```bash
# 价格突破阈值（百分比）
MONITOR_PRICE_BREAKOUT_THRESHOLD=3.0

# 成交量异常倍数
MONITOR_VOLUME_SPIKE_RATIO=2.0

# RSI 超买/超卖阈值
MONITOR_RSI_OVERBOUGHT=70
MONITOR_RSI_OVERSOLD=30

# 单次监控最大股票数量
MONITOR_MAX_STOCKS_PER_REQUEST=50

# 监控历史保留天数（0=永久）
MONITOR_HISTORY_RETENTION_DAYS=90
```

## 通知内容示例

### 有信号时
```
🔴 盯盘信号 | 贵州茅台 (600519)

**卖出信号 detected**
- 价格向下跌破20日均线 3.5%（当前:1850.00, MA20:1915.00）
- RSI 超买 (72.5)，警惕回调风险

- 当前价：¥1,850.00 (-2.3%)

**技术指标:**
MA5: 1870.00, MA20: 1915.00, RSI: 72.5

**💼 持仓情况**
- 持仓：100股 | 成本：¥1,750
- 浮盈：+¥10,000 (+5.7%)

**🤖 AI 分析**
核心结论：短期回调压力较大，建议部分止盈锁定利润。
- 建议：**减仓**
- 置信度：高

⏰ 2026-04-16 14:30
```

### 无信号时
```
📊 盯盘报告 | 贵州茅台 (600519)

✅ 无明显交易信号
- 当前价：¥1,880.00 (+0.5%)

**技术指标:**
MA5: 1875.00, MA20: 1870.00, RSI: 55.0 (中性)

**💼 持仓情况**
- 持仓：100股 | 成本：¥1,750
- 浮盈：+¥13,000 (+7.4%)

- 建议：继续观望

⏰ 2026-04-16 14:30
```

## 高级用法

### 自定义监控指标组合

```bash
# 仅监控价格和成交量
/monitor 600519 --indicators price,volume

# 监控所有技术指标
/monitor 600519 --indicators price,volume,ma,rsi,macd
```

### 批量监控自选股

```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519", "300750", "002594", "AAPL", "TSLA"],
    "indicators": ["price_breakout", "volume_spike", "rsi_signal"]
  }'
```

### 结合持仓分析

确保已配置持仓账户，然后：

```bash
/monitor 600519 --with-portfolio --account-id 1
```

系统会自动获取该账户的持仓信息，并在分析时考虑：
- 持仓成本
- 未实现盈亏
- 仓位占比
- 风险集中度

## 故障排查

### 问题：收不到通知

**检查清单：**
1. 确认已配置至少一个通知渠道（钉钉/飞书/Telegram 等）
2. 检查 `.env` 中的 Webhook URL 是否正确
3. 查看日志是否有通知发送失败的错误

### 问题：监控结果为空

**可能原因：**
1. 股票代码格式不正确（A 股 6 位数字，港股 HK+5 位数字，美股字母）
2. 数据源暂时不可用，稍后重试
3. 检查日志中的具体错误信息

### 问题：LLM 分析失败

**可能原因：**
1. LLM API Key 未配置或已过期
2. 网络连接问题
3. 系统会自动降级到 fallback 模式，仍会返回基础分析

## 未来规划

- [ ] 定时任务支持：盘中每小时自动扫描
- [ ] 复杂规则引擎：支持组合条件（如"价格突破 AND 成交量放大"）
- [ ] 回测框架：验证监控策略的历史表现
- [ ] Web UI 面板：可视化监控历史和信号统计
- [ ] 多用户支持：不同用户独立配置监控规则

## 相关文档

- [API 文档](http://localhost:8000/docs) - Swagger UI
- [持仓管理指南](PORTFOLIO_STRATEGY_GUIDE.md)
- [完整使用指南](full-guide.md)
