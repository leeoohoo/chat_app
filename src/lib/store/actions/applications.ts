import type { Application } from '../../../types';

interface Deps {
  set: any;
  get: any;
  client: any;
  getUserIdParam: () => string;
}

export function createApplicationActions({ set, get, client, getUserIdParam }: Deps) {
  const toFrontendApp = (apiApp: any): Application => ({
    id: apiApp.id,
    name: apiApp.name,
    url: apiApp.url,
    iconUrl: apiApp.icon_url ?? undefined,
    createdAt: new Date(apiApp.created_at),
    updatedAt: new Date(apiApp.updated_at ?? apiApp.created_at),
  });

  return {
    // 应用管理
    loadApplications: async () => {
      try {
        const userId = getUserIdParam();
        const items = await client.getApplications(userId);
        const apps: Application[] = (items || []).map(toFrontendApp);
        set((state: any) => {
          state.applications = apps;
        });
      } catch (error) {
        console.error('Failed to load applications:', error);
        set((state: any) => {
          state.applications = [];
        });
      }
    },
    createApplication: async (name: string, url: string, iconUrl?: string) => {
      try {
        const created = await client.createApplication({
          name,
          url,
          icon_url: iconUrl ?? null,
          user_id: getUserIdParam(),
        });
        const app = toFrontendApp(created);
        set((state: any) => {
          state.applications = [app, ...state.applications];
        });
      } catch (error) {
        console.error('Failed to create application:', error);
        set((state: any) => {
          state.error = error instanceof Error ? error.message : 'Failed to create application';
        });
      }
    },
    updateApplication: async (id: string, updates: Partial<Application>) => {
      try {
        const payload: any = {};
        if (updates.name !== undefined) payload.name = updates.name;
        if (updates.url !== undefined) payload.url = updates.url;
        if (updates.iconUrl !== undefined) payload.icon_url = updates.iconUrl ?? null;
        const updated = await client.updateApplication(id, payload);
        const nextApp = toFrontendApp(updated);
        set((state: any) => {
          state.applications = state.applications.map((a: Application) =>
            a.id === id ? nextApp : a
          );
        });
      } catch (error) {
        console.error('Failed to update application:', error);
        set((state: any) => {
          state.error = error instanceof Error ? error.message : 'Failed to update application';
        });
      }
    },
    deleteApplication: async (id: string) => {
      try {
        await client.deleteApplication(id);
        // 清理关联映射（仍在前端维护）
        const mcpRaw = localStorage.getItem('mcp_app_map');
        const sysRaw = localStorage.getItem('sysctx_app_map');
        const agentRaw = localStorage.getItem('agent_app_map');
        const mcpMap = mcpRaw ? (JSON.parse(mcpRaw) as Record<string, string[]>) : {};
        const sysMap = sysRaw ? (JSON.parse(sysRaw) as Record<string, string[]>) : {};
        const agentMap = agentRaw ? (JSON.parse(agentRaw) as Record<string, string[]>) : {};
        Object.keys(mcpMap).forEach((k) => {
          const arr = Array.isArray(mcpMap[k]) ? mcpMap[k] : [];
          mcpMap[k] = arr.filter((aid) => aid !== id);
        });
        Object.keys(sysMap).forEach((k) => {
          const arr = Array.isArray(sysMap[k]) ? sysMap[k] : [];
          sysMap[k] = arr.filter((aid) => aid !== id);
        });
        Object.keys(agentMap).forEach((k) => {
          const arr = Array.isArray(agentMap[k]) ? agentMap[k] : [];
          agentMap[k] = arr.filter((aid) => aid !== id);
        });
        localStorage.setItem('mcp_app_map', JSON.stringify(mcpMap));
        localStorage.setItem('sysctx_app_map', JSON.stringify(sysMap));
        localStorage.setItem('agent_app_map', JSON.stringify(agentMap));
        set((state: any) => {
          state.applications = state.applications.filter((a: Application) => a.id !== id);
          // 同步内存中的 appId 字段
          state.mcpConfigs = state.mcpConfigs.map((c: any) => ({ ...c, appIds: mcpMap[c.id] ?? [] }));
          state.systemContexts = state.systemContexts.map((c: any) => ({ ...c, appIds: sysMap[c.id] ?? [] }));
          state.agents = state.agents.map((a: any) => ({ ...a, appIds: agentMap[a.id] ?? [] }));
        });
      } catch (error) {
        console.error('Failed to delete application:', error);
        set((state: any) => {
          state.error = error instanceof Error ? error.message : 'Failed to delete application';
        });
      }
    },
    setSelectedApplication: (appId: string | null) => {
      set((state: any) => {
        state.selectedApplicationId = appId;
      });
    },
    setMcpAppAssociation: (mcpId: string, appIds: string[]) => {
      const raw = localStorage.getItem('mcp_app_map');
      const map = raw ? (JSON.parse(raw) as Record<string, string[]>) : {};
      map[mcpId] = Array.isArray(appIds) ? appIds : [];
      localStorage.setItem('mcp_app_map', JSON.stringify(map));
      set((state: any) => {
        state.mcpConfigs = state.mcpConfigs.map((c: any) => (c.id === mcpId ? { ...c, appIds: map[mcpId] } : c));
      });
    },
    setSystemContextAppAssociation: (contextId: string, appIds: string[]) => {
      const raw = localStorage.getItem('sysctx_app_map');
      const map = raw ? (JSON.parse(raw) as Record<string, string[]>) : {};
      map[contextId] = Array.isArray(appIds) ? appIds : [];
      localStorage.setItem('sysctx_app_map', JSON.stringify(map));
      set((state: any) => {
        state.systemContexts = state.systemContexts.map((c: any) => (c.id === contextId ? { ...c, appIds: map[contextId] } : c));
      });
    },
    setAgentAppAssociation: (agentId: string, appIds: string[]) => {
      const raw = localStorage.getItem('agent_app_map');
      const map = raw ? (JSON.parse(raw) as Record<string, string[]>) : {};
      map[agentId] = Array.isArray(appIds) ? appIds : [];
      localStorage.setItem('agent_app_map', JSON.stringify(map));
      set((state: any) => {
        state.agents = state.agents.map((a: any) => (a.id === agentId ? { ...a, appIds: map[agentId] } : a));
      });
    },
  };
}