import React, { useEffect, useState } from 'react';
import { useChatStoreFromContext, useChatRuntimeEnv, useChatApiClientFromContext } from '../lib/store/ChatStoreContext';
import { useChatStore } from '../lib/store';
import { apiClient as globalApiClient } from '../lib/api/client';
import type ApiClient from '../lib/api/client';

interface AgentManagerProps {
  onClose?: () => void;
  store?: any; // 可选的store参数，用于在没有Context Provider的情况下使用
}

interface AgentItem {
  id: string;
  name: string;
  description?: string;
  ai_model_config_id: string;
  mcp_config_ids: string[];
  callable_agent_ids?: string[];
  system_context_id?: string;
  enabled: boolean;
  created_at?: string;
}

const RobotIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6M9 16h6M6 8h12a2 2 0 012 2v8a2 2 0 01-2 2H6a2 2 0 01-2-2v-8a2 2 0 012-2z" />
  </svg>
);

const XMarkIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const PlusIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
);

const TrashIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);

const AgentManager: React.FC<AgentManagerProps> = ({ onClose, store: externalStore }) => {
  // 选择store来源
  let storeData;
  if (externalStore) {
    storeData = externalStore();
  } else {
    try {
      storeData = useChatStoreFromContext();
    } catch (error) {
      storeData = useChatStore();
    }
  }

  const {
    aiModelConfigs,
    loadAiModelConfigs,
    mcpConfigs,
    loadMcpConfigs,
    systemContexts,
    loadSystemContexts,
  } = storeData;

  // 从上下文获取当前用户环境
  const { userId: contextUserId } = useChatRuntimeEnv();
  const effectiveUserId = contextUserId || 'custom_user_123';
  const clientFromContext = useChatApiClientFromContext();
  const client: ApiClient = clientFromContext || globalApiClient;

  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [detailAgent, setDetailAgent] = useState<AgentItem | null>(null);
  const [editingAgent, setEditingAgent] = useState<AgentItem | null>(null);

  const [formData, setFormData] = useState<{
    name: string;
    description: string;
    ai_model_config_id: string;
    mcp_config_ids: string[];
    system_context_id?: string;
  }>({
    name: '',
    description: '',
    ai_model_config_id: '',
    mcp_config_ids: [],
    system_context_id: undefined,
  });

  const loadAll = async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        loadAiModelConfigs(),
        loadMcpConfigs(),
        loadSystemContexts(),
        // 刷新全局store中的智能体列表，供输入区选择
        (storeData.loadAgents ? storeData.loadAgents() : Promise.resolve()),
      ]);
      // 优先使用store加载的agents以保证与全局状态一致
      const list = storeData.agents && Array.isArray(storeData.agents)
        ? storeData.agents
        : await client.getAgents(effectiveUserId);
      setAgents(Array.isArray(list) ? list : []);
    } catch (e) {
      console.error('加载智能体失败', e);
    } finally {
      setIsLoading(false);
    }
  };

  // 针对新增/更新后可能存在的读写延迟，增加一次轻量重试刷新
  const refreshAgentsWithRetry = async (createdId?: string) => {
    const maxTries = 3;
    for (let i = 0; i < maxTries; i++) {
      try {
        if (storeData.loadAgents) {
          await storeData.loadAgents();
        }
        // 始终通过客户端获取最新列表，避免在同一渲染周期读取到过期的store快照
        const list = await client.getAgents(effectiveUserId);
        setAgents(Array.isArray(list) ? list : []);
        if (createdId && Array.isArray(list) && list.some(a => a.id === createdId)) {
          break;
        }
        if (!createdId) {
          break;
        }
        await new Promise<void>((resolve) => setTimeout(resolve, 250));
      } catch (err) {
        console.warn('刷新智能体列表失败，重试中…', err);
        await new Promise<void>((resolve) => setTimeout(resolve, 250));
      }
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      ai_model_config_id: '',
      mcp_config_ids: [],
      system_context_id: undefined,
    });
    setShowAddForm(false);
    setEditingAgent(null);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.ai_model_config_id) return;
    try {
      const created = await client.createAgent({
        name: formData.name.trim(),
        description: formData.description?.trim() || undefined,
        ai_model_config_id: formData.ai_model_config_id,
        mcp_config_ids: formData.mcp_config_ids,
        system_context_id: formData.system_context_id,
        user_id: effectiveUserId,
        enabled: true,
      });
      // 乐观更新本地列表，避免等待后端读写一致性
      if (created && created.id) {
        setAgents(prev => {
          const exists = prev.some(a => a.id === created.id);
          return exists ? prev.map(a => (a.id === created.id ? { ...a, ...created } : a)) : [created, ...prev];
        });
      }
      await refreshAgentsWithRetry(created?.id);
      resetForm();
    } catch (e) {
      console.error('创建智能体失败', e);
      alert('创建失败，请重试');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAgent) return;
    try {
      const updated = await client.updateAgent(editingAgent.id, {
        name: formData.name,
        description: formData.description,
        ai_model_config_id: formData.ai_model_config_id,
        mcp_config_ids: formData.mcp_config_ids,
        system_context_id: formData.system_context_id,
        enabled: true,
      });
      // 乐观更新本地列表
      setAgents(prev => prev.map(a => (
        a.id === editingAgent.id ? { ...a, ...updated, name: formData.name, description: formData.description, ai_model_config_id: formData.ai_model_config_id, mcp_config_ids: formData.mcp_config_ids, system_context_id: formData.system_context_id, enabled: true } : a
      )));
      await refreshAgentsWithRetry(editingAgent.id);
      resetForm();
    } catch (e) {
      console.error('更新智能体失败', e);
      alert('更新失败，请重试');
    }
  };

  const handleDelete = async (agentId: string) => {
    try {
      await client.deleteAgent(agentId);
      // 本地先删除，随后刷新确保一致
      setAgents(prev => prev.filter(a => a.id !== agentId));
      await refreshAgentsWithRetry();
    } catch (e) {
      console.error('删除智能体失败', e);
      alert('删除失败，请重试');
    }
  };


  const startEdit = (agent: AgentItem) => {
    setEditingAgent(agent);
    setShowAddForm(true);
    setFormData({
      name: agent.name,
      description: agent.description || '',
      ai_model_config_id: agent.ai_model_config_id,
      mcp_config_ids: Array.isArray(agent.mcp_config_ids) ? agent.mcp_config_ids : [],
      system_context_id: agent.system_context_id,
    });
  };

  const getModelName = (id: string) => {
    const m = aiModelConfigs.find((x: any) => x.id === id);
    return m ? `${m.name}（${m.model_name}）` : id;
  };
  const getSystemContextName = (id?: string) => {
    if (!id) return '未选择';
    const s = systemContexts.find((x: any) => x.id === id);
    return s ? s.name : id;
  };
  const getMcpNames = (ids: string[]) => {
    const names = ids.map((id) => {
      const c = mcpConfigs.find((x: any) => x.id === id);
      return c ? c.name : id;
    });
    return names.join('，');
  };

  return (
    <>
      {/* 背景遮罩 */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40" onClick={onClose} />

      {/* 抽屉面板（右侧） */}
      <div className="fixed right-0 top-0 h-full w-[520px] sm:w-[560px] bg-card z-50 shadow-xl breathing-border flex flex-col">
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center space-x-3">
            <RobotIcon />
            <h2 className="text-lg font-semibold text-foreground">智能体管理</h2>
          </div>
          <button onClick={onClose} className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors" title="关闭">
            <XMarkIcon />
          </button>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* 添加按钮 */}
          {!showAddForm && (
            <button
              onClick={() => setShowAddForm(true)}
              className="w-full p-4 border-2 border-dashed border-border rounded-lg hover:border-blue-500 transition-colors flex items-center justify-center space-x-2 text-muted-foreground hover:text-blue-600"
            >
              <PlusIcon />
              <span>新增智能体</span>
            </button>
          )}

          {/* 添加/编辑表单 */}
          {showAddForm && (
            <form onSubmit={editingAgent ? handleUpdate : handleCreate} className="p-4 bg-muted rounded-lg space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="例如：项目助理"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">描述</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="智能体用途说明"
                  rows={3}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">选择模型（单选）</label>
                <select
                  value={formData.ai_model_config_id}
                  onChange={(e) => setFormData({ ...formData, ai_model_config_id: e.target.value })}
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  required
                >
                  <option value="">请选择模型</option>
                  {aiModelConfigs.map((m: any) => (
                    <option key={m.id} value={m.id}>
                      {m.name}（{m.model_name}）
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">选择 MCP 配置（多选）</label>
                <div className="space-y-2 max-h-40 overflow-y-auto p-2 border rounded-md">
                  {mcpConfigs.map((c: any) => (
                    <label key={c.id} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.mcp_config_ids.includes(c.id)}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setFormData((prev) => ({
                            ...prev,
                            mcp_config_ids: checked
                              ? [...prev.mcp_config_ids, c.id]
                              : prev.mcp_config_ids.filter((id) => id !== c.id),
                          }));
                        }}
                      />
                      <span>{c.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">选择系统上下文</label>
                <select
                  value={formData.system_context_id || ''}
                  onChange={(e) => setFormData({ ...formData, system_context_id: e.target.value || undefined })}
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">不使用</option>
                  {systemContexts.map((sc: any) => (
                    <option key={sc.id} value={sc.id}>
                      {sc.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-end space-x-2">
                <button type="button" onClick={resetForm} className="px-3 py-2 rounded bg-muted text-muted-foreground hover:bg-accent">取消</button>
                <button type="submit" className="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">保存</button>
              </div>
            </form>
          )}

          {/* 列表展示 */}
          <div>
            {isLoading ? (
              <div className="text-muted-foreground">加载中...</div>
            ) : agents.length === 0 ? (
              <div className="text-muted-foreground">暂无智能体配置</div>
            ) : (
              <div className="space-y-3">
                {agents.map((a) => (
                  <div key={a.id} className="p-4 border rounded-lg flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <h3 className="font-medium text-foreground">{a.name}</h3>
                        {!a.enabled && (
                          <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">未启用</span>
                        )}
                      </div>
                      {a.description && (
                        <p className="mt-1 text-sm text-muted-foreground">{a.description}</p>
                      )}
                      <p className="mt-2 text-xs text-muted-foreground">模型：{getModelName(a.ai_model_config_id)}</p>
                      <p className="mt-1 text-xs text-muted-foreground">系统上下文：{getSystemContextName(a.system_context_id)}</p>
                      <p className="mt-1 text-xs text-muted-foreground">MCP配置：{getMcpNames(a.mcp_config_ids || [])}</p>
                    </div>
                    <div className="flex items-center space-x-2 ml-4">
                      <button onClick={() => setDetailAgent(a)} className="px-3 py-1 text-sm bg-muted text-foreground rounded hover:bg-accent transition-colors">详情</button>
                      <button onClick={() => startEdit(a)} className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors">编辑</button>
                      <button onClick={() => handleDelete(a.id)} className="px-3 py-1 text-sm bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 transition-colors flex items-center space-x-1">
                        <TrashIcon />
                        <span>删除</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        {/* 详情弹窗 */}
        {detailAgent && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="fixed inset-0 bg-black/50" onClick={() => setDetailAgent(null)} />
            <div className="relative bg-card border border-border rounded-lg shadow-xl w-[520px] p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <RobotIcon />
                  <h3 className="text-lg font-semibold text-foreground">智能体详情</h3>
                </div>
                <button onClick={() => setDetailAgent(null)} className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors">
                  <XMarkIcon />
                </button>
              </div>
              <div className="space-y-2">
                <p><span className="text-muted-foreground">名称：</span>{detailAgent.name}</p>
                {detailAgent.description && (
                  <p><span className="text-muted-foreground">描述：</span>{detailAgent.description}</p>
                )}
                <p><span className="text-muted-foreground">模型：</span>{getModelName(detailAgent.ai_model_config_id)}</p>
                <p><span className="text-muted-foreground">系统上下文：</span>{getSystemContextName(detailAgent.system_context_id)}</p>
                <p><span className="text-muted-foreground">MCP配置：</span>{getMcpNames(detailAgent.mcp_config_ids || [])}</p>
                <p className="text-xs text-muted-foreground">创建时间：{detailAgent.created_at ? new Date(detailAgent.created_at).toLocaleString() : '-'}</p>
              </div>
              <div className="mt-4 flex justify-end space-x-2">
                <button onClick={() => setDetailAgent(null)} className="px-3 py-2 rounded bg-muted text-muted-foreground hover:bg-accent">关闭</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default AgentManager;