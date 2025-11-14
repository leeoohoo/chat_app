import type { McpConfig } from '../../../types';
import type ApiClient from '../../api/client';

interface Deps {
  set: any;
  get: any;
  client: ApiClient;
  getUserIdParam: () => string;
}

export function createMcpActions({ set, get, client, getUserIdParam }: Deps) {
  return {
    loadMcpConfigs: async () => {
      try {
        const userId = getUserIdParam();
        const configs = await client.getMcpConfigs(userId);

        const assocRaw = localStorage.getItem('mcp_app_map');
        const assoc = assocRaw ? (JSON.parse(assocRaw) as Record<string, string[]>) : {};
        const merged = (configs as McpConfig[]).map((c: any) => ({ ...c, appIds: assoc[c.id] ?? [] }));

        set((state: any) => {
          state.mcpConfigs = merged as McpConfig[];
        });
      } catch (error) {
        console.error('Failed to load MCP configs:', error);
        set((state: any) => {
          state.error = error instanceof Error ? error.message : 'Failed to load MCP configs';
        });
      }
    },

    updateMcpConfig: async (config: McpConfig) => {
      try {
        const userId = getUserIdParam();
        console.log('🔍 updateMcpConfig 调用:', {
          userId,
          configId: (config as any).id,
          configName: (config as any).name,
        });

        let saved: McpConfig | null = null;
        if ((config as any).id) {
          const updateData: any = {
            id: (config as any).id,
            name: (config as any).name,
            command: (config as any).command,
            type: (config as any).type,
            args: (config as any).args ?? undefined,
            env: (config as any).env ?? undefined,
            cwd: (config as any).cwd ?? undefined,
            enabled: (config as any).enabled,
            userId,
          };
          console.log('🔍 updateMcpConfig 更新数据:', updateData);
          saved = await (client as any).updateMcpConfig(updateData);
        } else {
          // 如果没有 id，视为创建
          const createData: any = {
            name: (config as any).name,
            command: (config as any).command,
            type: (config as any).type,
            args: (config as any).args ?? undefined,
            env: (config as any).env ?? undefined,
            cwd: (config as any).cwd ?? undefined,
            enabled: (config as any).enabled,
            userId,
          };
          saved = await (client as any).createMcpConfig(createData);
        }

        // 前端持久化 MCP 与应用的关联（数组）
        const assocRaw = localStorage.getItem('mcp_app_map');
        const assoc = assocRaw ? (JSON.parse(assocRaw) as Record<string, string[]>) : {};
        const targetId = (saved as any)?.id ?? (config as any).id;
        if (targetId) {
          const nextIds: string[] = Array.isArray((config as any).appIds)
            ? (config as any).appIds
            : (assoc[targetId] ?? []);
          assoc[targetId] = nextIds;
          localStorage.setItem('mcp_app_map', JSON.stringify(assoc));
        }

        // 重新加载配置
        await get().loadMcpConfigs();

        return saved;
      } catch (error) {
        console.error('Failed to update MCP config:', error);
        set((state: any) => {
          state.error = error instanceof Error ? error.message : 'Failed to update MCP config';
        });
        return null;
      }
    },

    deleteMcpConfig: async (id: string) => {
      try {
        await client.deleteMcpConfig(id);
        set((state: any) => {
          state.mcpConfigs = state.mcpConfigs.filter((config: any) => config.id !== id);
        });
      } catch (error) {
        console.error('Failed to delete MCP config:', error);
        set((state: any) => {
          state.error = error instanceof Error ? error.message : 'Failed to delete MCP config';
        });
      }
    },
  };
}