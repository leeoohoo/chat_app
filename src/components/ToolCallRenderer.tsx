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
  console.log('🔍 ToolCallRenderer - 开始查找工具结果消息');
  console.log('🔍 当前工具调用ID:', toolCall.id);
  console.log('🔍 所有消息数量:', allMessages.length);
  console.log('🔍 所有消息:', allMessages.map(msg => ({
    id: msg.id,
    role: msg.role,
    tool_call_id: (msg as any).tool_call_id || (msg as any).toolCallId,
    metadata: msg.metadata,
    content: msg.content?.substring(0, 100) + '...'
  })));

  const toolResultMessage = allMessages.find(msg => {
    if (msg.role !== 'tool') return false;
    // 同时检查顶层和metadata中的tool_call_id（兼容不同格式）
    const topLevelId = (msg as any).tool_call_id || (msg as any).toolCallId;
    const metadataId = msg.metadata?.tool_call_id || msg.metadata?.toolCallId;
    return topLevelId === toolCall.id || metadataId === toolCall.id;
  });

  console.log('🔍 找到的工具结果消息:', toolResultMessage);
  console.log('🎨 ToolCallRenderer - 工具调用:', toolCall.id, '结果:', toolCall.result, '工具消息:', toolResultMessage?.content);

  // 优先使用toolCall.result，如果没有则使用tool消息的内容
  const result = toolCall.result || toolResultMessage?.content;
  
  const hasError = !!toolCall.error;
  const hasResult = !!result;
  
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

  // 递归平铺对象属性
  const flattenObject = (obj: any, prefix: string = ''): Record<string, any> => {
    const flattened: Record<string, any> = {};
    
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        const value = obj[key];
        const newKey = prefix ? `${prefix}.${key}` : key;
        
        if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
          // 如果是对象，递归平铺
          Object.assign(flattened, flattenObject(value, newKey));
        } else {
          // 如果是基本类型或数组，直接添加
          flattened[newKey] = value;
        }
      }
    }
    
    return flattened;
  };

  // 递归平铺对象属性（包含数组索引）用于结果渲染
  const flattenObjectWithArrays = (obj: any, prefix: string = ''): Record<string, any> => {
    const flattened: Record<string, any> = {};

    const isPlainObject = (val: any) => val !== null && typeof val === 'object' && !Array.isArray(val);

    if (Array.isArray(obj)) {
      obj.forEach((item, index) => {
        const arrayKey = `${prefix}[${index}]`;
        if (isPlainObject(item)) {
          Object.assign(flattened, flattenObjectWithArrays(item, arrayKey));
        } else if (Array.isArray(item)) {
          Object.assign(flattened, flattenObjectWithArrays(item, arrayKey));
        } else {
          flattened[arrayKey] = item;
        }
      });
      return flattened;
    }

    if (isPlainObject(obj)) {
      for (const key in obj) {
        if (!obj.hasOwnProperty(key)) continue;
        const value = obj[key];
        const newKey = prefix ? `${prefix}.${key}` : key;
        if (Array.isArray(value)) {
          Object.assign(flattened, flattenObjectWithArrays(value, newKey));
        } else if (isPlainObject(value)) {
          Object.assign(flattened, flattenObjectWithArrays(value, newKey));
        } else {
          flattened[newKey] = value;
        }
      }
      return flattened;
    }

    // 基本类型直接返回
    if (prefix) {
      flattened[prefix] = obj;
    }
    return flattened;
  };

  // 格式化参数为对话内容
  const formatArgumentsAsMessage = () => {
    if (!hasArguments) return '';
    
    // 平铺所有参数
    const flattenedArgs = flattenObject(parsedArguments);
    const argKeys = Object.keys(flattenedArgs);
    
    // 统一使用表格形式显示所有参数（包括单个参数）
    let tableContent = '| 参数 | 值 |\n|------|------|\n';
    argKeys.forEach(key => {
      const value = flattenedArgs[key];
      let formattedValue: string;
      
      if (typeof value === 'string') {
        formattedValue = value.replace(/\n/g, '<br>').replace(/\|/g, '\\|');
      } else if (Array.isArray(value)) {
        formattedValue = `[${value.join(', ')}]`.replace(/\|/g, '\\|');
      } else {
        formattedValue = JSON.stringify(value).replace(/\|/g, '\\|');
      }
      
      tableContent += `| ${key} | ${formattedValue} |\n`;
    });
    
    return tableContent;
  };

  const argumentsMessage = formatArgumentsAsMessage();

  // 解析结果 - 支持字符串与对象，检测是否为结构化JSON
  const parseResult = (): any | null => {
    if (!hasResult) return null;
    if (result && typeof result === 'object') {
      return result;
    }
    if (typeof result === 'string') {
      try {
        const parsed = JSON.parse(result);
        if (parsed && typeof parsed === 'object') {
          return parsed;
        }
      } catch (e) {
        // 非JSON字符串，按原文本渲染
        return null;
      }
    }
    return null;
  };

  const parsedResult = parseResult();
  const hasStructuredResult = !!(parsedResult && typeof parsedResult === 'object');

  // ===== 树形表格支持：根据 JSON 自动生成层级行 =====
  const inferType = (val: any): string => {
    if (val === null) return 'null';
    if (Array.isArray(val)) {
      if (val.length === 0) return 'array []';
      const first = val[0];
      const elemType = inferType(first);
      return elemType === 'object' ? 'object []' : `${elemType}[]`;
    }
    switch (typeof val) {
      case 'string': return 'string';
      case 'number': return Number.isInteger(val) ? 'integer' : 'number';
      case 'boolean': return 'boolean';
      case 'object': return 'object';
      default: return typeof val;
    }
  };

  interface TreeNode {
    path: string;
    name: string;
    type: string;
    value: any;
    children: TreeNode[];
  }

  const buildTreeNodes = (obj: any, name = '', path = ''): TreeNode[] => {
    const nodes: TreeNode[] = [];
    if (obj === null || obj === undefined) return nodes;

    if (Array.isArray(obj)) {
      const node: TreeNode = {
        path: path || name || 'list',
        name: name || 'list',
        type: inferType(obj),
        value: obj,
        children: obj.map((item, index) => {
          const itemPath = `${path || name || 'list'}[${index}]`;
          const itemType = inferType(item);
          return {
            path: itemPath,
            name: `[${index}]`,
            type: itemType,
            value: item,
            children: (itemType === 'object' || Array.isArray(item)) ? buildTreeNodes(item, `[${index}]`, itemPath) : []
          };
        })
      };
      nodes.push(node);
      return nodes;
    }

    if (typeof obj === 'object') {
      Object.keys(obj).forEach((key) => {
        const value = obj[key];
        const currentPath = path ? `${path}.${key}` : key;
        const t = inferType(value);
        const children = (t === 'object' || Array.isArray(value)) ? buildTreeNodes(value, key, currentPath) : [];
        nodes.push({
          path: currentPath,
          name: key,
          type: t,
          value,
          children,
        });
      });
    }

    return nodes;
  };

  const TreeTable: React.FC<{ data: any }> = ({ data }) => {
    const roots = Array.isArray(data) ? buildTreeNodes(data, 'list', 'list') : buildTreeNodes(data, '', '');
    const [expanded, setExpanded] = useState<Set<string>>(() => new Set(roots.filter(r => r.children.length > 0).map(r => r.path)));

    const toggleExpand = (p: string) => {
      setExpanded(prev => {
        const next = new Set(prev);
        if (next.has(p)) next.delete(p); else next.add(p);
        return next;
      });
    };

    const formatValue = (val: any): string => {
      if (val === null) return 'null';
      if (Array.isArray(val)) return `数组(${val.length})`;
      if (typeof val === 'object') return '对象';
      if (typeof val === 'string') return val;
      try { return JSON.stringify(val); } catch { return String(val); }
    };

    const renderNodes = (nodes: TreeNode[], depth: number): React.ReactNode => {
      return nodes.map((node) => {
        const hasChildren = node.children && node.children.length > 0;
        const isExpanded = expanded.has(node.path);
        const icon = hasChildren ? (isExpanded ? '▾' : '▸') : '';
        const valueText = hasChildren ? formatValue(node.value) : formatValue(node.value);
        return (
          <React.Fragment key={node.path}>
            <tr>
              <td style={{ paddingLeft: depth * 16 }}>
                {hasChildren ? (
                  <button
                    type="button"
                    onClick={() => toggleExpand(node.path)}
                    className="mr-2 text-gray-600 dark:text-gray-300 hover:text-black dark:hover:text-white"
                    aria-label={isExpanded ? '收起' : '展开'}
                  >
                    {icon}
                  </button>
                ) : (
                  <span className="mr-4" />
                )}
                {node.name}
              </td>
              <td style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>{valueText}</td>
            </tr>
            {hasChildren && isExpanded && renderNodes(node.children, depth + 1)}
          </React.Fragment>
        );
      });
    };

    return (
      <div className="border-l-4 border-green-400 dark:border-green-500 rounded-lg overflow-hidden bg-green-50/50 dark:bg-green-900/20 mb-2">
        <div className="markdown-renderer">
          <table>
            <thead>
              <tr>
                <th>字段</th>
                <th>值</th>
              </tr>
            </thead>
            <tbody>
              {renderNodes(roots, 0)}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // 移除未使用的表格格式化方法

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
        
        {!hasResult && !hasError && (
          <span className="status-badge status-pending">
            等待中
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

      {/* 详细信息 - 展开时显示 */}
      {showDetails && (
         <div className="details-container">
         
          {/* 参数详情 - 移动到详情里面，移除标题 */}
          {hasArguments && (
            <div>
              {/* 使用格式化的参数内容，而不是原始JSON */}
              {argumentsMessage && (
                <div className="border-l-4 border-blue-400 dark:border-blue-500 rounded-lg overflow-hidden bg-blue-50/50 dark:bg-blue-900/20 mb-4">
                  <MarkdownRenderer 
                    content={argumentsMessage} 
                  />
                </div>
              )}
            </div>
          )}

          {/* 结果 */}
          {hasResult && (
            <div>
              <div className="details-title">结果:</div>
              {hasStructuredResult ? (
                <TreeTable data={parsedResult} />
              ) : (
                <MarkdownRenderer content={typeof result === 'string' ? result : JSON.stringify(result)} />
              )}
            </div>
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