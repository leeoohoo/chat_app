import React, { useState } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import type { ToolCall, Message } from '../types';
import './ToolCallRenderer.css';

interface ToolCallRendererProps {
  toolCall: ToolCall;
  allMessages?: Message[];
  className?: string;
}

export const ToolCallRenderer: React.FC<ToolCallRendererProps> = ({
  toolCall,
  allMessages = [],
  className: _className,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  // 查找对应的tool角色消息作为结果
  const toolResultMessage = allMessages.find(msg => 
    msg.role === 'tool' && 
    ((msg as any).toolCallId === toolCall.id || (msg as any).tool_call_id === toolCall.id)
  );
  
  // 优先使用tool消息的内容，其次使用toolCall.result
  const resultContent = toolResultMessage?.content || toolCall.result;
  
  const hasError = !!toolCall.error;
  const hasResult = !!resultContent;
  
  // 解析参数 - 处理字符串和对象两种格式
  const parseArguments = () => {
    if (!toolCall.arguments) return {};
    
    // 如果已经是对象，直接返回
    if (typeof toolCall.arguments === 'object') {
      return toolCall.arguments;
    }
    
    // 如果是字符串，尝试解析为 JSON
    if (typeof toolCall.arguments === 'string') {
      try {
        return JSON.parse(toolCall.arguments);
      } catch (e) {
        console.warn('Failed to parse tool arguments:', toolCall.arguments, e);
        return {};
      }
    }
    
    return {};
  };
  
  const parsedArguments = parseArguments();
  const hasArguments = parsedArguments && Object.keys(parsedArguments).length > 0;

  // 格式化参数为对话内容
  const formatArgumentsAsMessage = () => {
    if (!hasArguments) return '';
    
    const argKeys = Object.keys(parsedArguments);
    
    // 如果只有一个参数，直接显示其内容
    if (argKeys.length === 1) {
      const value = parsedArguments[argKeys[0]];
      return typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    }
    
    // 如果有多个参数，用表格形式显示
    let tableContent = '| 参数 | 值 |\n|------|------|\n';
    argKeys.forEach(key => {
      const value = parsedArguments[key];
      const formattedValue = typeof value === 'string' 
        ? value.replace(/\n/g, '<br>').replace(/\|/g, '\\|')
        : JSON.stringify(value).replace(/\|/g, '\\|');
      tableContent += `| ${key} | ${formattedValue} |\n`;
    });
    
    return tableContent;
  };

  const argumentsMessage = formatArgumentsAsMessage();

  return (
    <div className="tool-call-renderer tool-call-container">
      <div className="tool-header">
        <span className="tool-name">
          @{toolCall.name}
        </span>
        {hasError && (
          <span className="status-badge status-error">
            错误
          </span>
        )}
        
        {hasResult && !hasError && (
          <span className="status-badge status-success">
            完成
          </span>
        )}
        
        {(hasArguments || hasResult || hasError) && (
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="toggle-button"
          >
            {showDetails ? '收起详情' : '查看详情'}
          </button>
        )}
      </div>

      {/* 参数内容 - 只在有参数时显示 */}
      {hasArguments && argumentsMessage && (
        <div className="border-l-4 border-blue-400 dark:border-blue-500 rounded-lg overflow-hidden bg-blue-50/50 dark:bg-blue-900/20">
          <MarkdownRenderer 
            content={argumentsMessage} 
            className="p-3"
          />
        </div>
      )}

      {/* 详细信息 - 展开时显示 */}
      {showDetails && (
         <div className="details-container">
         

          {/* 结果 */}
          {hasResult && (
            <MarkdownRenderer content={toolCall.result || ''} />
          )}

          {/* 错误 */}
          {hasError && (
            <div>
              <div className="details-title">错误:</div>
              <div className="status-badge status-error" style={{display: 'block', padding: '0.5rem'}}>
                {toolCall.error}
              </div>
            </div>
          )}

          {/* 时间戳 */}
          <div className="text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700 pt-2">
            执行时间: {(() => {
              const date = new Date(toolCall.createdAt);
              return isNaN(date.getTime()) ? '时间未知' : date.toLocaleString();
            })()}
          </div>
        </div>
      )}
    </div>
  );
};

export default ToolCallRenderer;