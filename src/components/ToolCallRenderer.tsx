import React, { useState } from 'react';
import { cn } from '../lib/utils';
import type { ToolCall, Message } from '../types';

interface ToolCallRendererProps {
  toolCall: ToolCall;
  allMessages?: Message[];
  className?: string;
}

export const ToolCallRenderer: React.FC<ToolCallRendererProps> = ({
  toolCall,
  allMessages = [],
  className,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showArguments, setShowArguments] = useState(false);
  const [showResult, setShowResult] = useState(false);

  // 查找对应的tool角色消息作为结果
  const toolResultMessage = allMessages.find(msg => 
    msg.role === 'tool' && 
    ((msg as any).toolCallId === toolCall.id || (msg as any).tool_call_id === toolCall.id)
  );
  
  // 优先使用tool消息的内容，其次使用toolCall.result
  const resultContent = toolResultMessage?.content || toolCall.result;
  
  // 获取AI生成的总结
  const resultSummary = toolResultMessage?.summary || toolResultMessage?.metadata?.summary;
  
  const hasError = !!toolCall.error;
  const hasResult = !!resultContent;
  const hasArguments = toolCall.arguments && Object.keys(toolCall.arguments).length > 0;

  const formatJson = (obj: any) => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj);
    }
  };

  return (
    <div className={cn(
      'border rounded-lg p-3 bg-muted/50',
      hasError && 'border-destructive bg-destructive/5',
      className
    )}>
      {/* 工具调用头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-sm font-medium">
              Tool: {toolCall.name}
            </span>
          </div>
          
          {hasError && (
            <span className="inline-flex items-center gap-1 text-xs text-destructive bg-destructive/10 px-2 py-0.5 rounded">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Error
            </span>
          )}
          
          {hasResult && !hasError && (
            <span className="inline-flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Success
            </span>
          )}
        </div>
        
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 hover:bg-muted rounded transition-colors"
          title={isExpanded ? 'Collapse' : 'Expand'}
        >
          <svg 
            className={cn('w-4 h-4 transition-transform', isExpanded && 'rotate-180')} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* 展开的详细信息 */}
      {isExpanded && (
        <div className="mt-3 space-y-3">
          {/* 参数 */}
          {hasArguments && (
            <div>
              <button
                onClick={() => setShowArguments(!showArguments)}
                className="flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                <svg 
                  className={cn('w-3 h-3 transition-transform', showArguments && 'rotate-90')} 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                Arguments
              </button>
              
              {showArguments && (
                <pre className="mt-2 p-2 bg-background border rounded text-xs overflow-x-auto">
                  <code>{formatJson(toolCall.arguments)}</code>
                </pre>
              )}
            </div>
          )}

          {/* 结果 */}
          {hasResult && (
            <div>
              {/* 如果有AI总结，优先显示总结 */}
              {resultSummary ? (
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">AI Summary</div>
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                    {resultSummary}
                  </div>
                  
                  {/* 查看完整结果的按钮 */}
                  <button
                    onClick={() => setShowResult(!showResult)}
                    className="flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <svg 
                      className={cn('w-3 h-3 transition-transform', showResult && 'rotate-90')} 
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    {showResult ? 'Hide Full Result' : 'Show Full Result'}
                  </button>
                  
                  {showResult && (
                    <pre className="mt-2 p-2 bg-background border rounded text-xs overflow-x-auto">
                      <code>{resultContent}</code>
                    </pre>
                  )}
                </div>
              ) : (
                /* 没有总结时的原始显示方式 */
                <div>
                  <button
                    onClick={() => setShowResult(!showResult)}
                    className="flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <svg 
                      className={cn('w-3 h-3 transition-transform', showResult && 'rotate-90')} 
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    Result
                  </button>
                  
                  {showResult && (
                    <pre className="mt-2 p-2 bg-background border rounded text-xs overflow-x-auto">
                      <code>{resultContent}</code>
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 错误信息 */}
          {hasError && (
            <div>
              <div className="text-sm font-medium text-destructive mb-2">Error</div>
              <div className="p-2 bg-destructive/5 border border-destructive/20 rounded text-sm text-destructive">
                {toolCall.error}
              </div>
            </div>
          )}

          {/* 时间戳 */}
          <div className="text-xs text-muted-foreground">
            Executed at: {(() => {
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