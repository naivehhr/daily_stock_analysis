import { useState, useCallback } from 'react';
import { Play, History, AlertCircle, Activity, Clock, Check, Settings, Eye, Trash2, RefreshCw, X } from 'lucide-react';
import { monitorApi } from '../api/monitor';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import { ApiErrorAlert, Card, Badge, Button, EmptyState, Input, Checkbox } from '../components/common';
import MonitorRuleManager from '../components/monitor/MonitorRuleManager';

const MONITOR_INPUT_CLASS =
  'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60';

interface MonitorResult {
  stock_code: string;
  stock_name: string;
  current_price: number;
  change_pct: number;
  
  // 技术指标
  ma5?: number;
  ma10?: number;
  ma20?: number;
  volume_ratio?: number;
  rsi?: number;
  macd_dif?: number;
  macd_dea?: number;
  
  // 量能分析指标
  price_angle?: number;
  momentum_strength?: number;
  volume_power?: number;
  
  // 势能分析指标
  momentum_3d?: number;
  momentum_5d?: number;
  acceleration?: number;
  
  signals: Array<{
    indicator: string;
    signal_type: string;
    description: string;
  }>;
  llm_summary?: string;
  llm_advice?: string;
  portfolio?: {
    has_position: boolean;
    quantity: number;
    avg_cost: number;
    unrealized_pnl: number;
    pnl_pct: number;
  };
  timestamp: string;
}

interface HistoryRecord {
  id: number;
  stock_code: string;
  triggered_at: string;
  signal_types: string[];
  summary: string;
  notified: boolean;
}

interface HistoryDetail extends HistoryRecord {
  report_data?: any;
}

export default function MonitorPage() {
  // 表单状态
  const [stockCodes, setStockCodes] = useState('');
  const [selectedIndicators, setSelectedIndicators] = useState<string[]>(['price_breakout', 'volume_spike']);
  const [withPortfolio, setWithPortfolio] = useState(false);
  const [accountId, setAccountId] = useState<number | ''>('');

  // 结果状态
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [results, setResults] = useState<MonitorResult[]>([]);
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showRuleManager, setShowRuleManager] = useState(false);

  // 历史记录操作状态
  const [selectedDetail, setSelectedDetail] = useState<HistoryDetail | null>(null);
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set());
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // 指标选项
  const indicatorOptions = [
    { value: 'price_breakout', label: '价格突破' },
    { value: 'volume_spike', label: '成交量异常' },
    { value: 'ma_cross', label: '均线交叉' },
    { value: 'rsi_signal', label: 'RSI 信号' },
    { value: 'macd_signal', label: 'MACD 信号' },
    { value: 'momentum', label: '势能分析' },
    { value: 'volume_momentum', label: '量能分析' },
  ];

  // 执行监控
  const handleRunMonitor = useCallback(async () => {
    if (!stockCodes.trim()) {
      setError({
        title: '验证错误',
        message: '请输入股票代码',
        rawMessage: '请输入股票代码',
        status: 400,
        category: 'missing_params',
      });
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const codes = stockCodes.split(',').map(c => c.trim()).filter(Boolean);

      const response = await monitorApi.analyze({
        stock_codes: codes,
        indicators: selectedIndicators,
        with_portfolio: withPortfolio,
        account_id: accountId || undefined,
      });

      if (response.results) {
        setResults(response.results);
      } else if (response.error) {
        setError({
          title: '监控失败',
          message: response.error,
          rawMessage: response.error,
          status: 500,
          category: 'http_error',
        });
      }
    } catch (err) {
      const parsedError = getParsedApiError(err as unknown as Error);
      setError(parsedError);
    } finally {
      setLoading(false);
    }
  }, [stockCodes, selectedIndicators, withPortfolio, accountId]);

  // 加载历史记录
  const loadHistory = useCallback(async () => {
    try {
      const records = await monitorApi.getHistory({ days: 7, limit: 50 });
      setHistory(records);
      setShowHistory(true);
      setSelectedIds(new Set()); // 重置选择
    } catch (err) {
      console.error('加载历史记录失败:', err);
      setError(getParsedApiError(err as unknown as Error));
    }
  }, []);

  // 查看详情
  const handleViewDetail = useCallback(async (recordId: number) => {
    try {
      setLoading(true);
      const detail = await monitorApi.getHistoryDetail(recordId);
      setSelectedDetail(detail);
    } catch (err) {
      console.error('加载详情失败:', err);
      setError(getParsedApiError(err as unknown as Error));
    } finally {
      setLoading(false);
    }
  }, []);

  // 删除单条记录
  const handleDeleteRecord = useCallback(async (recordId: number) => {
    if (!confirm('确定要删除这条监控记录吗？此操作不可恢复。')) {
      return;
    }

    try {
      setDeletingIds(prev => new Set(prev).add(recordId));
      await monitorApi.deleteHistory(recordId);
      
      // 从列表中移除
      setHistory(prev => prev.filter(r => r.id !== recordId));
      setSelectedIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(recordId);
        return newSet;
      });
      
      // 如果正在查看该记录的详情，关闭详情
      if (selectedDetail?.id === recordId) {
        setSelectedDetail(null);
      }
    } catch (err) {
      console.error('删除记录失败:', err);
      setError(getParsedApiError(err as unknown as Error));
    } finally {
      setDeletingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(recordId);
        return newSet;
      });
    }
  }, [selectedDetail]);

  // 批量删除
  const handleBatchDelete = useCallback(async () => {
    if (selectedIds.size === 0) {
      return;
    }

    if (!confirm(`确定要删除选中的 ${selectedIds.size} 条记录吗？此操作不可恢复。`)) {
      return;
    }

    try {
      setLoading(true);
      const result = await monitorApi.batchDeleteHistory(Array.from(selectedIds));
      
      // 从列表中移除已删除的记录
      setHistory(prev => prev.filter(r => !selectedIds.has(r.id)));
      setSelectedIds(new Set());
      
      // 显示成功消息
      alert(result.message);
    } catch (err) {
      console.error('批量删除失败:', err);
      setError(getParsedApiError(err as unknown as Error));
    } finally {
      setLoading(false);
    }
  }, [selectedIds]);

  // 重新分析
  const handleReanalyze = useCallback((stockCode: string) => {
    setStockCodes(stockCode);
    setShowHistory(false);
    // 滚动到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // 切换选择
  const toggleSelect = (recordId: number) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(recordId)) {
        newSet.delete(recordId);
      } else {
        newSet.add(recordId);
      }
      return newSet;
    });
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedIds.size === history.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(history.map(r => r.id)));
    }
  };

  // 切换指标选择
  const toggleIndicator = (value: string) => {
    setSelectedIndicators(prev =>
      prev.includes(value)
        ? prev.filter(v => v !== value)
        : [...prev, value]
    );
  };

  // 渲染信号徽章
  const renderSignalBadge = (signalType: string) => {
    switch (signalType) {
      case 'buy':
        return <Badge variant="success" glow>买入</Badge>;
      case 'sell':
        return <Badge variant="danger" glow>卖出</Badge>;
      case 'hold':
        return <Badge variant="warning">持有</Badge>;
      default:
        return <Badge variant="default">观望</Badge>;
    }
  };

  // 渲染涨跌幅
  const renderChangeBadge = (changePct: number) => {
    const isPositive = changePct >= 0;
    return (
      <Badge variant={isPositive ? 'success' : 'danger'}>
        {isPositive ? '+' : ''}{changePct.toFixed(2)}%
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">盯盘监控</h1>
          <p className="mt-2 text-muted-foreground">
            实时监控股票技术指标，AI 分析交易信号并推送通知
          </p>
        </div>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            onClick={() => setShowRuleManager(!showRuleManager)}
            disabled={loading}
          >
            <Settings className="mr-2 h-4 w-4" />
            {showRuleManager ? '隐藏规则' : '规则管理'}
          </Button>
          <Button
            variant="outline"
            onClick={loadHistory}
            disabled={loading}
          >
            <History className="mr-2 h-4 w-4" />
            查看历史
          </Button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <ApiErrorAlert error={error} onDismiss={() => setError(null)} />
      )}

      {/* 监控规则管理面板 */}
      {showRuleManager && (
        <MonitorRuleManager />
      )}

      {/* 配置面板 */}
      <Card>
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold mb-4">监控配置</h3>

            {/* 股票代码输入 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                股票代码 <span className="text-red-500">*</span>
              </label>
              <Input
                placeholder="例如：600519,AAPL,hk00700（支持多只，逗号分隔）"
                value={stockCodes}
                onChange={(e) => setStockCodes(e.target.value)}
                className={MONITOR_INPUT_CLASS}
                disabled={loading}
              />
            </div>

            {/* 监控指标选择 */}
            <div className="space-y-2 mt-4">
              <label className="text-sm font-medium">监控指标</label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {indicatorOptions.map(option => (
                  <Checkbox
                    key={option.value}
                    checked={selectedIndicators.includes(option.value)}
                    onChange={() => toggleIndicator(option.value)}
                    label={option.label}
                    disabled={loading}
                  />
                ))}
              </div>
            </div>

            {/* 持仓集成选项 */}
            <div className="space-y-2 mt-4">
              <Checkbox
                checked={withPortfolio}
                onChange={() => setWithPortfolio(!withPortfolio)}
                label="包含持仓分析"
                disabled={loading}
              />
              {withPortfolio && (
                <div className="ml-6 mt-2 space-y-2">
                  <label className="text-sm font-medium">账户 ID</label>
                  <Input
                    type="number"
                    placeholder="留空使用默认账户"
                    value={accountId}
                    onChange={(e) => setAccountId(e.target.value ? parseInt(e.target.value) : '')}
                    className={MONITOR_INPUT_CLASS}
                    disabled={loading}
                  />
                </div>
              )}
            </div>

            {/* 执行按钮 */}
            <div className="pt-4">
              <Button
                onClick={handleRunMonitor}
                disabled={loading || !stockCodes.trim()}
                size="lg"
                className="w-full md:w-auto"
              >
                {loading ? (
                  <>
                    <Activity className="mr-2 h-4 w-4 animate-spin" />
                    分析中...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    开始监控
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* 历史记录面板 */}
      {showHistory && (
        <Card>
          <div className="space-y-4">
            {/* 头部 */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <h3 className="text-lg font-semibold">最近监控记录</h3>
                {history.length > 0 && (
                  <Badge variant="default">{history.length} 条</Badge>
                )}
              </div>
              <div className="flex items-center space-x-2">
                {selectedIds.size > 0 && (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={handleBatchDelete}
                    disabled={loading}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    删除选中 ({selectedIds.size})
                  </Button>
                )}
                <Button variant="ghost" size="sm" onClick={() => setShowHistory(false)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {history.length === 0 ? (
              <EmptyState
                icon={<History className="h-12 w-12" />}
                title="暂无监控记录"
                description="执行监控分析后，历史记录将显示在这里"
              />
            ) : (
              <>
                {/* 全选按钮 */}
                <div className="flex items-center justify-between px-2">
                  <label className="flex items-center space-x-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === history.length && history.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded border-gray-300"
                    />
                    <span>全选</span>
                  </label>
                </div>

                {/* 历史记录列表 */}
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {history.map(record => (
                    <div
                      key={record.id}
                      className={`p-3 rounded-lg border transition-colors ${
                        selectedIds.has(record.id)
                          ? 'bg-primary/5 border-primary/30'
                          : 'bg-card hover:bg-accent/50'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-2 flex-1">
                          <input
                            type="checkbox"
                            checked={selectedIds.has(record.id)}
                            onChange={() => toggleSelect(record.id)}
                            className="mt-1 rounded border-gray-300"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2">
                              <span className="font-mono font-medium">{record.stock_code}</span>
                              {record.signal_types.length > 0 && (
                                <Badge variant="warning" size="sm">
                                  {record.signal_types.length} 个信号
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center text-xs text-muted-foreground mt-1">
                              <Clock className="mr-1 h-3 w-3" />
                              {new Date(record.triggered_at).toLocaleString('zh-CN')}
                            </div>
                            {record.summary && (
                              <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                                {record.summary}
                              </p>
                            )}
                          </div>
                        </div>
                        
                        {/* 操作按钮 */}
                        <div className="flex items-center space-x-1 ml-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewDetail(record.id)}
                            title="查看详情"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleReanalyze(record.stock_code)}
                            title="重新分析"
                          >
                            <RefreshCw className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteRecord(record.id)}
                            disabled={deletingIds.has(record.id)}
                            title="删除"
                            className="text-destructive hover:text-destructive"
                          >
                            {deletingIds.has(record.id) ? (
                              <Activity className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </Card>
      )}

      {/* 详情弹窗 */}
      {selectedDetail && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-background rounded-xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden">
            {/* 弹窗头部 */}
            <div className="flex items-center justify-between p-4 border-b">
              <div>
                <h3 className="text-lg font-semibold">监控详情</h3>
                <p className="text-sm text-muted-foreground">
                  {selectedDetail.stock_code} - {new Date(selectedDetail.triggered_at).toLocaleString('zh-CN')}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedDetail(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* 弹窗内容 */}
            <div className="p-4 overflow-y-auto max-h-[calc(80vh-120px)]">
              <div className="space-y-4">
                {/* 信号类型 */}
                <div>
                  <h4 className="text-sm font-medium mb-2">信号类型</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedDetail.signal_types.map((type, idx) => (
                      <Badge key={idx} variant="warning">{type}</Badge>
                    ))}
                  </div>
                </div>

                {/* 摘要 */}
                {selectedDetail.summary && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">分析摘要</h4>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                      {selectedDetail.summary}
                    </p>
                  </div>
                )}

                {/* 详细报告数据 */}
                {selectedDetail.report_data && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">完整报告</h4>
                    <pre className="text-xs bg-muted p-4 rounded-lg overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(selectedDetail.report_data, null, 2)}
                    </pre>
                  </div>
                )}

                {/* 元信息 */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">通知状态:</span>{' '}
                    <Badge variant={selectedDetail.notified ? 'success' : 'default'}>
                      {selectedDetail.notified ? '已通知' : '未通知'}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-muted-foreground">创建时间:</span>{' '}
                    {new Date((selectedDetail as any).created_at).toLocaleString('zh-CN')}
                  </div>
                </div>
              </div>
            </div>

            {/* 弹窗底部 */}
            <div className="p-4 border-t flex justify-end space-x-2">
              <Button
                variant="outline"
                onClick={() => handleReanalyze(selectedDetail.stock_code)}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                重新分析
              </Button>
              <Button
                variant="danger"
                onClick={() => {
                  handleDeleteRecord(selectedDetail.id);
                  setSelectedDetail(null);
                }}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                删除
              </Button>
              <Button onClick={() => setSelectedDetail(null)}>
                关闭
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 监控结果 */}
      {results.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">监控结果</h3>
          {results.map((result, index) => (
            <Card key={index}>
              <div className="space-y-4">
                {/* 股票头部信息 */}
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <h4 className="text-xl font-bold">{result.stock_name}</h4>
                      <span className="font-mono text-muted-foreground">
                        ({result.stock_code})
                      </span>
                    </div>
                    <div className="flex items-center space-x-3 mt-2">
                      <span className="text-2xl font-bold">
                        ¥{result.current_price.toFixed(2)}
                      </span>
                      {renderChangeBadge(result.change_pct)}
                    </div>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    {new Date(result.timestamp).toLocaleString('zh-CN')}
                  </div>
                </div>

                {/* 检测到的信号 */}
                {result.signals.length > 0 ? (
                  <div className="space-y-2">
                    <h5 className="text-sm font-medium flex items-center">
                      <AlertCircle className="mr-2 h-4 w-4 text-warning" />
                      检测到 {result.signals.length} 个信号
                    </h5>
                    <div className="space-y-2">
                      {result.signals.map((signal, sigIndex) => (
                        <div
                          key={sigIndex}
                          className="flex items-start space-x-2 p-2 rounded bg-accent/50"
                        >
                          {renderSignalBadge(signal.signal_type)}
                          <span className="text-sm flex-1">{signal.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center text-sm text-muted-foreground">
                    <Check className="mr-2 h-4 w-4 text-success" />
                    无明显交易信号
                  </div>
                )}

                {/* 量能分析 */}
                {(result.price_angle !== undefined || result.momentum_strength !== undefined || result.volume_power !== undefined) && (
                  <div className="p-3 rounded-lg border bg-card">
                    <h5 className="text-sm font-medium mb-2 flex items-center">
                      📊 量能分析
                    </h5>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                      {result.price_angle !== undefined && (
                        <div>
                          <span className="text-muted-foreground">价格角度:</span>{' '}
                          <span className={`font-medium ${
                            result.price_angle > 30 ? 'text-success' : 
                            result.price_angle < -30 ? 'text-danger' : ''
                          }`}>
                            {result.price_angle.toFixed(1)}°
                          </span>
                        </div>
                      )}
                      {result.momentum_strength !== undefined && (
                        <div>
                          <span className="text-muted-foreground">动量强度:</span>{' '}
                          <span className={`font-medium ${
                            result.momentum_strength > 0.5 ? 'text-success' : 
                            result.momentum_strength < -0.5 ? 'text-danger' : ''
                          }`}>
                            {result.momentum_strength.toFixed(2)}
                          </span>
                        </div>
                      )}
                      {result.volume_power !== undefined && (
                        <div>
                          <span className="text-muted-foreground">量能力量:</span>{' '}
                          <span className={`font-medium ${
                            result.volume_power > 5 ? 'text-success' : 
                            result.volume_power < -5 ? 'text-danger' : ''
                          }`}>
                            {result.volume_power.toFixed(2)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 势能分析 */}
                {(result.momentum_3d !== undefined || result.momentum_5d !== undefined || result.acceleration !== undefined) && (
                  <div className="p-3 rounded-lg border bg-card">
                    <h5 className="text-sm font-medium mb-2 flex items-center">
                      ⚡ 势能分析
                    </h5>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                      {result.momentum_3d !== undefined && (
                        <div>
                          <span className="text-muted-foreground">3日动量:</span>{' '}
                          <span className={`font-medium ${
                            result.momentum_3d > 3 ? 'text-success' : 
                            result.momentum_3d < -3 ? 'text-danger' : ''
                          }`}>
                            {result.momentum_3d >= 0 ? '+' : ''}{result.momentum_3d.toFixed(2)}%
                          </span>
                        </div>
                      )}
                      {result.momentum_5d !== undefined && (
                        <div>
                          <span className="text-muted-foreground">5日动量:</span>{' '}
                          <span className={`font-medium ${
                            result.momentum_5d > 5 ? 'text-success' : 
                            result.momentum_5d < -5 ? 'text-danger' : ''
                          }`}>
                            {result.momentum_5d >= 0 ? '+' : ''}{result.momentum_5d.toFixed(2)}%
                          </span>
                        </div>
                      )}
                      {result.acceleration !== undefined && (
                        <div>
                          <span className="text-muted-foreground">加速度:</span>{' '}
                          <span className={`font-medium ${
                            result.acceleration > 2 ? 'text-success' : 
                            result.acceleration < -2 ? 'text-danger' : ''
                          }`}>
                            {result.acceleration >= 0 ? '+' : ''}{result.acceleration.toFixed(2)}%
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 持仓信息 */}
                {result.portfolio?.has_position && (
                  <div className="p-3 rounded-lg border bg-card">
                    <h5 className="text-sm font-medium mb-2 flex items-center">
                      💼 持仓情况
                    </h5>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">持仓:</span>{' '}
                        <span className="font-medium">
                          {result.portfolio.quantity} 股
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">成本:</span>{' '}
                        <span className="font-medium">
                          ¥{result.portfolio.avg_cost.toFixed(2)}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">浮盈:</span>{' '}
                        <span
                          className={`font-medium ${
                            result.portfolio.unrealized_pnl >= 0
                              ? 'text-success'
                              : 'text-danger'
                          }`}
                        >
                          ¥{result.portfolio.unrealized_pnl.toFixed(2)} (
                          {result.portfolio.pnl_pct >= 0 ? '+' : ''}
                          {result.portfolio.pnl_pct.toFixed(2)}%)
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* AI 分析 */}
                {(result.llm_summary || result.llm_advice) && (
                  <div className="p-3 rounded-lg border bg-gradient-to-r from-primary/5 to-secondary/5">
                    <h5 className="text-sm font-medium mb-2 flex items-center">
                      🤖 AI 分析
                    </h5>
                    {result.llm_summary && (
                      <p className="text-sm mb-2">{result.llm_summary}</p>
                    )}
                    {result.llm_advice && (
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-muted-foreground">建议:</span>
                        <Badge variant="info">{result.llm_advice}</Badge>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* 空状态 */}
      {!loading && results.length === 0 && !showHistory && (
        <EmptyState
          icon={<Activity className="h-12 w-12" />}
          title="开始监控你的股票"
          description="输入股票代码，选择监控指标，点击开始监控即可实时获取交易信号"
        />
      )}
    </div>
  );
}
