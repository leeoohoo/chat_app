import React, { useEffect, useState } from 'react';
import { useChatStoreFromContext } from '../lib/store/ChatStoreContext';
import { useChatStore } from '../lib/store';

interface ApplicationManagerProps {
  onClose?: () => void;
  store?: any; // 可选的store参数，用于在没有Context Provider的情况下使用
}

const ApplicationManager: React.FC<ApplicationManagerProps> = ({ onClose, store: externalStore }) => {
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
    applications,
    selectedApplicationId,
    loadApplications,
    createApplication,
    updateApplication,
    deleteApplication,
    setSelectedApplication,
  } = storeData;

  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<{ name: string; url: string; iconUrl: string }>(
    { name: '', url: '', iconUrl: '' }
  );

  useEffect(() => {
    loadApplications?.();
  }, [loadApplications]);

  const resetForm = () => {
    setEditingId(null);
    setFormData({ name: '', url: '', iconUrl: '' });
    setShowAddForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    if (editingId) {
      await updateApplication?.(editingId, {
        name: formData.name.trim(),
        url: formData.url.trim(),
        iconUrl: formData.iconUrl.trim() || undefined,
      });
    } else {
      await createApplication?.(formData.name.trim(), formData.url.trim(), formData.iconUrl.trim() || undefined);
    }
    resetForm();
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
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-500" />
            <h2 className="text-lg font-semibold text-foreground">应用管理</h2>
          </div>
          <button onClick={onClose} className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors" title="关闭">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>

        {/* 内容区域 */}
        <div className="p-4 flex-1 overflow-y-auto space-y-4">
          {/* 添加按钮 */}
          {!showAddForm && (
            <button
              onClick={() => setShowAddForm(true)}
              className="w-full mb-2 p-4 border-2 border-dashed border-border rounded-lg hover:border-blue-500 transition-colors flex items-center justify-center space-x-2 text-muted-foreground hover:text-blue-600"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m6-6H6"/></svg>
              <span>新增应用</span>
            </button>
          )}

          {/* 添加/编辑表单 */}
          {showAddForm && (
            <form onSubmit={handleSubmit} className="mb-4 p-4 bg-muted rounded-lg space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="例如：Jira、GitHub"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">URL</label>
                <input
                  type="text"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="https://app.example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">图标URL</label>
                <input
                  type="text"
                  value={formData.iconUrl}
                  onChange={(e) => setFormData({ ...formData, iconUrl: e.target.value })}
                  className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="https://app.example.com/icon.png"
                />
              </div>
              <div className="flex items-center justify-end space-x-2">
                <button type="button" className="px-3 py-2 rounded bg-muted hover:bg-accent" onClick={resetForm}>取消</button>
                <button type="submit" className="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">{editingId ? '保存' : '创建'}</button>
              </div>
            </form>
          )}

          {/* 应用列表 */}
          <div className="space-y-2">
            {applications?.map((app: any) => (
              <div key={app.id} className="flex items-center justify-between p-3 rounded border hover:bg-muted transition-colors">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center overflow-hidden">
                    {app.iconUrl ? (
                      <img src={app.iconUrl} alt={app.name} className="w-8 h-8 object-cover"/>
                    ) : (
                      <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-500" />
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-foreground">{app.name}</div>
                    {app.url && <div className="text-xs text-muted-foreground">{app.url}</div>}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    className={`px-2 py-1 text-xs rounded ${selectedApplicationId === app.id ? 'bg-green-600 text-white' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'}`}
                    onClick={() => setSelectedApplication?.(selectedApplicationId === app.id ? null : app.id)}
                  >
                    {selectedApplicationId === app.id ? '已选中' : '选择'}
                  </button>
                  <button
                    className="px-2 py-1 text-xs bg-muted rounded hover:bg-accent"
                    onClick={() => {
                      setEditingId(app.id);
                      setShowAddForm(true);
                      setFormData({ name: app.name, url: app.url || '', iconUrl: app.iconUrl || '' });
                    }}
                  >编辑</button>
                  <button
                    className="px-2 py-1 text-xs bg-destructive text-destructive-foreground rounded hover:bg-destructive/90"
                    onClick={() => deleteApplication?.(app.id)}
                  >删除</button>
                </div>
              </div>
            ))}
            {applications?.length === 0 && (
              <div className="text-sm text-muted-foreground">暂无应用，点击上方按钮添加。</div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default ApplicationManager;