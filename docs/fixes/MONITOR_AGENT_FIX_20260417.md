# MonitorAgent 错误修复记录

**日期**: 2026-04-17  
**问题来源**: 
- `logs/stock_analysis_20260417.log` 第 1621-1682 行（第一轮修复）
- `logs/stock_analysis_20260417.log` 第 2619-2629 行（第二轮修复）

---

## 问题描述

### 错误 1: AgentOpinion 构造函数参数不匹配

**错误信息**:
```
TypeError: __init__() got an unexpected keyword argument 'summary'
```

**位置**: 
- `src/agent/agents/monitor_agent.py:200`
- `src/agent/agents/monitor_agent.py:212`

**原因**: 
代码使用了错误的参数名 `summary` 和 `details`，但 `AgentOpinion` 数据类的实际字段是：
- `signal` (str) - 信号/结论
- `confidence` (float) - 置信度
- `reasoning` (str) - 推理过程
- `raw_data` (dict) - 原始数据
- `key_levels` (dict) - 关键价位
- `agent_name` (str) - Agent 名称
- `timestamp` (float) - 时间戳

### 错误 2: await 非协程对象

**错误信息**:
```
TypeError: object StageResult can't be used in 'await' expression
```

**位置**: 
- `src/monitor/core.py:370`

**原因**: 
`agent.run(ctx)` 方法返回的是 `StageResult` 对象，不是协程（coroutine），不能使用 `await`。

### 错误 3: 访问不存在的属性

**位置**: 
- `src/monitor/core.py:374`

**原因**: 
代码尝试访问 `result.opinion.details`，但 `AgentOpinion` 没有 `details` 属性，应该是 `raw_data`。

### 错误 4: MonitorSignal 字段名错误

**错误信息**:
```
AttributeError: 'MonitorSignal' object has no attribute 'type'
```

**位置**: 
- `src/monitor/core.py:351`

**原因**: 
代码尝试访问 `s.type.value`，但 `MonitorSignal` 的字段是：
- `indicator` (IndicatorType) - 指标类型
- `signal_type` (SignalType) - 信号类型

而不是单一的 `type` 字段。

---

## 修复方案

### 修复 1: monitor_agent.py

**文件**: `src/agent/agents/monitor_agent.py`

**修改前**:
```python
opinion = AgentOpinion(
    agent_name=self.agent_name,
    summary=data.get("core_conclusion", ""),
    details=data,
    confidence=self._parse_confidence(data.get("confidence", "中")),
)
```

**修改后**:
```python
opinion = AgentOpinion(
    agent_name=self.agent_name,
    signal=data.get("core_conclusion", ""),
    confidence=self._parse_confidence(data.get("confidence", "中")),
    reasoning=data.get("action_plan", ""),
    raw_data=data,
)
```

**异常处理部分也做了相应修改**:
```python
return AgentOpinion(
    agent_name=self.agent_name,
    signal="分析完成（JSON 解析失败）",
    confidence=0.5,
    reasoning="查看原始输出",
    raw_data={"raw_text": raw_text},
)
```

### 修复 2: monitor/core.py - 移除 await

**文件**: `src/monitor/core.py`

**修改前**:
```python
# 运行 Agent
result = await agent.run(ctx)
```

**修改后**:
```python
# 运行 Agent
result = agent.run(ctx)
```

### 修复 3: monitor/core.py - 修正属性访问

**文件**: `src/monitor/core.py`

**修改前**:
```python
if result and result.opinion:
    return result.opinion.details or {}
```

**修改后**:
```python
if result and result.opinion:
    return result.opinion.raw_data or {}
```

### 修复 4: monitor/core.py - 修正 MonitorSignal 字段访问

**文件**: `src/monitor/core.py`

**修改前**:
```python
signal_lines = "\n".join([f"  - {s.type.value}: {s.description}" for s in signals]) if signals else "  无"
```

**修改后**:
```python
signal_lines = "\n".join([f"  - {s.indicator.value}/{s.signal_type.value}: {s.description}" for s in signals]) if signals else "  无"
```

---

## 验证结果

### 测试 1: AgentOpinion 创建
```bash
✅ AgentOpinion 创建成功
  agent_name: monitor
  signal: 看涨
  confidence: 0.8
  reasoning: 技术面突破
  raw_data: {'test': 'data'}
```

### 测试 2: MonitorAgent post_process
```bash
✅ MonitorAgent post_process 成功
  agent_name: monitor
  signal: 短期震荡，关注支撑位
  confidence: 0.7
  reasoning: 建议在支撑位附近轻仓试多
  raw_data keys: ['core_conclusion', 'action_plan', 'confidence']
```

### 测试 3: MonitorSignal 字段访问
```bash
✅ 信号格式化成功
信号数量: 2
格式化输出:
  - ma_cross/buy: MA5上穿MA10
  - rsi_signal/sell: RSI超买
```

---

## 影响范围

### 受影响的模块
1. **MonitorAgent** (`src/agent/agents/monitor_agent.py`)
   - 盯盘智能体分析功能
   - JSON 解析和后处理逻辑

2. **MonitorCore** (`src/monitor/core.py`)
   - 盯盘监控核心逻辑
   - LLM 分析调用流程

### 不受影响的模块
- 其他 Agent（TechnicalAgent, RiskAgent, IntelAgent 等）都正确使用了 `AgentOpinion` 的字段
- 数据库层、API 层、前端均不受影响

---

## 相关日志

**错误发生时的日志片段**:

**第一轮错误** (AgentOpinion 参数问题):
```
2026-04-17 00:21:58 | ERROR | src/agent/agents/monitor_agent.py:210 | 解析 MonitorAgent 输出失败: __init__() got an unexpected keyword argument 'summary'
2026-04-17 00:21:58 | ERROR | src/agent/agents/base_agent.py:144 | [monitor] execution failed: __init__() got an unexpected keyword argument 'summary'
2026-04-17 00:21:58 | ERROR | src/monitor/core.py:389 | LLM 分析异常: object StageResult can't be used in 'await' expression
```

**第二轮错误** (MonitorSignal 字段问题):
```
2026-04-17 00:46:29 | ERROR | src/monitor/core.py:257 | [601138] LLM 分析失败: 'MonitorSignal' object has no attribute 'type'
Traceback (most recent call last):
  File "/Users/menghu/Desktop/project/daily_stock_analysis/src/monitor/core.py", line 351, in _call_llm_analysis
    signal_lines = "\n".join([f"  - {s.type.value}: {s.description}" for s in signals]) if signals else "  无"
AttributeError: 'MonitorSignal' object has no attribute 'type'
```

**修复后预期行为**:
- MonitorAgent 能够正确解析 LLM 返回的 JSON
- 生成正确的 AgentOpinion 对象
- 盯盘监控流程正常执行
- 不再出现 TypeError 异常

---

## 后续建议

1. **统一 Agent 输出格式**: 确保所有 Agent 的 `post_process` 方法都正确使用 `AgentOpinion` 字段
2. **添加类型检查**: 在 CI 流程中添加更严格的类型检查，避免此类错误
3. **完善单元测试**: 为 MonitorAgent 和 MonitorCore 添加完整的单元测试，覆盖正常和异常场景
4. **文档更新**: 在开发者文档中明确 `AgentOpinion` 和 `MonitorSignal` 的使用规范
5. **代码审查**: 加强对 Pydantic 模型字段访问的代码审查，避免使用错误的属性名

---

**修复状态**: ✅ 已完成  
**测试状态**: ✅ 已验证  
**部署状态**: ⏳ 待部署
