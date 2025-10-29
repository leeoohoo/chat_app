import React, { useState, memo } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import { AttachmentRenderer } from './AttachmentRenderer';
import { ToolCallRenderer } from './ToolCallRenderer';
import { cn, formatTime } from '../lib/utils';
import type { Message, Attachment } from '../types';

// 工具调用数据转换函数
const convertToolCallData = (tc: any) => {
  return {
    id: tc.id || tc.tool_call_id || `tool_${Date.now()}_${Math.random()}`,
    messageId: tc.messageId || '',
    name: tc.function?.name || tc.name || 'unknown_tool',
    arguments: tc.function?.arguments || tc.arguments || '{}',
    result: tc.result || '',
    error: tc.error || undefined,
    createdAt: tc.createdAt || tc.created_at || new Date()
  };
};

interface MessageItemProps {
  message: Message;
  isLast?: boolean;
  isStreaming?: boolean;
  onEdit?: (messageId: string, content: string) => void;
  onDelete?: (messageId: string) => void;
  allMessages?: Message[]; // 添加所有消息的引用
  customRenderer?: {
    renderMessage?: (message: Message) => React.ReactNode;
    renderAttachment?: (attachment: Attachment) => React.ReactNode;
  };
}

const MessageItemComponent: React.FC<MessageItemProps> = ({
  message,
  isLast = false,
  isStreaming = false,
  onEdit,
  onDelete,
  allMessages = [],
  customRenderer,
}) => {
  console.log('🚀🚀🚀 MessageItem 组件被调用！消息ID:', message.id, '角色:', message.role);
  console.log('🚀🚀🚀 完整消息对象:', message);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);

  // 处理代码应用
  const handleApplyCode = (code: string, language: string) => {
    // 复制代码到剪贴板
    navigator.clipboard.writeText(code).then(() => {
      console.log('代码已复制到剪贴板:', { code, language });
    }).catch(err => {
      console.error('复制失败:', err);
    });
  };
  const [showActions, setShowActions] = useState(false);

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isSystem = message.role === 'system';
  const isTool = message.role === 'tool';

  // 隐藏tool角色的消息，因为它们应该作为工具调用的结果显示
  if (isTool) {
    return null;
  }

  // 使用自定义渲染器
  if (customRenderer?.renderMessage) {
    return <div>{customRenderer.renderMessage(message)}</div>;
  }

  const handleEdit = () => {
    if (onEdit && editContent.trim() !== message.content) {
      onEdit(message.id, editContent.trim());
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditContent(message.content);
    setIsEditing(false);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
    } catch (error) {
      console.error('Failed to copy message:', error);
    }
  };

  const attachments = message.metadata?.attachments || [];
  // 获取工具调用数据 - 优先使用metadata.toolCalls，这是通过WebSocket流式传输存储的数据
  const toolCalls = message.metadata?.toolCalls || [];
  
  console.log('🔧 工具调用数据:', {
        'metadata.toolCalls': message.metadata?.toolCalls,
        'toolCalls长度': toolCalls.length,
        '消息ID': message.id,
        'contentSegments': message.metadata?.contentSegments,
        'contentSegments长度': message.metadata?.contentSegments?.length || 0
    });

  return (
    <div
      className={cn(
        'group relative rounded-lg transition-colors',
        // 基础布局样式 - 所有消息都使用统一的左对齐布局
        !isAssistant && 'flex gap-3 px-4 py-4',
        // assistant消息使用简化布局（无头像无头部）
        isAssistant && 'px-4 py-2',
        // 角色特定样式 - 移除左右对齐差异，统一左对齐
        isUser && 'bg-user-message',
        isSystem && 'bg-muted border-l-4 border-primary',
        isTool && 'bg-blue-50 dark:bg-blue-950/20 border-l-4 border-blue-500',
        'hover:bg-opacity-80'
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* 头像 - assistant消息不显示头像 */}
      {!isAssistant && (
        <div className="flex-shrink-0">
          <div className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
            isUser && 'bg-primary text-primary-foreground',
            isSystem && 'bg-muted text-muted-foreground',
            isTool && 'bg-blue-500 text-white'
          )}>
            {isUser ? 'U' : isTool ? 'T' : 'S'}
          </div>
        </div>
      )}

      {/* 消息内容 */}
      <div className="flex-1 min-w-0">
        {/* 消息头部 - assistant消息不显示头部 */}
        {!isAssistant && (
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium">
              {isUser ? 'You' : isTool ? 'Tool Result' : 'System'}
            </span>
            <span className="text-xs text-muted-foreground">
              {formatTime(message.createdAt)}
            </span>
            {message.metadata?.model && (
              <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                {message.metadata.model}
              </span>
            )}
          </div>
        )}

        {/* 附件 */}
        {attachments.length > 0 && (
          <div className="mb-3 space-y-2">
            {attachments.map((attachment) => (
              <AttachmentRenderer
                key={attachment.id}
                attachment={attachment}
                customRenderer={customRenderer?.renderAttachment}
              />
            ))}
          </div>
        )}

        {/* 动态渲染消息内容和工具调用 */}
        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full p-2 border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary"
              rows={3}
              autoFocus
            />
            <div className="flex gap-2">
              <button
                onClick={handleEdit}
                className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90"
              >
                Save
              </button>
              <button
                onClick={handleCancelEdit}
                className="px-3 py-1 text-sm bg-muted text-muted-foreground rounded hover:bg-muted/80"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {/* 使用新的内容分段渲染机制 */}
            {(() => {
              const contentSegments = message.metadata?.contentSegments || [];
              const hasContent = message.content && message.content.trim().length > 0;
              const isCurrentlyStreaming = isStreaming && isLast;
              
              // 如果有内容分段，使用分段渲染
              if (contentSegments.length > 0) {
                console.log('🎨 使用分段渲染，分段数量:', contentSegments.length);
                console.log('🎨 分段详情:', contentSegments);
                return (
                  <div className="space-y-0.5">
                    {contentSegments.map((segment, index) => {
                       console.log(`🎨 渲染分段 ${index}:`, segment);
                       if (segment.type === 'text') {
                         console.log(`🎨 渲染文本分段 ${index}:`, segment.content);
                         return (
                           <div key={`segment-${index}`} className="prose prose-sm max-w-none">
                             <MarkdownRenderer
                               content={segment.content as string}
                               isStreaming={isCurrentlyStreaming && index === contentSegments.length - 1}
                               onApplyCode={handleApplyCode}
                             />
                           </div>
                         );
                       } else if (segment.type === 'tool_call') {
                         console.log(`🎨 渲染工具调用分段 ${index}:`, segment);
                         // 根据toolCallId查找对应的工具调用
                         const toolCall = toolCalls.find(tc => tc.id === segment.toolCallId);
                         console.log(`🎨 查找工具调用 ${segment.toolCallId}:`, toolCall);
                         if (toolCall) {
                           console.log(`🎨 找到工具调用，开始渲染:`, toolCall);
                           return (
                             <div key={`tool-${toolCall.id}`}>
                               <ToolCallRenderer
                                 toolCall={toolCall}
                                 allMessages={allMessages}
                               />
                             </div>
                           );
                         } else {
                           console.log(`🎨 ❌ 未找到工具调用 ${segment.toolCallId}`);
                         }
                       }
                       return null;
                     })}
                  </div>
                );
              }
              
              // 回退到传统渲染方式（向后兼容）
              console.log('🎨 使用传统渲染方式');
              console.log('🎨 hasContent:', hasContent);
              console.log('🎨 toolCalls.length:', toolCalls.length);
              return (
                <div className="space-y-0.5">
                  {/* 渲染文本内容 */}
                  {hasContent && (
                    <div className="prose prose-sm max-w-none">
                      <MarkdownRenderer
                        content={message.content}
                        isStreaming={isCurrentlyStreaming}
                        onApplyCode={handleApplyCode}
                      />
                    </div>
                  )}
                  
                  {/* 渲染工具调用（历史消息兼容） - 修复：确保工具调用总是被渲染 */}
                  {toolCalls.length > 0 && (
                    <div className="space-y-0.5">
                      <div className="text-sm text-muted-foreground font-medium">工具调用:</div>
                      {toolCalls.map((toolCall) => {
                         console.log('🎨 传统方式渲染工具调用:', toolCall);
                         return (
                           <div key={`tool-${toolCall.id}`}>
                             <ToolCallRenderer
                               toolCall={toolCall}
                               allMessages={allMessages}
                             />
                           </div>
                         );
                       })}
                     </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}

        {/* Token使用信息 */}
        {message.tokensUsed && (
          <div className="mt-2 text-xs text-muted-foreground">
            Tokens used: {message.tokensUsed}
          </div>
        )}
      </div>

      {/* 操作按钮 */}
      {showActions && !isEditing && (
        <div className="absolute top-2 right-2 flex gap-1 bg-background border rounded-md shadow-sm opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={handleCopy}
            className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
            title="Copy message"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </button>
          
          {isUser && onEdit && (
            <button
              onClick={() => setIsEditing(true)}
              className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
              title="Edit message"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          )}
          
          {onDelete && (
            <button
              onClick={() => onDelete(message.id)}
              className="p-1.5 hover:bg-destructive/10 rounded text-muted-foreground hover:text-destructive transition-colors"
              title="Delete message"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// 使用memo优化性能，只在关键props变化时重新渲染
export const MessageItem = memo(MessageItemComponent, (prevProps, nextProps) => {
  // 比较关键属性
  return (
    prevProps.message.id === nextProps.message.id &&
    prevProps.message.content === nextProps.message.content &&
    prevProps.message.createdAt === nextProps.message.createdAt &&
    prevProps.isLast === nextProps.isLast &&
    prevProps.isStreaming === nextProps.isStreaming &&
    JSON.stringify(prevProps.message.metadata) === JSON.stringify(nextProps.message.metadata)
  );
});

export default MessageItem;