# 盯盘监控模块 - 端到端测试计划

## 测试环境准备

### 1. 前置条件检查

```bash
# 1. 确认 Python 环境
python3 --version  # 应 >= 3.10

# 2. 安装依赖
pip install -r requirements.txt

# 3. 确认数据库初始化
python3 -c "from src.storage import get_db; db = get_db(); print('数据库连接成功')"

# 4. 检查通知渠道配置（至少配置一个）
# 在 .env 中确认已配置：
# - WECHAT_WEBHOOK_URL 或
# - FEISHU_WEBHOOK_URL 或
# - TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID 等

# 5. 确认 LLM 配置
# 在 .env 中确认已配置至少一个 LLM API Key
```

### 2. 启动服务

```bash
# 方式1：开发模式
python3 main.py --serve

# 方式2：使用 uvicorn
uvicorn server:app --reload --host 0.0.0.0 --port 8000

# 确认服务启动成功
curl http://localhost:8000/api/v1/monitor/health
# 预期响应: {"status":"healthy","module":"monitor"}
```

---

## 测试用例清单

### TC-01: API 健康检查

**目的**: 验证监控模块 API 是否正常注册

**步骤**:
```bash
curl http://localhost:8000/api/v1/monitor/health
```

**预期结果**:
```json
{
  "status": "healthy",
  "module": "monitor"
}
```

**通过标准**: 返回 200 状态码和上述 JSON

---

### TC-02: 单只股票基础监控（无持仓）

**目的**: 验证最基本的监控流程

**步骤**:
```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519"],
    "indicators": ["price_breakout", "volume_spike"]
  }'
```

**预期结果**:
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
      "llm_summary": "...",
      "portfolio": null
    }
  ]
}
```

**验证点**:
- ✅ `status` 为 "completed"
- ✅ `results` 数组包含 1 个元素
- ✅ `stock_code` 和 `stock_name` 正确
- ✅ `current_price` > 0
- ✅ `signals` 是数组（可以为空）
- ✅ 收到通知推送（检查钉钉/飞书/Telegram）

**通过标准**: API 返回成功且收到通知

---

### TC-03: 多只股票并发监控

**目的**: 验证并发处理能力

**步骤**:
```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519", "300750", "002594", "AAPL", "TSLA"],
    "indicators": ["price_breakout", "volume_spike", "rsi_signal"]
  }'
```

**预期结果**:
- 返回 5 只股票的监控结果
- 每只股票的结果结构完整
- 总耗时 < 60 秒（取决于 LLM 响应速度）

**验证点**:
- ✅ `results.length === 5`
- ✅ 每只股票都有 `stock_code`, `stock_name`, `current_price`
- ✅ 所有股票都收到了通知

**通过标准**: 所有股票分析完成且无错误

---

### TC-04: 包含持仓分析的监控

**目的**: 验证持仓集成功能

**前置条件**: 
- 已在系统中创建持仓账户并录入交易

**步骤**:
```bash
# 1. 先查询账户ID
curl http://localhost:8000/api/v1/portfolio/accounts

# 2. 执行带持仓的监控
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519"],
    "indicators": ["price_breakout", "volume_spike"],
    "with_portfolio": true,
    "account_id": 1
  }'
```

**预期结果**:
```json
{
  "results": [
    {
      "stock_code": "600519",
      "portfolio": {
        "has_position": true,
        "quantity": 100,
        "avg_cost": 1750.00,
        "current_price": 1850.00,
        "unrealized_pnl": 10000.00,
        "pnl_pct": 5.71
      },
      "llm_advice": "部分止盈"
    }
  ]
}
```

**验证点**:
- ✅ `portfolio.has_position === true`
- ✅ `portfolio.quantity > 0`
- ✅ `portfolio.avg_cost > 0`
- ✅ LLM 建议考虑了持仓成本

**通过标准**: 返回持仓信息且 AI 分析提及持仓情况

---

### TC-05: 指定不同监控指标组合

**目的**: 验证各指标检测逻辑

**测试子用例**:

#### 5.1 仅价格突破
```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519"],
    "indicators": ["price_breakout"]
  }'
```

#### 5.2 仅成交量异常
```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519"],
    "indicators": ["volume_spike"]
  }'
```

#### 5.3 RSI 信号
```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519"],
    "indicators": ["rsi_signal"]
  }'
```

#### 5.4 MACD 信号
```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519"],
    "indicators": ["macd_signal"]
  }'
```

#### 5.5 均线交叉
```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519"],
    "indicators": ["ma_cross"]
  }'
```

**验证点**:
- ✅ 每个请求都成功返回
- ✅ 信号类型与请求的指标匹配
- ✅ 技术指标值在合理范围内（RSI: 0-100, MA: > 0）

**通过标准**: 所有指标组合都能正常执行

---

### TC-06: 查询监控历史

**目的**: 验证历史记录持久化

**步骤**:
```bash
# 1. 先执行一次监控（TC-02）

# 2. 查询历史
curl "http://localhost:8000/api/v1/monitor/history?days=7&limit=10"

# 3. 查询特定股票历史
curl "http://localhost:8000/api/v1/monitor/history?stock_code=600519&days=7"
```

**预期结果**:
```json
[
  {
    "id": 1,
    "stock_code": "600519",
    "triggered_at": "2026-04-16T14:30:00",
    "signal_types": ["price_breakout"],
    "summary": "价格向上突破...",
    "notified": true
  }
]
```

**验证点**:
- ✅ 返回数组非空（如果之前执行过监控）
- ✅ 每条记录包含必要字段
- ✅ `triggered_at` 是有效的时间戳
- ✅ `signal_types` 是数组

**通过标准**: 能正确查询到历史记录

---

### TC-07: Bot 命令触发监控

**目的**: 验证机器人命令集成

**前置条件**: 
- 已配置钉钉或飞书机器人
- 机器人已启动并连接到系统

**步骤**:
1. 在钉钉/飞书中发送消息：
   ```
   /monitor 600519
   ```

2. 等待回复

**预期结果**:
- 立即收到确认消息："📊 已开始监控 1 只股票..."
- 稍后收到监控结果通知
- 通知内容包含股票信息、信号、AI 分析

**验证点**:
- ✅ 确认消息及时返回
- ✅ 监控结果包含技术指标
- ✅ 如果有信号，明确标注信号类型
- ✅ AI 分析简洁专业

**通过标准**: 通过 Bot 成功触发监控并收到完整结果

---

### TC-08: Bot 命令带参数监控

**目的**: 验证 Bot 命令参数解析

**步骤**:
在钉钉/飞书中发送：
```
/monitor 600519,AAPL --indicators price,volume,rsi --with-portfolio
```

**预期结果**:
- 解析出 2 只股票代码
- 使用指定的 3 个指标
- 包含持仓分析

**验证点**:
- ✅ 通知中包含 2 只股票的结果
- ✅ 检测的信号类型符合预期
- ✅ 如果有持仓，显示持仓信息

**通过标准**: 参数正确解析且执行成功

---

### TC-09: Web UI 监控页面

**目的**: 验证 Web 前端功能

**步骤**:
1. 浏览器访问 `http://localhost:8000/`
2. 点击左侧导航"监控"
3. 输入股票代码：`600519,AAPL`
4. 勾选监控指标（至少选 2 个）
5. 可选：勾选"包含持仓分析"
6. 点击"开始监控"按钮

**预期结果**:
- 显示加载状态
- 分析完成后显示结果卡片
- 每张卡片包含：
  - 股票名称和代码
  - 当前价格和涨跌幅
  - 检测到的信号列表
  - AI 分析摘要和建议
  - 持仓信息（如果启用）
- 点击"查看历史"能看到历史记录

**验证点**:
- ✅ 页面正常加载无报错
- ✅ 表单验证工作正常（空代码提示错误）
- ✅ 结果显示格式正确
- ✅ 历史记录面板能打开和关闭
- ✅ 响应式设计（移动端也能正常使用）

**通过标准**: Web UI 所有交互正常

---

### TC-10: 错误处理 - 无效股票代码

**目的**: 验证错误输入处理

**步骤**:
```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["INVALID"],
    "indicators": ["price_breakout"]
  }'
```

**预期结果**:
```json
{
  "status": "failed",
  "error": "无法获取 INVALID 的实时行情"
}
```

**验证点**:
- ✅ 返回明确的错误信息
- ✅ 不崩溃，服务继续运行
- ✅ 日志中有详细错误记录

**通过标准**: 优雅处理错误输入

---

### TC-11: 错误处理 - 无持仓时请求持仓分析

**目的**: 验证无持仓场景

**步骤**:
```bash
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519"],
    "with_portfolio": true,
    "account_id": 999
  }'
```

**预期结果**:
- 不因账户不存在而崩溃
- 返回监控结果，`portfolio` 为 `null`
- 日志中记录警告信息

**验证点**:
- ✅ 服务不崩溃
- ✅ 返回部分成功的结果
- ✅ 有明确的日志记录

**通过标准**: 降级处理，不影响主流程

---

### TC-12: 性能测试 - 大量股票并发

**目的**: 验证系统性能和超时控制

**步骤**:
```bash
# 监控 20 只股票
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519", "300750", "002594", "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "BABA", "JD", "PDD", "NIO", "XPEV", "LI", "hk00700", "hk09988", "hk01810", "hk09618"],
    "indicators": ["price_breakout", "volume_spike"]
  }' \
  --max-time 120
```

**预期结果**:
- 在 120 秒内完成（或超时返回）
- 至少部分股票返回结果
- 系统不崩溃

**验证点**:
- ✅ 总耗时 < 120 秒
- ✅ 成功率 > 80%
- ✅ 内存占用稳定（无明显泄漏）

**通过标准**: 在可接受时间内完成大批量监控

---

### TC-13: 通知渠道测试

**目的**: 验证多渠道通知

**前置条件**: 
- 配置了多个通知渠道（如钉钉 + 飞书 + Telegram）

**步骤**:
1. 执行一次监控
2. 检查所有配置的通知渠道

**预期结果**:
- 所有配置的渠道都收到通知
- 通知内容格式正确
- Markdown 渲染正常

**验证点**:
- ✅ 钉钉收到通知
- ✅ 飞书收到通知
- ✅ Telegram 收到通知（如果配置）
- ✅ 邮件收到通知（如果配置）
- ✅ 单个渠道失败不影响其他渠道

**通过标准**: 所有可用渠道都成功推送

---

### TC-14: 数据库持久化验证

**目的**: 验证数据正确保存到数据库

**步骤**:
```bash
# 1. 执行监控
curl -X POST http://localhost:8000/api/v1/monitor/analyze \
  -H "Content-Type: application/json" \
  -d '{"stock_codes": ["600519"]}'

# 2. 直接查询数据库
python3 << 'EOF'
from src.storage import get_db
db = get_db()
records = db.get_monitor_history(stock_code="600519", limit=5, days=1)
print(f"找到 {len(records)} 条记录")
for r in records:
    print(f"ID: {r.id}, 时间: {r.triggered_at}, 信号: {r.signal_types}")
EOF
```

**预期结果**:
- 数据库中至少有 1 条新记录
- `signal_types` 是有效的 JSON 数组
- `report_json` 包含完整的 MonitorResult

**验证点**:
- ✅ 记录数增加
- ✅ 字段值正确
- ✅ 时间戳准确

**通过标准**: 数据正确持久化且可查询

---

### TC-15: 自然语言 Bot 路由

**目的**: 验证 NLU 意图识别

**步骤**:
在钉钉/飞书中发送自然语言消息：
```
帮我监控一下贵州茅台
盯盘 600519
看看 600519 的信号
```

**预期结果**:
- 系统识别为监控意图
- 自动执行监控并返回结果

**验证点**:
- ✅ 自然语言被正确理解
- ✅ 股票代码被正确提取
- ✅ 执行监控并返回结果

**通过标准**: 自然语言能触发监控功能

---

## 回归测试清单

每次代码修改后，至少执行以下核心测试：

- [ ] TC-01: API 健康检查
- [ ] TC-02: 单只股票基础监控
- [ ] TC-06: 查询监控历史
- [ ] TC-09: Web UI 监控页面
- [ ] TC-10: 错误处理

---

## 自动化测试脚本

### 快速冒烟测试

创建 `tests/test_monitor_smoke.py`:

```python
"""
盯盘监控模块 - 冒烟测试
"""
import requests
import pytest

BASE_URL = "http://localhost:8000"

def test_health_check():
    """健康检查"""
    resp = requests.get(f"{BASE_URL}/api/v1/monitor/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_single_stock_monitor():
    """单只股票监控"""
    resp = requests.post(
        f"{BASE_URL}/api/v1/monitor/analyze",
        json={"stock_codes": ["600519"]}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert len(data["results"]) > 0
    assert data["results"][0]["stock_code"] == "600519"

def test_invalid_stock_code():
    """无效股票代码"""
    resp = requests.post(
        f"{BASE_URL}/api/v1/monitor/analyze",
        json={"stock_codes": ["INVALID"]}
    )
    assert resp.status_code == 200  # API 返回 200，但 status 为 failed
    data = resp.json()
    assert data["status"] == "failed" or len(data.get("results", [])) == 0

def test_history_query():
    """查询历史"""
    resp = requests.get(f"{BASE_URL}/api/v1/monitor/history?days=7&limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

运行：
```bash
python3 -m pytest tests/test_monitor_smoke.py -v
```

---

## 问题排查指南

### 问题1: API 返回 404

**可能原因**: 路由未注册

**解决方案**:
```bash
# 检查 router.py 是否包含 monitor
grep -n "monitor" api/v1/router.py

# 重启服务
python3 main.py --serve
```

### 问题2: 收不到通知

**可能原因**: 通知渠道未配置或 Webhook URL 错误

**解决方案**:
```bash
# 检查 .env 配置
grep -E "WEBHOOK|TELEGRAM|EMAIL" .env

# 查看日志
tail -f logs/app.log | grep -i "notification"
```

### 问题3: LLM 分析失败

**可能原因**: API Key 无效或网络问题

**解决方案**:
```bash
# 检查 LLM 配置
grep -E "LLM_|GEMINI_|DEEPSEEK_" .env

# 测试 LLM 连接
python3 -c "from src.analyzer import GeminiAnalyzer; a = GeminiAnalyzer(); print(a.generate_text('test', max_tokens=10))"
```

### 问题4: Web UI 页面空白

**可能原因**: 前端资源未构建

**解决方案**:
```bash
cd apps/dsa-web
npm run build
# 或使用开发服务器
npm run dev
```

### 问题5: 数据库表不存在

**可能原因**: 数据库未迁移

**解决方案**:
```python
python3 << 'EOF'
from src.storage import get_db, Base, MonitorHistory, MonitorRules
db = get_db()
# 手动创建表
Base.metadata.create_all(db._engine)
print("表创建成功")
EOF
```

---

## 测试报告模板

执行完所有测试后，填写以下报告：

```markdown
## 盯盘监控模块测试报告

**测试日期**: 2026-04-16
**测试人员**: [姓名]
**测试环境**: [本地/Docker/服务器]

### 测试结果汇总

| 测试用例 | 状态 | 备注 |
|---------|------|------|
| TC-01   | ✅/❌ |      |
| TC-02   | ✅/❌ |      |
| ...     | ...  |      |

**通过率**: X/Y (Z%)

### 发现的问题

1. [问题描述]
   - 严重程度: [高/中/低]
   - 复现步骤: [...]
   - 建议修复: [...]

### 性能指标

- 单只股票平均耗时: XX 秒
- 10 只股票并发耗时: XX 秒
- 内存占用: XX MB

### 结论

[通过/不通过] - [简要说明]
```

---

## 持续集成建议

将以下测试加入 CI 流程：

```yaml
# .github/workflows/monitor-test.yml
name: Monitor Module Tests

on:
  push:
    paths:
      - 'src/monitor/**'
      - 'api/v1/endpoints/monitor.py'
      - 'bot/commands/monitor.py'

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt pytest requests
      
      - name: Start service
        run: python main.py --serve &
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      
      - name: Wait for service
        run: sleep 10
      
      - name: Run smoke tests
        run: pytest tests/test_monitor_smoke.py -v
      
      - name: Check AI assets
        run: python scripts/check_ai_assets.py
```

---

## 总结

本测试计划覆盖了盯盘监控模块的所有核心功能，包括：

- ✅ API 接口测试
- ✅ Bot 命令测试
- ✅ Web UI 测试
- ✅ 错误处理测试
- ✅ 性能测试
- ✅ 集成测试

建议在每次发布前至少执行**回归测试清单**中的所有用例，确保功能稳定性。
