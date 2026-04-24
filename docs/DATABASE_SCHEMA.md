# 数据库表结构说明

本文档详细说明 `daily_stock_analysis` 项目中使用的 SQLite 数据库表结构及其用途。

**数据库位置**: `data/stock_analysis.db`  
**ORM 框架**: SQLAlchemy  
**数据库引擎**: SQLite (支持 WAL 模式)

---

## 目录

- [1. 核心数据表](#1-核心数据表)
  - [1.1 stock_daily - 股票日线数据](#11-stock_daily---股票日线数据)
  - [1.2 analysis_history - 分析历史记录](#12-analysis_history---分析历史记录)
  - [1.3 news_intel - 新闻情报](#13-news_intel---新闻情报)
  - [1.4 fundamental_snapshot - 基本面快照](#14-fundamental_snapshot---基本面快照)
- [2. 回测相关表](#2-回测相关表)
  - [2.1 backtest_results - 回测结果](#21-backtest_results---回测结果)
  - [2.2 backtest_summaries - 回测汇总](#22-backtest_summaries---回测汇总)
- [3. 投资组合管理表](#3-投资组合管理表)
  - [3.1 portfolio_accounts - 投资账户](#31-portfolio_accounts---投资账户)
  - [3.2 portfolio_trades - 交易记录](#32-portfolio_trades---交易记录)
  - [3.3 portfolio_cash_ledger - 资金流水](#33-portfolio_cash_ledger---资金流水)
  - [3.4 portfolio_corporate_actions - 公司行为](#34-portfolio_corporate_actions---公司行为)
  - [3.5 portfolio_positions - 持仓快照](#35-portfolio_positions---持仓快照)
  - [3.6 portfolio_position_lots - 持仓批次](#36-portfolio_position_lots---持仓批次)
  - [3.7 portfolio_daily_snapshots - 每日账户快照](#37-portfolio_daily_snapshots---每日账户快照)
  - [3.8 portfolio_fx_rates - 汇率缓存](#38-portfolio_fx_rates---汇率缓存)
- [4. 监控相关表](#4-监控相关表)
  - [4.1 monitor_history - 盯盘历史](#41-monitor_history---盯盘历史)
  - [4.2 monitor_rules - 监控规则](#42-monitor_rules---监控规则)
- [5. 对话与使用统计表](#5-对话与使用统计表)
  - [5.1 conversation_messages - 对话消息](#51-conversation_messages---对话消息)
  - [5.2 llm_usage - LLM 使用统计](#52-llm_usage---llm-使用统计)

---

## 1. 核心数据表

### 1.1 stock_daily - 股票日线数据

**用途**: 存储每日股票行情数据和技术指标，是系统的基础数据源。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| code | String(10) | 股票代码（如 600519, 000001），索引 |
| date | Date | 交易日期，索引 |
| open | Float | 开盘价 |
| high | Float | 最高价 |
| low | Float | 最低价 |
| close | Float | 收盘价 |
| volume | Float | 成交量（股） |
| amount | Float | 成交额（元） |
| pct_chg | Float | 涨跌幅（%） |
| ma5 | Float | 5日均线 |
| ma10 | Float | 10日均线 |
| ma20 | Float | 20日均线 |
| volume_ratio | Float | 量比 |
| data_source | String(50) | 数据来源（如 AkshareFetcher） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

**约束**:
- 唯一约束: `(code, date)` - 同一股票同一天只能有一条记录
- 索引: `ix_code_date` - 加速按股票和日期查询

---

### 1.2 analysis_history - 分析历史记录

**用途**: 保存每次 AI 分析的结果，包括情绪评分、操作建议、趋势预测等核心结论，以及狙击点位等详细数据。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| query_id | String(64) | 关联查询链路 ID，索引 |
| code | String(10) | 股票代码，索引 |
| name | String(50) | 股票名称 |
| report_type | String(16) | 报告类型，索引 |
| sentiment_score | Integer | 情绪评分 |
| operation_advice | String(20) | 操作建议 |
| trend_prediction | String(50) | 趋势预测 |
| analysis_summary | Text | 分析摘要 |
| raw_result | Text | 原始分析结果 |
| news_content | Text | 相关新闻内容 |
| context_snapshot | Text | 上下文快照 |
| ideal_buy | Float | 理想买入价 |
| secondary_buy | Float | 次要买入价 |
| stop_loss | Float | 止损价 |
| take_profit | Float | 止盈价 |
| position_advice | String(16) | 仓位建议 (empty/light/half/heavy/full) |
| support_levels | Text | 支撑位 (JSON 数组) |
| resistance_levels | Text | 压力位 (JSON 数组) |
| breakout_analysis | Text | 突破分析结果 (JSON) |
| created_at | DateTime | 创建时间，索引 |

**索引**:
- `ix_analysis_code_time` - 加速按股票和时间查询

---

### 1.3 news_intel - 新闻情报

**用途**: 存储搜索到的新闻情报条目，用于后续分析与查询，支持多维度检索。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| query_id | String(64) | 关联用户查询操作，索引 |
| code | String(10) | 股票代码，索引 |
| name | String(50) | 股票名称 |
| dimension | String(32) | 搜索维度 (latest_news/risk_check/earnings/market_analysis/industry)，索引 |
| query | String(255) | 搜索关键词 |
| provider | String(32) | 搜索引擎提供商，索引 |
| title | String(300) | 新闻标题 |
| snippet | Text | 新闻摘要 |
| url | String(1000) | 新闻链接 |
| source | String(100) | 新闻来源 |
| published_date | DateTime | 发布日期，索引 |
| fetched_at | DateTime | 抓取时间，索引 |
| query_source | String(32) | 查询来源 (bot/web/cli/system)，索引 |
| requester_platform | String(20) | 请求者平台 |
| requester_user_id | String(64) | 请求者用户 ID |
| requester_user_name | String(64) | 请求者用户名 |
| requester_chat_id | String(64) | 请求者聊天 ID |
| requester_message_id | String(64) | 请求者消息 ID |
| requester_query | String(255) | 请求者查询内容 |

**约束**:
- 唯一约束: `uix_news_url` - URL 去重
- 索引: `ix_news_code_pub` - 加速按股票和发布时间查询

---

### 1.4 fundamental_snapshot - 基本面快照

**用途**: 存储基本面上下文快照（P0 write-only），仅用于写入，主链路不依赖读取该表，便于后续回测/画像扩展。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| query_id | String(64) | 查询 ID，索引 |
| code | String(10) | 股票代码，索引 |
| payload | Text | 基本面数据负载 (JSON) |
| source_chain | Text | 数据来源链 |
| coverage | Text | 覆盖范围 |
| created_at | DateTime | 创建时间，索引 |

**索引**:
- `ix_fundamental_snapshot_query_code` - 加速按查询 ID 和股票查询
- `ix_fundamental_snapshot_created` - 加速按创建时间查询

---

## 2. 回测相关表

### 2.1 backtest_results - 回测结果

**用途**: 存储单条分析记录的回测结果，评估历史分析的准确性。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| analysis_history_id | Integer | 关联分析历史 ID，外键，索引 |
| code | String(10) | 股票代码，索引 |
| analysis_date | Date | 分析日期，索引 |
| eval_window_days | Integer | 评估窗口天数，默认 10 |
| engine_version | String(16) | 回测引擎版本，默认 'v1' |
| eval_status | String(16) | 评估状态 (pending/completed/failed)，默认 'pending' |
| evaluated_at | DateTime | 评估时间，索引 |
| operation_advice | String(20) | 操作建议快照 |
| position_recommendation | String(8) | 仓位建议 (long/cash) |
| start_price | Float | 起始价格 |
| end_close | Float | 结束收盘价 |
| max_high | Float | 期间最高价 |
| min_low | Float | 期间最低价 |
| stock_return_pct | Float | 股票收益率 (%) |
| direction_expected | String(16) | 预期方向 (up/down/flat/not_down) |
| direction_correct | Boolean | 方向是否正确 |
| outcome | String(16) | 结果 (win/loss/neutral) |
| stop_loss | Float | 止损价 |
| take_profit | Float | 止盈价 |
| hit_stop_loss | Boolean | 是否触及止损 |
| hit_take_profit | Boolean | 是否触及止盈 |
| first_hit | String(16) | 首次触发 (take_profit/stop_loss/ambiguous/neither/not_applicable) |
| first_hit_date | Date | 首次触发日期 |
| first_hit_trading_days | Integer | 首次触发的交易日数 |
| simulated_entry_price | Float | 模拟入场价 |
| simulated_exit_price | Float | 模拟出场价 |
| simulated_exit_reason | String(24) | 模拟出场原因 |
| simulated_return_pct | Float | 模拟收益率 (%) |

**约束**:
- 唯一约束: `uix_backtest_analysis_window_version` - `(analysis_history_id, eval_window_days, engine_version)`
- 索引: `ix_backtest_code_date` - 加速按股票和日期查询

---

### 2.2 backtest_summaries - 回测汇总

**用途**: 存储回测汇总指标，按股票或全局维度统计回测表现。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| scope | String(16) | 范围 (overall/stock)，索引 |
| code | String(16) | 股票代码，索引 |
| eval_window_days | Integer | 评估窗口天数，默认 10 |
| engine_version | String(16) | 回测引擎版本，默认 'v1' |
| computed_at | DateTime | 计算时间，索引 |
| total_evaluations | Integer | 总评估次数 |
| completed_count | Integer | 完成次数 |
| insufficient_count | Integer | 数据不足次数 |
| long_count | Integer | 做多次数 |
| cash_count | Integer | 空仓次数 |
| win_count | Integer | 盈利次数 |
| loss_count | Integer | 亏损次数 |
| neutral_count | Integer | 中性次数 |
| direction_accuracy_pct | Float | 方向准确率 (%) |
| win_rate_pct | Float | 胜率 (%) |
| neutral_rate_pct | Float | 中性率 (%) |
| avg_stock_return_pct | Float | 平均股票收益率 (%) |
| avg_simulated_return_pct | Float | 平均模拟收益率 (%) |
| stop_loss_trigger_rate | Float | 止损触发率 |
| take_profit_trigger_rate | Float | 止盈触发率 |
| ambiguous_rate | Float | 模糊率 |
| avg_days_to_first_hit | Float | 平均首次触发天数 |
| advice_breakdown_json | Text | 建议分解 (JSON) |
| diagnostics_json | Text | 诊断信息 (JSON) |

**约束**:
- 唯一约束: `uix_backtest_summary_scope_code_window_version` - `(scope, code, eval_window_days, engine_version)`

---

## 3. 投资组合管理表

### 3.1 portfolio_accounts - 投资账户

**用途**: 存储投资组合账户元数据，支持多账户管理。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| owner_id | String(64) | 所有者 ID，索引 |
| name | String(64) | 账户名称 |
| broker | String(64) | 券商名称 |
| market | String(8) | 市场 (cn/hk/us)，默认 'cn'，索引 |
| base_currency | String(8) | 基础货币，默认 'CNY' |
| is_active | Boolean | 是否激活，默认 true，索引 |
| created_at | DateTime | 创建时间，索引 |
| updated_at | DateTime | 更新时间 |

**索引**:
- `ix_portfolio_account_owner_active` - 加速按所有者和激活状态查询

---

### 3.2 portfolio_trades - 交易记录

**用途**: 存储已执行的交易事件，作为回放的事实来源。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| account_id | Integer | 账户 ID，外键，索引 |
| trade_uid | String(128) | 交易唯一 ID |
| symbol | String(16) | 股票代码，索引 |
| market | String(8) | 市场，默认 'cn' |
| currency | String(8) | 货币，默认 'CNY' |
| trade_date | Date | 交易日期，索引 |
| side | String(8) | 交易方向 (buy/sell) |
| quantity | Float | 数量 |
| price | Float | 价格 |
| fee | Float | 手续费，默认 0.0 |
| tax | Float | 税费，默认 0.0 |
| note | String(255) | 备注 |
| dedup_hash | String(64) | 去重哈希，索引 |
| created_at | DateTime | 创建时间，索引 |

**约束**:
- 唯一约束: `uix_portfolio_trade_uid` - `(account_id, trade_uid)`
- 唯一约束: `uix_portfolio_trade_dedup_hash` - `(account_id, dedup_hash)`
- 索引: `ix_portfolio_trade_account_date` - 加速按账户和日期查询

---

### 3.3 portfolio_cash_ledger - 资金流水

**用途**: 记录资金进出事件。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| account_id | Integer | 账户 ID，外键，索引 |
| event_date | Date | 事件日期，索引 |
| direction | String(8) | 方向 (in/out) |
| amount | Float | 金额 |
| currency | String(8) | 货币，默认 'CNY' |
| note | String(255) | 备注 |
| created_at | DateTime | 创建时间，索引 |

**索引**:
- `ix_portfolio_cash_account_date` - 加速按账户和日期查询

---

### 3.4 portfolio_corporate_actions - 公司行为

**用途**: 记录影响现金或持股数量的公司行为（如分红、拆股）。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| account_id | Integer | 账户 ID，外键，索引 |
| symbol | String(16) | 股票代码，索引 |
| market | String(8) | 市场，默认 'cn' |
| currency | String(8) | 货币，默认 'CNY' |
| effective_date | Date | 生效日期，索引 |
| action_type | String(24) | 行为类型 (cash_dividend/split_adjustment) |
| cash_dividend_per_share | Float | 每股现金分红 |
| split_ratio | Float | 拆股比例 |
| note | String(255) | 备注 |
| created_at | DateTime | 创建时间，索引 |

**索引**:
- `ix_portfolio_ca_account_date` - 加速按账户和日期查询

---

### 3.5 portfolio_positions - 持仓快照

**用途**: 存储每个账户中每只股票的最新回放持仓快照。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| account_id | Integer | 账户 ID，外键，索引 |
| cost_method | String(8) | 成本计算方法 (fifo/avg)，默认 'fifo' |
| symbol | String(16) | 股票代码，索引 |
| market | String(8) | 市场，默认 'cn' |
| currency | String(8) | 货币，默认 'CNY' |
| quantity | Float | 持仓数量，默认 0.0 |
| avg_cost | Float | 平均成本，默认 0.0 |
| total_cost | Float | 总成本，默认 0.0 |
| last_price | Float | 最新价格，默认 0.0 |
| market_value_base | Float | 市值（基础货币），默认 0.0 |
| unrealized_pnl_base | Float | 未实现盈亏（基础货币），默认 0.0 |
| valuation_currency | String(8) | 估值货币，默认 'CNY' |
| updated_at | DateTime | 更新时间，索引 |

**约束**:
- 唯一约束: `uix_portfolio_position_account_symbol_market_currency` - `(account_id, symbol, market, currency, cost_method)`

---

### 3.6 portfolio_position_lots - 持仓批次

**用途**: 存储 FIFO 回放使用的批次级别剩余数量。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| account_id | Integer | 账户 ID，外键，索引 |
| cost_method | String(8) | 成本计算方法 (fifo/avg)，默认 'fifo' |
| symbol | String(16) | 股票代码，索引 |
| market | String(8) | 市场，默认 'cn' |
| currency | String(8) | 货币，默认 'CNY' |
| open_date | Date | 开仓日期，索引 |
| remaining_quantity | Float | 剩余数量，默认 0.0 |
| unit_cost | Float | 单位成本，默认 0.0 |
| source_trade_id | Integer | 来源交易 ID，外键 |
| updated_at | DateTime | 更新时间，索引 |

**索引**:
- `ix_portfolio_lot_account_symbol` - 加速按账户和股票查询

---

### 3.7 portfolio_daily_snapshots - 每日账户快照

**用途**: 存储通过实时回放生成的每日账户快照。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| account_id | Integer | 账户 ID，外键，索引 |
| snapshot_date | Date | 快照日期，索引 |
| cost_method | String(8) | 成本计算方法 (fifo/avg)，默认 'fifo' |
| base_currency | String(8) | 基础货币，默认 'CNY' |
| total_cash | Float | 总现金，默认 0.0 |
| total_market_value | Float | 总市值，默认 0.0 |
| total_equity | Float | 总权益，默认 0.0 |
| unrealized_pnl | Float | 未实现盈亏，默认 0.0 |
| realized_pnl | Float | 已实现盈亏，默认 0.0 |
| fee_total | Float | 总手续费，默认 0.0 |
| tax_total | Float | 总税费，默认 0.0 |
| fx_stale | Boolean | 汇率是否过时，默认 false |
| payload | Text | 完整快照数据 (JSON) |
| created_at | DateTime | 创建时间，索引 |
| updated_at | DateTime | 更新时间 |

**约束**:
- 唯一约束: `uix_portfolio_snapshot_account_date_method` - `(account_id, snapshot_date, cost_method)`

---

### 3.8 portfolio_fx_rates - 汇率缓存

**用途**: 缓存跨货币投资组合转换使用的汇率。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| from_currency | String(8) | 源货币，索引 |
| to_currency | String(8) | 目标货币，索引 |
| rate_date | Date | 汇率日期，索引 |
| rate | Float | 汇率 |
| source | String(32) | 来源，默认 'manual' |
| is_stale | Boolean | 是否过时，默认 false |
| updated_at | DateTime | 更新时间 |

**约束**:
- 唯一约束: `uix_portfolio_fx_pair_date` - `(from_currency, to_currency, rate_date)`

---

## 4. 监控相关表

### 4.1 monitor_history - 盯盘历史

**用途**: 存储每次监控触发的分析结果，支持回溯查询和信号追踪。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| stock_code | String(16) | 股票代码，索引 |
| triggered_at | DateTime | 触发时间，索引 |
| signal_types | Text | 信号类型 (JSON 数组) |
| summary | Text | 摘要 |
| report_json | Text | 完整的 MonitorResult JSON |
| notified | Boolean | 是否已通知，默认 false |
| created_at | DateTime | 创建时间 |

**索引**:
- `idx_monitor_stock_time` - 加速按股票和时间查询

---

### 4.2 monitor_rules - 监控规则

**用途**: 存储用户配置的监控规则，支持定时自动监控（预留功能）。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| user_id | String(64) | 用户 ID，索引（多用户支持预留） |
| stock_code | String(16) | 股票代码 |
| indicators | Text | 监控指标 (JSON 数组) |
| custom_rules | Text | 自定义规则 (JSON 对象) |
| is_active | Boolean | 是否激活，默认 true |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

**约束**:
- 唯一约束: `uq_user_stock_rule` - `(user_id, stock_code)` - 每个用户对每只股票只能有一个规则

---

## 5. 对话与使用统计表

### 5.1 conversation_messages - 对话消息

**用途**: 存储 Agent 对话历史记录，支持多会话管理。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| session_id | String(100) | 会话 ID，索引 |
| role | String(20) | 角色 (user/assistant/system) |
| content | Text | 消息内容 |
| created_at | DateTime | 创建时间，索引 |

---

### 5.2 llm_usage - LLM 使用统计

**用途**: 记录每次 LLM 调用的 token 使用情况，用于审计和成本分析。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键，自增 |
| call_type | String(32) | 调用类型 (analysis/agent/market_review)，索引 |
| model | String(128) | 模型名称 |
| stock_code | String(16) | 股票代码（可选） |
| prompt_tokens | Integer | 提示词 token 数，默认 0 |
| completion_tokens | Integer | 完成 token 数，默认 0 |
| total_tokens | Integer | 总 token 数，默认 0 |
| called_at | DateTime | 调用时间，索引 |

---

## 数据库设计特点

### 1. 索引优化
- 所有表都对常用查询字段建立了索引
- 复合索引用于加速多条件查询（如 `ix_code_date`, `ix_analysis_code_time`）
- 唯一约束防止数据重复

### 2. 外键关系
- 投资组合相关表通过 `account_id` 外键关联到 `portfolio_accounts`
- 回测结果通过 `analysis_history_id` 外键关联到 `analysis_history`
- 持仓批次通过 `source_trade_id` 外键关联到 `portfolio_trades`

### 3. JSON 字段
- 复杂数据结构使用 Text 类型存储 JSON 字符串
- 包括：支撑位/压力位、突破分析、基本面数据、诊断信息等

### 4. 时间戳
- 所有表都有 `created_at` 字段记录创建时间
- 部分表有 `updated_at` 字段记录更新时间
- 支持按时间范围查询和历史回溯

### 5. 多租户支持
- 部分表预留了 `user_id` 或 `owner_id` 字段
- 为未来多用户场景做准备

### 6. 数据完整性
- 使用唯一约束防止重复数据
- 使用外键保证引用完整性
- 使用 NOT NULL 约束保证关键字段不为空

---

## 数据库迁移

项目使用 SQLAlchemy 的自动建表功能，并在 `DatabaseManager` 中实现了手动迁移逻辑：

```python
# 示例：添加新列
session.execute(text("ALTER TABLE analysis_history ADD COLUMN position_advice VARCHAR(16)"))
```

迁移策略：
1. 检查现有表结构
2. 对比期望的列定义
3. 动态添加缺失的列
4. 迁移失败不影响系统运行，仅记录错误日志

---

**最后更新**: 2026-04-17  
**维护者**: daily_stock_analysis 团队
