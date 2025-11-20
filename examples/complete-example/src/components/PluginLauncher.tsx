import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { AiChat } from '@leeoohoo/aichat';

export type ChatPlugin = {
  id: string;
  name: string;
  icon?: React.ReactNode;
  render: (ctx: { aiChat: AiChat }) => React.ReactNode;
};

interface Props {
  aiChat: AiChat | null;
  plugins: ChatPlugin[];
}

/**
 * 头部插件入口（注入到 ThemeToggle 左侧）+ 悬浮菜单 + 插件弹窗
 */
export const PluginLauncher: React.FC<Props> = ({ aiChat, plugins }) => {
  const [pluginMenuOpen, setPluginMenuOpen] = useState(false);
  const [pluginModalOpen, setPluginModalOpen] = useState(false);
  const [activePluginId, setActivePluginId] = useState<string | null>(null);
  const activePlugin = plugins.find(p => p.id === activePluginId) || null;

  const pluginBtnRef = useRef<HTMLButtonElement | null>(null);
  const pluginMenuRef = useRef<HTMLDivElement | null>(null);
  const [pluginHost, setPluginHost] = useState<HTMLElement | null>(null);
  const [menuPos, setMenuPos] = useState<{ top: number; left: number } | null>(null);
  const MENU_WIDTH = 288;
  const [menuEntered, setMenuEntered] = useState(false);

  // 按钮宿主：插入到 ThemeToggle 按钮左侧
  useEffect(() => {
    if (!aiChat) return;
    const candidates = [
      'button[aria-label*="mode"]',
      'button[aria-label*="Mode"]',
      'button[aria-label*="theme"]',
      'button[title*="mode"]',
      'button[title*="Mode"]',
      'button[title*="theme"]',
    ];
    let themeBtn: HTMLElement | null = null;
    for (const sel of candidates) {
      const el = document.querySelector(sel) as HTMLElement | null;
      if (el) { themeBtn = el; break; }
    }
    if (!themeBtn) return;
    let host = document.getElementById('aichat-plugin-host') as HTMLElement | null;
    if (!host) {
      host = document.createElement('div');
      host.id = 'aichat-plugin-host';
      host.style.display = 'inline-flex';
      host.style.alignItems = 'center';
      host.style.marginRight = '12px';
      themeBtn.parentElement?.insertBefore(host, themeBtn);
    }
    setPluginHost(host);
  }, [aiChat, plugins.length]);

  // 菜单定位：右对齐按钮
  useEffect(() => {
    if (pluginMenuOpen && pluginBtnRef.current) {
      const rect = pluginBtnRef.current.getBoundingClientRect();
      const vw = window.innerWidth;
      const left = Math.min(
        Math.max(Math.round(rect.right - MENU_WIDTH), 12),
        vw - MENU_WIDTH - 12
      );
      const top = Math.round(rect.bottom + 8);
      setMenuPos({ top, left });
    }
  }, [pluginMenuOpen]);

  // 菜单淡入动画
  useEffect(() => {
    if (pluginMenuOpen) {
      setMenuEntered(false);
      const id = window.requestAnimationFrame(() => setMenuEntered(true));
      return () => window.cancelAnimationFrame(id);
    } else {
      setMenuEntered(false);
    }
  }, [pluginMenuOpen]);

  // 外点关闭
  useEffect(() => {
    if (!pluginMenuOpen) return;
    const onDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (pluginMenuRef.current && pluginMenuRef.current.contains(target)) return;
      if (pluginBtnRef.current && pluginBtnRef.current.contains(target as Node)) return;
      setPluginMenuOpen(false);
    };
    window.addEventListener('mousedown', onDown);
    return () => window.removeEventListener('mousedown', onDown);
  }, [pluginMenuOpen]);

  // ESC 关闭（优先关闭弹窗）
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (pluginModalOpen) setPluginModalOpen(false);
        else if (pluginMenuOpen) setPluginMenuOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [pluginModalOpen, pluginMenuOpen]);

  if (!aiChat) return null;

  return (
    <>
      {/* Header 内的插件按钮（Portal 注入到主题按钮左侧） */}
      {pluginHost && createPortal(
        <button
          ref={pluginBtnRef}
          className="p-2 hover:bg-muted rounded-lg transition-colors"
          onClick={() => setPluginMenuOpen(v => !v)}
          title="插件"
          aria-label="插件"
          aria-haspopup="menu"
          aria-expanded={pluginMenuOpen}
        >
          {/* 2x2 grid icon（与 ThemeToggle 风格统一） */}
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 4H5a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V5a1 1 0 00-1-1zm10 0h-4a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V5a1 1 0 00-1-1zM9 14H5a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1v-4a1 1 0 00-1-1zm10 0h-4a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1v-4a1 1 0 00-1-1z" />
          </svg>
        </button>,
        pluginHost
      )}

      {/* 插件菜单浮层 */}
      {pluginMenuOpen && menuPos && createPortal((
        <div
          ref={pluginMenuRef}
          className={`fixed bg-card border border-border rounded-lg py-2 transform transition-all duration-150 ease-out ${menuEntered ? 'opacity-100 translate-y-0 shadow-2xl' : 'opacity-0 -translate-y-1 shadow-lg'}`}
          style={{ top: `${menuPos.top}px`, left: `${menuPos.left}px`, width: `${MENU_WIDTH}px`, zIndex: 10000 }}
          role="menu"
        >
          <div className="absolute -top-2 right-6 w-3 h-3 bg-card rotate-45 border-t border-l border-border"></div>

          <div className="px-3 pb-2 border-b border-border flex items-center justify-between">
            <div className="text-xs font-medium text-foreground">插件</div>
            <div className="text-[11px] text-muted-foreground">{plugins.length}</div>
          </div>

          <div className="max-h-72 overflow-auto">
            {plugins.length === 0 && (
              <div className="px-3 py-3 text-xs text-muted-foreground">暂无可用插件</div>
            )}
            {plugins.map((p) => (
              <button
                key={p.id}
                className="w-full text-left px-3 py-2 text-sm hover:bg-muted flex items-center gap-2"
                onClick={() => { setActivePluginId(p.id); setPluginMenuOpen(false); setPluginModalOpen(true); }}
                role="menuitem"
              >
                <span className="inline-flex items-center justify-center w-6 h-6 bg-muted rounded text-[11px] text-foreground">
                  {p.icon ? p.icon : (p.name?.[0] ?? 'P')}
                </span>
                <span className="text-foreground truncate">{p.name}</span>
              </button>
            ))}
          </div>
        </div>
      ), document.body)}

      {/* 插件弹窗（MCP 放大版）*/}
      {pluginModalOpen && activePlugin && createPortal((
        <div className="fixed inset-0" style={{ zIndex: 10001 }}>
          <div className="absolute inset-0 bg-black/45" onClick={() => setPluginModalOpen(false)} />
          <div
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card border border-border rounded-lg shadow-2xl flex flex-col"
            style={{
              width: `min(98vw, ${activePlugin.id === 'mcp-manager-plugin' ? 1280 : 1100}px)`,
              height: `min(94vh, ${activePlugin.id === 'mcp-manager-plugin' ? 900 : 820}px)`,
            }}
          >
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <div className="font-medium text-foreground text-sm">{activePlugin.name}</div>
              <button className="text-muted-foreground hover:text-foreground" onClick={() => setPluginModalOpen(false)}>
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {activePlugin.render({ aiChat })}
            </div>
          </div>
        </div>
      ), document.body)}
    </>
  );
};

export default PluginLauncher;
