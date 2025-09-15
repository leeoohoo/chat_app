import React, { useState, useEffect } from 'react';
import { useChatStore } from '../lib/store';

// 文档图标组件
const DocumentIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

// 关闭图标组件
const XMarkIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

// 保存图标组件
const SaveIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
  </svg>
);

interface SystemContextEditorProps {
  onClose?: () => void;
}

const SystemContextEditor: React.FC<SystemContextEditorProps> = ({ onClose }) => {
  const { systemContext, updateSystemContext, loadSystemContext } = useChatStore();
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // 组件初始化时加载系统上下文
  useEffect(() => {
    const loadContent = async () => {
      console.log('SystemContextEditor: Starting to load system context');
      setIsLoading(true);
      try {
        await loadSystemContext();
        console.log('SystemContextEditor: System context loaded successfully');
      } catch (error) {
        console.error('SystemContextEditor: Failed to load system context:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadContent();
  }, []); // 移除loadSystemContext依赖，避免无限循环

  // 当 systemContext 更新时同步到本地状态
  useEffect(() => {
    setContent(systemContext || '');
  }, [systemContext]);

  // 保存系统上下文
  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateSystemContext(content);
      onClose?.();
    } catch (error) {
      console.error('Failed to save system context:', error);
      alert('保存失败，请重试');
    } finally {
      setIsSaving(false);
    }
  };

  // 处理键盘快捷键
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      handleSave();
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <DocumentIcon />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              系统上下文设置
            </h2>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <SaveIcon />
              <span>{isSaving ? '保存中...' : '保存'}</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <XMarkIcon />
            </button>
          </div>
        </div>

        {/* 内容区域 */}
        <div className="p-6 overflow-hidden flex flex-col" style={{ height: 'calc(90vh - 120px)' }}>
          {/* 说明文字 */}
          <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              <strong>系统上下文</strong>将作为每次对话的系统提示词，支持 Markdown 格式。
              您可以在这里设置 AI 的角色、行为规范、回答风格等。
            </p>
            <p className="text-xs text-blue-600 dark:text-blue-300 mt-2">
              提示：使用 Ctrl+S 快速保存
            </p>
          </div>

          {/* 编辑器 */}
          <div className="flex-1 flex flex-col">
            <div className="mb-2 flex items-center justify-between">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Markdown 内容
              </label>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {content.length} 字符
              </div>
            </div>
            
            {isLoading ? (
              <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-300 dark:border-gray-600">
                <div className="text-gray-500 dark:text-gray-400">加载中...</div>
              </div>
            ) : (
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1 w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white resize-none font-mono text-sm"
                placeholder="请输入系统上下文内容，支持 Markdown 格式...\n\n例如：\n# AI 助手角色设定\n\n你是一个专业的编程助手，具有以下特点：\n- 提供准确、简洁的代码解决方案\n- 遵循最佳实践和代码规范\n- 耐心解答技术问题\n\n## 回答风格\n- 使用中文回答\n- 代码示例要完整可运行\n- 提供必要的解释说明"
                spellCheck={false}
              />
            )}
          </div>

          {/* 底部提示 */}
          <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
            <p>• 支持标准 Markdown 语法：标题、列表、代码块、链接等</p>
            <p>• 内容将在每次对话开始时自动发送给 AI</p>
            <p>• 留空则使用默认系统提示词</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemContextEditor;