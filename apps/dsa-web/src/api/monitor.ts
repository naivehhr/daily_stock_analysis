/**
 * 监控模块 API 客户端
 */

import apiClient from './index';

export interface MonitorRequest {
  stock_codes: string[];
  indicators?: string[];
  with_portfolio?: boolean;
  account_id?: number;
}

export interface MonitorSignal {
  indicator: string;
  signal_type: string;
  confidence: number;
  description: string;
}

export interface PortfolioContext {
  has_position: boolean;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_pct: number;
  position_ratio: number;
}

export interface MonitorResult {
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
  
  signals: MonitorSignal[];
  llm_summary?: string;
  llm_advice?: string;
  llm_confidence?: string;
  portfolio?: PortfolioContext;
  timestamp: string;
  analysis_duration_ms: number;
}

export interface MonitorResponse {
  status: string;
  results?: MonitorResult[];
  error?: string;
}

export interface HistoryQueryParams {
  stock_code?: string;
  limit?: number;
  days?: number;
}

export interface HistoryRecord {
  id: number;
  stock_code: string;
  triggered_at: string;
  signal_types: string[];
  summary: string;
  report_json: string;
  notified: boolean;
  created_at: string;
}

export interface HistoryDetail extends HistoryRecord {
  report_data?: Record<string, unknown>;
  created_at: string; // 明确声明，确保 TypeScript 识别
}

// === 监控规则管理类型 ===

export interface MonitorRule {
  id: number;
  user_id?: string | null;
  stock_code: string;
  indicators: string[];
  custom_rules?: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateMonitorRuleRequest {
  stock_code: string;
  indicators?: string[];
  custom_rules?: Record<string, unknown>;
  is_active?: boolean;
}

export interface UpdateMonitorRuleRequest {
  indicators?: string[];
  custom_rules?: Record<string, unknown>;
  is_active?: boolean;
}

export const monitorApi = {
  /**
   * 执行监控分析
   */
  async analyze(request: MonitorRequest): Promise<MonitorResponse> {
    const response = await apiClient.post('/api/v1/monitor/analyze', request);
    return response.data;
  },

  /**
   * 查询监控历史
   */
  async getHistory(params: HistoryQueryParams = {}): Promise<HistoryRecord[]> {
    const response = await apiClient.get('/api/v1/monitor/history', { params });
    return response.data;
  },

  /**
   * 获取监控历史详情
   */
  async getHistoryDetail(recordId: number): Promise<HistoryDetail> {
    const response = await apiClient.get(`/api/v1/monitor/history/${recordId}`);
    return response.data;
  },

  /**
   * 删除单条监控历史记录
   */
  async deleteHistory(recordId: number): Promise<{ message: string; record_id: number }> {
    const response = await apiClient.delete(`/api/v1/monitor/history/${recordId}`);
    return response.data;
  },

  /**
   * 批量删除监控历史记录
   */
  async batchDeleteHistory(
    recordIds: number[]
  ): Promise<{ message: string; deleted_count: number }> {
    const response = await apiClient.post('/api/v1/monitor/history/batch-delete', recordIds);
    return response.data;
  },

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{ status: string; module: string }> {
    const response = await apiClient.get('/api/v1/monitor/health');
    return response.data;
  },

  // === 监控规则管理 API ===

  /**
   * 查询监控规则列表
   */
  async listRules(params?: {
    user_id?: string;
    stock_code?: string;
    is_active?: boolean;
  }): Promise<MonitorRule[]> {
    const response = await apiClient.get('/api/v1/monitor/rules', { params });
    return response.data;
  },

  /**
   * 获取单个监控规则
   */
  async getRule(ruleId: number): Promise<MonitorRule> {
    const response = await apiClient.get(`/api/v1/monitor/rules/${ruleId}`);
    return response.data;
  },

  /**
   * 创建监控规则
   */
  async createRule(request: CreateMonitorRuleRequest): Promise<MonitorRule> {
    const response = await apiClient.post('/api/v1/monitor/rules', request);
    return response.data;
  },

  /**
   * 更新监控规则
   */
  async updateRule(
    ruleId: number,
    request: UpdateMonitorRuleRequest
  ): Promise<MonitorRule> {
    const response = await apiClient.put(`/api/v1/monitor/rules/${ruleId}`, request);
    return response.data;
  },

  /**
   * 删除监控规则
   */
  async deleteRule(ruleId: number): Promise<{ message: string; rule_id: number }> {
    const response = await apiClient.delete(`/api/v1/monitor/rules/${ruleId}`);
    return response.data;
  },

  /**
   * 批量删除监控规则
   */
  async batchDeleteRules(
    ruleIds: number[]
  ): Promise<{ message: string; deleted_count: number }> {
    const response = await apiClient.post('/api/v1/monitor/rules/batch-delete', ruleIds);
    return response.data;
  },
};
