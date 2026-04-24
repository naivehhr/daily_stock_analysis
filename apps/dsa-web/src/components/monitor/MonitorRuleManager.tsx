import { useState, useEffect, useCallback } from 'react';
import { Plus, Edit2, Trash2, Save, X, AlertCircle } from 'lucide-react';
import { monitorApi } from '../../api/monitor';
import type { MonitorRule, CreateMonitorRuleRequest, UpdateMonitorRuleRequest } from '../../api/monitor';
import { Card, Button, Badge, Input, Checkbox, EmptyState } from '../common';

// 预留接口，未来可能用于规则选择

const INDICATOR_OPTIONS = [
  { value: 'price_breakout', label: '价格突破' },
  { value: 'volume_spike', label: '成交量异常' },
  { value: 'ma_cross', label: '均线交叉' },
  { value: 'rsi_signal', label: 'RSI 信号' },
  { value: 'macd_signal', label: 'MACD 信号' },
];

export default function MonitorRuleManager() {
  const [rules, setRules] = useState<MonitorRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingRule, setEditingRule] = useState<MonitorRule | null>(null);
  const [creatingRule, setCreatingRule] = useState(false);
  const [selectedRuleIds, setSelectedRuleIds] = useState<number[]>([]);

  // 表单状态
  const [formData, setFormData] = useState<{
    stock_code: string;
    indicators: string[];
    is_active: boolean;
  }>({
    stock_code: '',
    indicators: ['price_breakout', 'volume_spike'],
    is_active: true,
  });

  // 加载规则列表
  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const data = await monitorApi.listRules();
      setRules(data);
    } catch (error) {
      console.error('加载监控规则失败:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  // 开始创建规则
  const handleCreate = () => {
    setCreatingRule(true);
    setEditingRule(null);
    setFormData({
      stock_code: '',
      indicators: ['price_breakout', 'volume_spike'],
      is_active: true,
    });
  };

  // 开始编辑规则
  const handleEdit = (rule: MonitorRule) => {
    setEditingRule(rule);
    setCreatingRule(false);
    setFormData({
      stock_code: rule.stock_code,
      indicators: rule.indicators,
      is_active: rule.is_active,
    });
  };

  // 取消编辑/创建
  const handleCancel = () => {
    setEditingRule(null);
    setCreatingRule(false);
    setFormData({
      stock_code: '',
      indicators: ['price_breakout', 'volume_spike'],
      is_active: true,
    });
  };

  // 保存规则
  const handleSave = async () => {
    if (!formData.stock_code.trim()) {
      alert('请输入股票代码');
      return;
    }

    try {
      if (editingRule) {
        // 更新现有规则
        const updateData: UpdateMonitorRuleRequest = {
          indicators: formData.indicators,
          is_active: formData.is_active,
        };
        await monitorApi.updateRule(editingRule.id, updateData);
      } else {
        // 创建新规则
        const createData: CreateMonitorRuleRequest = {
          stock_code: formData.stock_code.trim(),
          indicators: formData.indicators,
          is_active: formData.is_active,
        };
        await monitorApi.createRule(createData);
      }

      // 重新加载列表
      await loadRules();
      handleCancel();
    } catch (error) {
      console.error('保存规则失败:', error);
      alert('保存规则失败，请重试');
    }
  };

  // 删除规则
  const handleDelete = async (ruleId: number) => {
    if (!confirm('确定要删除这条监控规则吗？')) {
      return;
    }

    try {
      await monitorApi.deleteRule(ruleId);
      await loadRules();
    } catch (error) {
      console.error('删除规则失败:', error);
      alert('删除规则失败，请重试');
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedRuleIds.length === 0) {
      return;
    }

    if (!confirm(`确定要删除选中的 ${selectedRuleIds.length} 条规则吗？`)) {
      return;
    }

    try {
      await monitorApi.batchDeleteRules(selectedRuleIds);
      setSelectedRuleIds([]);
      await loadRules();
    } catch (error) {
      console.error('批量删除规则失败:', error);
      alert('批量删除规则失败，请重试');
    }
  };

  // 切换规则选择
  const toggleRuleSelection = (ruleId: number) => {
    setSelectedRuleIds(prev =>
      prev.includes(ruleId)
        ? prev.filter(id => id !== ruleId)
        : [...prev, ruleId]
    );
  };

  // 切换指标选择
  const toggleIndicator = (value: string) => {
    setFormData(prev => ({
      ...prev,
      indicators: prev.indicators.includes(value)
        ? prev.indicators.filter(v => v !== value)
        : [...prev.indicators, value],
    }));
  };

  // 渲染指标徽章
  const renderIndicatorBadges = (indicators: string[]) => {
    const indicatorLabels: Record<string, string> = {
      price_breakout: '价格突破',
      volume_spike: '成交量',
      ma_cross: '均线交叉',
      rsi_signal: 'RSI',
      macd_signal: 'MACD',
    };

    return indicators.map(indicator => (
      <Badge key={indicator} variant="info" size="sm">
        {indicatorLabels[indicator] || indicator}
      </Badge>
    ));
  };

  // 如果正在编辑或创建，显示表单
  if (editingRule || creatingRule) {
    return (
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">
              {editingRule ? '编辑监控规则' : '新建监控规则'}
            </h3>
            <Button variant="ghost" size="sm" onClick={handleCancel}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* 股票代码输入 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              股票代码 <span className="text-red-500">*</span>
            </label>
            <Input
              placeholder="例如：600519"
              value={formData.stock_code}
              onChange={(e) => setFormData(prev => ({ ...prev, stock_code: e.target.value }))}
              disabled={!!editingRule} // 编辑时不允许修改股票代码
              className="h-10"
            />
          </div>

          {/* 监控指标选择 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">监控指标</label>
            <div className="grid grid-cols-2 gap-3">
              {INDICATOR_OPTIONS.map(option => (
                <Checkbox
                  key={option.value}
                  checked={formData.indicators.includes(option.value)}
                  onChange={() => toggleIndicator(option.value)}
                  label={option.label}
                />
              ))}
            </div>
          </div>

          {/* 启用状态 */}
          <div className="space-y-2">
            <Checkbox
              checked={formData.is_active}
              onChange={() => setFormData(prev => ({ ...prev, is_active: !prev.is_active }))}
              label="启用此规则"
            />
          </div>

          {/* 操作按钮 */}
          <div className="flex space-x-2 pt-2">
            <Button onClick={handleSave} size="sm">
              <Save className="mr-2 h-4 w-4" />
              保存
            </Button>
            <Button variant="outline" onClick={handleCancel} size="sm">
              取消
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  // 显示规则列表
  return (
    <Card>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">监控规则管理</h3>
          <div className="flex space-x-2">
            {selectedRuleIds.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleBatchDelete}
                className="text-danger hover:text-danger"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                批量删除 ({selectedRuleIds.length})
              </Button>
            )}
            <Button onClick={handleCreate} size="sm">
              <Plus className="mr-2 h-4 w-4" />
              新建规则
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="py-8 text-center text-muted-foreground">加载中...</div>
        ) : rules.length === 0 ? (
          <EmptyState
            icon={<AlertCircle className="h-12 w-12" />}
            title="暂无监控规则"
            description="点击「新建规则」添加你的第一个监控规则"
          />
        ) : (
          <div className="space-y-3">
            {rules.map(rule => (
              <div
                key={rule.id}
                className={`p-4 rounded-lg border transition-all ${
                  selectedRuleIds.includes(rule.id)
                    ? 'border-primary bg-primary/5'
                    : 'bg-card hover:bg-accent/50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    {/* 复选框 */}
                    <Checkbox
                      checked={selectedRuleIds.includes(rule.id)}
                      onChange={() => toggleRuleSelection(rule.id)}
                      label=""
                    />

                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono font-bold text-lg">
                          {rule.stock_code}
                        </span>
                        <Badge
                          variant={rule.is_active ? 'success' : 'default'}
                          size="sm"
                        >
                          {rule.is_active ? '已启用' : '已禁用'}
                        </Badge>
                      </div>

                      <div className="flex flex-wrap gap-2 mt-2">
                        {renderIndicatorBadges(rule.indicators)}
                      </div>

                      <div className="text-xs text-muted-foreground mt-2">
                        创建于 {new Date(rule.created_at).toLocaleDateString('zh-CN')}
                        {' · '}
                        更新于 {new Date(rule.updated_at).toLocaleDateString('zh-CN')}
                      </div>
                    </div>
                  </div>

                  <div className="flex space-x-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(rule)}
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(rule.id)}
                      className="text-danger hover:text-danger"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
