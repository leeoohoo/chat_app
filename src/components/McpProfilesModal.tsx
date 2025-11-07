import React, { useEffect, useState } from 'react';
import { apiClient } from '../lib/api/client';
import type { McpConfig } from '../types';

const ServerIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
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

interface CreateProfileData {
  name: string;
  envJson: string; // JSON 文本（可空，优先使用动态表单）
  enabled: boolean;
}

interface McpProfilesModalProps {
  open: boolean;
  config: McpConfig | null;
  onClose: () => void;
}

const McpProfilesModal: React.FC<McpProfilesModalProps> = ({ open, config, onClose }) => {
  const [profiles, setProfiles] = useState<any[]>([]);
  const [profilesLoading, setProfilesLoading] = useState(false);
  const [profilesError, setProfilesError] = useState<string | null>(null);

  const [editingProfileId, setEditingProfileId] = useState<string | null>(null);

  const [createProfileModalOpen, setCreateProfileModalOpen] = useState(false);
  const [createProfileData, setCreateProfileData] = useState<CreateProfileData>({
    name: '',
    envJson: '',
    enabled: false,
  });
  const [createProfileError, setCreateProfileError] = useState<string | null>(null);
  const [createDynamicConfig, setCreateDynamicConfig] = useState<Record<string, any>>({});

  useEffect(() => {
    const fetchProfiles = async () => {
      if (!open || !config?.id) return;
      setProfilesLoading(true);
      setProfilesError(null);
      try {
        const pfs = await apiClient.getMcpConfigProfiles(config.id);
        setProfiles(Array.isArray(pfs) ? pfs : []);
      } catch (e: any) {
        setProfilesError(e?.message || '获取配置档案失败');
      } finally {
        setProfilesLoading(false);
      }
    };
    fetchProfiles();
  }, [open, config?.id]);

  if (!open) return null;

  return (
    <div className="modal-container">
      <div className="modal-content w-full max-w-3xl max-h-[85vh] overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center space-x-3">
            <ServerIcon />
            <h3 className="text-lg font-semibold text-foreground">配置档案 - {config?.name}</h3>
          </div>
          <button
            onClick={() => onClose()}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
          >
            <XMarkIcon />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-4 overflow-y-auto" style={{ maxHeight: 'calc(85vh - 100px)' }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm text-muted-foreground">已保存的配置档案</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="px-2 py-1 text-xs bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80"
                onClick={async () => {
                  if (!config?.id) return;
                  setProfilesLoading(true);
                  try {
                    const pfs = await apiClient.getMcpConfigProfiles(config.id);
                    setProfiles(Array.isArray(pfs) ? pfs : []);
                  } finally {
                    setProfilesLoading(false);
                  }
                }}
              >
                刷新列表
              </button>
              <button
                type="button"
                className="px-2 py-1 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700"
                onClick={async () => {
                  if (!config?.id) return;
                  let dynamicObj: Record<string, any> | undefined;
                  try {
                    const res = await apiClient.getMcpConfigResource(config.id);
                    const cfg = (res && res.config) || {};
                    // 改为直接使用接口返回的整体 config 作为动态表单数据
                    if (cfg && typeof cfg === 'object') dynamicObj = cfg;
                  } catch {}
                  setCreateProfileData({
                    name: `配置_${new Date().toLocaleString('zh-CN')}`,
                    // 动态表单优先，不再默认填充 env JSON
                    envJson: '',
                    enabled: false,
                  });
                  setCreateDynamicConfig(dynamicObj || {});
                  setEditingProfileId(null);
                  setCreateProfileModalOpen(true);
                }}
              >
                新增配置档案
              </button>
            </div>
          </div>

          {profilesLoading ? (
            <div className="text-xs text-muted-foreground">加载中...</div>
          ) : profilesError ? (
            <div className="text-xs text-destructive">{profilesError}</div>
          ) : profiles.length === 0 ? (
            <div className="text-xs text-muted-foreground">暂无配置档案，点击右上角“新增配置档案”。</div>
          ) : (
            <div className="space-y-2">
              {profiles.map((p: any) => (
                <div key={p.id} className="px-2 py-2 border border-border rounded-md">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="text-sm text-foreground font-medium">{p.name}</div>
                      {p.enabled && (
                        <span className="px-2 py-0.5 text-[10px] rounded-full bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200">已启用</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        className="px-2 py-1 text-xs bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80"
                        onClick={async () => {
                          if (!config?.id) return;
                          try {
                            await apiClient.activateMcpConfigProfile(config.id, p.id);
                            const pfs = await apiClient.getMcpConfigProfiles(config.id);
                            setProfiles(Array.isArray(pfs) ? pfs : []);
                          } catch {}
                        }}
                      >
                        激活
                      </button>
                      <button
                        type="button"
                        className="px-2 py-1 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700"
                        onClick={() => {
                          // 进入编辑模式，预填表单
                          setEditingProfileId(p.id);
                          setCreateProfileData({
                            name: p.name || '',
                            envJson: (() => { try { return JSON.stringify(p.env || {}, null, 2); } catch { return ''; } })(),
                            enabled: !!p.enabled,
                          });
                          const env = p.env || {};
                          const parsed: Record<string, any> = {};
                          Object.keys(env || {}).forEach((k) => {
                            const v = env[k];
                            if (typeof v === 'string') {
                              const text = v.trim();
                              try { parsed[k] = JSON.parse(text); }
                              catch {
                                if (text.includes(',')) parsed[k] = text.split(',').map(s => s.trim()).filter(Boolean);
                                else parsed[k] = text;
                              }
                            } else {
                              parsed[k] = v;
                            }
                          });
                          setCreateDynamicConfig(parsed);
                          setCreateProfileModalOpen(true);
                        }}
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        className="px-2 py-1 text-xs bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/80"
                        onClick={async () => {
                          if (!config?.id) return;
                          const ok = window.confirm(`确定删除配置档案 “${p.name}” 吗？`);
                          if (!ok) return;
                          try {
                            await apiClient.deleteMcpConfigProfile(config.id, p.id);
                            const pfs = await apiClient.getMcpConfigProfiles(config.id);
                            setProfiles(Array.isArray(pfs) ? pfs : []);
                          } catch (e) {
                            console.error('删除配置档案失败:', e);
                          }
                        }}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 详情弹窗已移除：编辑与删除在列表中操作 */}

      {/* 新增配置档案表单弹窗 */}
      {createProfileModalOpen && (
        <div className="modal-container z-[100]">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => { setCreateProfileModalOpen(false); setCreateProfileError(null); }}
          />
          <div className="fixed inset-0 flex items-center justify-center p-4">
            <div className="modal-content w-full max-w-2xl transform overflow-hidden">
              <div className="flex items-center justify-between p-4 border-b border-border">
                <div className="flex items-center gap-2">
                  <PlusIcon />
                  <h3 className="text-base font-semibold text-foreground">{editingProfileId ? '编辑配置档案' : '新增配置档案'}</h3>
                </div>
                <button
                  onClick={() => { setCreateProfileModalOpen(false); setCreateProfileError(null); }}
                  className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
                >
                  <XMarkIcon />
                </button>
              </div>
              <div className="p-4">
                {createProfileError && (
                  <div className="mb-2 text-xs text-destructive">{createProfileError}</div>
                )}
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">名称</label>
                    <input
                      type="text"
                      value={createProfileData.name}
                      onChange={(e) => setCreateProfileData({ ...createProfileData, name: e.target.value })}
                      className="w-full px-3 py-2 border border-input bg-background text-foreground rounded-md"
                    />
                  </div>
                  <div>
                    {createDynamicConfig && Object.keys(createDynamicConfig).length > 0 && (
                      <div className="mb-3">
                        <label className="block text-xs font-medium text-foreground mb-1">动态参数</label>
                        <div className="grid grid-cols-1 gap-3">
                          {Object.keys(createDynamicConfig).map((key) => {
                            const val = createDynamicConfig[key];
                            const type = typeof val;
                            const isArray = Array.isArray(val);
                            return (
                              <div key={key}>
                                <label className="block text-xs text-muted-foreground mb-1">{key}</label>
                                {type === 'boolean' ? (
                                  <div className="flex items-center">
                                    <input
                                      type="checkbox"
                                      checked={!!val}
                                      onChange={(e) => setCreateDynamicConfig({ ...createDynamicConfig, [key]: e.target.checked })}
                                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                    />
                                    <span className="ml-2 text-xs">{String(val)}</span>
                                  </div>
                                ) : isArray ? (
                                  <input
                                    type="text"
                                    value={(val as any[]).join(', ')}
                                    onChange={(e) => setCreateDynamicConfig({
                                      ...createDynamicConfig,
                                      [key]: e.target.value
                                        .split(',')
                                        .map(s => s.trim())
                                        .filter(Boolean)
                                    })}
                                    className="w-full px-2 py-1 border border-input bg-background text-foreground rounded-md"
                                  />
                                ) : type === 'object' && val !== null ? (
                                  <textarea
                                    value={(() => { try { return JSON.stringify(val, null, 2); } catch { return String(val); } })()}
                                    onChange={(e) => {
                                      try {
                                        const parsed = JSON.parse(e.target.value);
                                        setCreateDynamicConfig({ ...createDynamicConfig, [key]: parsed });
                                      } catch {
                                        // 保留原始文本，避免打断输入；最终保存会进行JSON序列化
                                        setCreateDynamicConfig({ ...createDynamicConfig, [key]: e.target.value });
                                      }
                                    }}
                                    rows={4}
                                    className="w-full px-2 py-1 border border-input bg-background text-foreground rounded-md font-mono text-xs"
                                  />
                                ) : (
                                  <input
                                    type={type === 'number' ? 'number' : 'text'}
                                    value={val ?? ''}
                                    onChange={(e) => setCreateDynamicConfig({
                                      ...createDynamicConfig,
                                      [key]: type === 'number' ? Number(e.target.value) : e.target.value
                                    })}
                                    className="w-full px-2 py-1 border border-input bg-background text-foreground rounded-md"
                                  />
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                    {/* 移除默认的 env(JSON) 输入，仅在需要时可扩展加入高级开关 */}
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    className="px-3 py-1 text-xs bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80"
                    onClick={() => { setCreateProfileModalOpen(false); setCreateProfileError(null); }}
                  >
                    取消
                  </button>
                  <button
                    type="button"
                    className="px-3 py-1 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700"
                    onClick={async () => {
                      setCreateProfileError(null);
                      try {
                        if (!config?.id) throw new Error('缺少配置ID');
                        // 优先使用动态表单的修改内容；仅当动态表单为空时，才回退到旧的 envJson
                        let envObj: Record<string, any> | null = null;
                        const hasDynamic = createDynamicConfig && Object.keys(createDynamicConfig).length > 0;
                        if (hasDynamic) {
                          envObj = createDynamicConfig;
                        } else {
                          const envText = (createProfileData.envJson || '').trim();
                          if (envText) {
                            try {
                              const parsed = JSON.parse(envText);
                              if (parsed && typeof parsed === 'object') envObj = parsed;
                            } catch (e: any) {
                              throw new Error('env JSON 格式错误');
                            }
                          }
                        }
                        let finalEnv: Record<string, string> | null = null;
                        if (envObj && typeof envObj === 'object') {
                          finalEnv = {};
                          for (const k of Object.keys(envObj)) {
                            const v = envObj[k];
                            if (Array.isArray(v)) finalEnv[k] = v.join(',');
                            else if (typeof v === 'boolean' || typeof v === 'number') finalEnv[k] = String(v);
                            else if (v === null || v === undefined) finalEnv[k] = '';
                            else if (typeof v === 'object') finalEnv[k] = JSON.stringify(v);
                            else finalEnv[k] = String(v);
                          }
                        }
                        if (editingProfileId) {
                          const res = await apiClient.updateMcpConfigProfile(config.id, editingProfileId, {
                            name: createProfileData.name,
                            env: finalEnv,
                            enabled: createProfileData.enabled,
                          });
                          if (res) {
                            const pfs = await apiClient.getMcpConfigProfiles(config.id);
                            setProfiles(Array.isArray(pfs) ? pfs : []);
                            setCreateProfileModalOpen(false);
                            setEditingProfileId(null);
                          } else {
                            throw new Error('更新失败');
                          }
                        } else {
                          const res = await apiClient.createMcpConfigProfile(config.id, {
                            name: createProfileData.name,
                            env: finalEnv,
                            enabled: createProfileData.enabled,
                          });
                          if (res && (res.id || res.success)) {
                            const pfs = await apiClient.getMcpConfigProfiles(config.id);
                            setProfiles(Array.isArray(pfs) ? pfs : []);
                            setCreateProfileModalOpen(false);
                          } else {
                            throw new Error('创建失败');
                          }
                        }
                      } catch (e: any) {
                        setCreateProfileError(e?.message || '保存失败');
                      }
                    }}
                  >
                    保存
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default McpProfilesModal;