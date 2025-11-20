import React, { useEffect, useState } from 'react';
import type { AiChat } from '@leeoohoo/aichat';

// 简单插件面板：复用现有后端接口，替代内置 MCP 管理
export const McpManagerPluginPanel: React.FC<{ aiChat: AiChat }> = ({ aiChat }) => {
  const api = aiChat.getApiClient();
  const cfg = aiChat.getConfig();
  const userId = cfg.userId;

  type AnyObj = Record<string, any>;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);

  const emptyForm = {
    id: '',
    name: '',
    type: 'http' as 'http',
    command: '',
    enabled: true,
  };

  const [form, setForm] = useState<any>({ ...emptyForm });
  const [editingId, setEditingId] = useState<string | null>(null);
  const isEditing = !!editingId;
  const [showForm, setShowForm] = useState(false); // 列表优先，点击新增/编辑才显示表单

  const loadAll = async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.getMcpConfigs(userId);
      setItems(Array.isArray(data) ? data : []);
    } catch (e: any) {
      setError(e?.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  const reset = () => {
    setEditingId(null);
    setForm({ ...emptyForm });
    setShowForm(false);
  };

  const startEdit = async (it: AnyObj) => {
    setEditingId(it.id);
    setForm({
      id: it.id,
      name: it.name || '',
      type: 'http',
      command: it.command || '',
      enabled: !!it.enabled,
    });
    setShowForm(true);
  };

  const upsert = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const body: AnyObj = {
        name: form.name.trim(),
        command: form.command.trim(), // 作为 URL 使用
        type: 'http',
        enabled: !!form.enabled,
        user_id: userId,
      };
      if (!editingId) {
        await api.createMcpConfig({ id: `mcp_${Date.now()}_${Math.random().toString(36).slice(2,8)}`, ...(body as any) } as any);
      } else {
        await api.updateMcpConfig(editingId, body);
      }
      await loadAll();
      reset();
    } catch (e: any) {
      setError(e?.message || '保存失败');
    }
  };

  const removeOne = async (id: string) => {
    if (!confirm('确定删除该服务器配置吗？')) return;
    try { await api.deleteMcpConfig(id); await loadAll(); if (editingId === id) reset(); } catch (e: any) { alert(e?.message || '删除失败'); }
  };

  const toggleEnabled = async (it: AnyObj) => {
    try { await api.updateMcpConfig(it.id, { enabled: !it.enabled }); await loadAll(); } catch {}
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <div className="font-medium">MCP 服务器管理（插件）</div>
        <div className="flex items-center gap-2">
          <button className="px-2 py-1 text-xs bg-gray-100 rounded border" onClick={loadAll}>刷新</button>
        </div>
      </div>

      {error && <div className="mb-2 text-xs text-red-600">{error}</div>}

      {/* 新建/编辑表单（仅在触发时显示） */}
      {showForm && (
        <form onSubmit={upsert} className="p-2 border rounded mb-3">
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs">名称<input className="mt-1 w-full border rounded px-2 py-1 text-sm" value={form.name} onChange={(e)=>setForm({...form, name:e.target.value})} required/></label>
            <div className="text-xs" />
            <label className="text-xs col-span-2">URL
              <input className="mt-1 w-full border rounded px-2 py-1 text-sm" placeholder="https://your-mcp-server.example.com" value={form.command} onChange={(e)=>setForm({...form, command:e.target.value})} required/>
            </label>
            <label className="text-xs flex items-center gap-2"> <input type="checkbox" checked={!!form.enabled} onChange={(e)=>setForm({...form, enabled:e.target.checked})}/> 启用</label>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <button type="submit" className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm">{isEditing?'更新':'添加'}</button>
            <button type="button" className="px-3 py-1.5 bg-gray-200 rounded text-sm" onClick={reset}>取消</button>
          </div>
        </form>
      )}

      {/* 配置列表 */}
      <div className="space-y-2">
        <div className="mb-2 flex items-center justify-between">
          <div className="text-xs text-gray-600">{loading ? '加载中…' : `共 ${items.length} 个服务器`}</div>
          {!showForm && (
            <button className="px-2 py-1 text-xs bg-blue-600 text-white rounded" onClick={()=>{ setShowForm(true); setEditingId(null); setForm({ ...emptyForm }); }}>新增</button>
          )}
        </div>
        {!loading && items.length===0 && <div className="text-xs text-gray-500">暂无配置</div>}
        {items.map(it => (
          <div key={it.id} className="border rounded p-2">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium">{it.name} <span className="ml-2 text-xs text-gray-500">[{it.type}]</span></div>
            <div className="flex items-center gap-2">
                <button className="px-2 py-0.5 text-xs border rounded" onClick={()=>startEdit(it)}>编辑</button>
                <button className="px-2 py-0.5 text-xs border rounded" onClick={()=>toggleEnabled(it)}>{it.enabled?'禁用':'启用'}</button>
                <button className="px-2 py-0.5 text-xs border rounded text-red-600" onClick={()=>removeOne(it.id)}>删除</button>
              </div>
            </div>
            <div className="mt-1 text-xs text-gray-600 break-all">URL: {it.command}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// 注册插件：向 App 注入一个带按钮的弹窗面板
export function registerMcpManagerPlugin() {
  if (typeof window === 'undefined') return;
  const reg = (window as any).registerAiChatPlugin;
  if (typeof reg !== 'function') return;
  reg({
    id: 'mcp-manager-plugin',
    name: 'MCP 管理',
    icon: <span className="text-xs">MCP</span>,
    render: ({ aiChat }: { aiChat: AiChat }) => <McpManagerPluginPanel aiChat={aiChat} />,
  });
}

declare global {
  interface Window {
    registerAiChatPlugin?: (plugin: any) => void;
  }
}
