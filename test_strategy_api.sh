#!/bin/bash
# 测试盯盘策略创建 API

echo "=========================================="
echo "测试：创建盯盘策略"
echo "=========================================="

# 测试数据
TEST_DATA='{
  "name": "测试涨跌策略",
  "strategy_type": "custom",
  "config": {
    "name": "测试涨跌策略",
    "description": "测试策略 - 600519",
    "buy_conditions": [
      {"type": "drop_percent", "value": 5.0}
    ],
    "sell_conditions": [
      {"type": "rise_percent", "value": 10.0}
    ],
    "watch_conditions": [],
    "position_on_buy": "half",
    "position_on_sell": "empty",
    "stop_loss_percent": 8.0,
    "take_profit_percent": 15.0,
    "symbols": ["600519"],
    "priority": 100,
    "is_active": true
  },
  "symbols": ["600519"],
  "priority": 100
}'

echo ""
echo "📋 发送请求..."
echo "$TEST_DATA" | python3 -m json.tool

echo ""
echo "🚀 调用 API..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/trading-strategies/" \
  -H "Content-Type: application/json" \
  -d "$TEST_DATA")

echo ""
echo "📊 响应结果:"
echo "$RESPONSE" | python3 -m json.tool

# 检查是否成功
if echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('\n✅ 测试通过!' if 'id' in data and 'config_json' in data else '\n❌ 测试失败!')" 2>/dev/null; then
  exit 0
else
  echo ""
  echo "❌ 响应解析失败或API未返回预期字段"
  exit 1
fi
