import React, { useState } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import { AttachmentRenderer } from './AttachmentRenderer';
import { ToolCallRenderer } from './ToolCallRenderer';
import { cn, formatTime } from '../lib/utils';
import type { Message, Attachment } from '../types';

interface MessageItemProps {
  message: Message;
  isLast?: boolean;
  isStreaming?: boolean;
  onEdit?: (messageId: string, content: string) => void;
  onDelete?: (messageId: string) => void;
  customRenderer?: {
    renderMessage?: (message: Message) => React.ReactNode;
    renderAttachment?: (attachment: Attachment) => React.ReactNode;
  };
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  isLast = false,
  isStreaming = false,
  onEdit,
  onDelete,
  customRenderer,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [showActions, setShowActions] = useState(false);

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isSystem = message.role === 'system';

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
  const toolCalls = message.metadata?.toolCalls || [];

  return (
    <div
      className={cn(
        'group relative flex gap-3 px-4 py-4 rounded-lg transition-colors',
        isUser && 'bg-user-message ml-12',
        isAssistant && 'bg-assistant-message mr-12',
        isSystem && 'bg-muted mx-12 border-l-4 border-primary',
        'hover:bg-opacity-80'
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* 头像 */}
      <div className="flex-shrink-0">
        <div className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
          isUser && 'bg-primary text-primary-foreground',
          isAssistant && 'bg-secondary text-secondary-foreground',
          isSystem && 'bg-muted text-muted-foreground'
        )}>
          {isUser ? 'U' : isAssistant ? 'AI' : 'S'}
        </div>
      </div>

      {/* 消息内容 */}
      <div className="flex-1 min-w-0">
        {/* 消息头部 */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium">
            {isUser ? 'You' : isAssistant ? 'Assistant' : 'System'}
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
            {/* 始终保持内容在前，工具调用在后的顺序 */}
            {(() => {
              const hasContent = message.content && message.content.trim().length > 0;
              const hasToolCalls = toolCalls && toolCalls.length > 0;
              const isCurrentlyStreaming = isStreaming && isLast;
              
              // 如果没有工具调用，直接渲染内容
              if (!hasToolCalls) {
                return hasContent ? (
                  <div className="prose prose-sm max-w-none">
                    <MarkdownRenderer
                      content={message.content}
                      isStreaming={isCurrentlyStreaming}
                    />
                  </div>
                ) : null;
              }
              
              // 有工具调用时，需要按时间顺序渲染，并分割内容
               const renderItems: Array<{
                 type: 'content';
                 content: string;
                 timestamp: Date;
               } | {
                 type: 'tool';
                 toolCall: any;
                 timestamp: Date;
               }> = [];
               
               // 按工具调用的位置分割内容
               const sortedToolCalls = [...toolCalls].sort((a, b) => {
                 const posA = a.contentPositionBefore || 0;
                 const posB = b.contentPositionBefore || 0;
                 return posA - posB;
               });
               
               let lastPosition = 0;
               
               sortedToolCalls.forEach((toolCall, index) => {
                 const position = toolCall.contentPositionBefore || 0;
                 
                 // 添加工具调用前的内容片段
                 if (position > lastPosition) {
                   const contentSegment = message.content.slice(lastPosition, position);
                   if (contentSegment.trim()) {
                     renderItems.push({
                       type: 'content',
                       content: contentSegment,
                       timestamp: new Date(message.createdAt.getTime() + lastPosition) // 使用位置作为时间偏移
                     });
                   }
                 }
                 
                 // 添加工具调用
                 renderItems.push({
                   type: 'tool',
                   toolCall,
                   timestamp: toolCall.createdAt || message.createdAt
                 });
                 
                 lastPosition = position;
               });
               
               // 添加最后一个工具调用后的内容
               if (lastPosition < message.content.length) {
                 const remainingContent = message.content.slice(lastPosition);
                 if (remainingContent.trim()) {
                   renderItems.push({
                     type: 'content',
                     content: remainingContent,
                     timestamp: new Date(message.createdAt.getTime() + lastPosition + 1000) // 确保在工具调用之后
                   });
                 }
               }
               
               // 如果没有工具调用但有内容，直接添加全部内容
               if (renderItems.length === 0 && hasContent) {
                 renderItems.push({
                   type: 'content',
                   content: message.content,
                   timestamp: message.createdAt
                 });
               }
              
              // 按时间戳排序
              renderItems.sort((a, b) => {
                const timeA = new Date(a.timestamp).getTime();
                const timeB = new Date(b.timestamp).getTime();
                return timeA - timeB;
              });
              
              return (
                <div className="space-y-3">
                  {renderItems.map((item, index) => {
                    if (item.type === 'content') {
                      return (
                        <div key={`content-${index}`} className="prose prose-sm max-w-none">
                          <MarkdownRenderer
                            content={item.content}
                            isStreaming={isCurrentlyStreaming && index === renderItems.length - 1}
                          />
                        </div>
                      );
                    } else {
                      return (
                        <div key={`tool-${item.toolCall.id}`}>
                          <ToolCallRenderer
                            toolCall={item.toolCall}
                          />
                        </div>
                      );
                    }
                  })}
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

export default MessageItem;