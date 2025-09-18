import React, { useMemo } from 'react';
import { cn } from '../lib/utils';

interface MarkdownRendererProps {
    content: string;
    isStreaming?: boolean;
    className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
                                                                      content,
                                                                      isStreaming = false,
                                                                      className,
                                                                  }) => {
    // 增强的Markdown渲染，支持代码高亮和数学公式
    const renderContent = useMemo(() => {
        return (text: string) => {
            let processedText = text;

            // 处理数学公式块 ($$...$$)
            const mathBlockRegex = /\$\$([\s\S]*?)\$\$/g;
            processedText = processedText.replace(mathBlockRegex, (_match, formula) => {
                return `<div class="math-block bg-muted/50 dark:bg-muted/70 p-3 rounded-md my-2 text-center font-mono text-sm border border-border">${formula.trim()}</div>`;
            });

            // 处理内联数学公式 ($...$)
            const mathInlineRegex = /\$([^$]+)\$/g;
            processedText = processedText.replace(mathInlineRegex, (_match, formula) => {
                return `<span class="math-inline bg-muted/30 dark:bg-muted/50 px-1 py-0.5 rounded font-mono text-sm">${formula}</span>`;
            });

            // 智能处理代码块，支持流式渲染时的未闭合代码块
            // 首先处理完整的代码块
            const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
            processedText = processedText.replace(codeBlockRegex, (_match, language, code) => {
                const lang = language || 'text';
                const highlightedCode = highlightCode(code.trim(), lang);
                return `<div class="code-block my-3 rounded-md border border-border overflow-hidden"><div class="code-header bg-gray-100 dark:bg-gray-800 px-3 py-2 text-xs text-gray-600 dark:text-gray-300 border-b border-border font-medium">${lang}</div><pre class="bg-gray-50 dark:bg-gray-900 p-4 overflow-x-auto m-0"><code class="text-sm text-gray-800 dark:text-gray-200 font-mono leading-relaxed">${highlightedCode}</code></pre></div>`;
            });

            // 处理流式渲染时的未闭合代码块（仅在流式模式下）
            if (isStreaming) {
                // 匹配以```开头但没有结尾```的代码块
                const unclosedCodeBlockRegex = /```(\w+)?\n?([\s\S]*?)$/;
                const unclosedMatch = processedText.match(unclosedCodeBlockRegex);

                if (unclosedMatch && !unclosedMatch[0].includes('```', 3)) {
                    const [fullMatch, language, code] = unclosedMatch;
                    const lang = language || 'text';
                    const highlightedCode = highlightCode(code, lang);

                    // 替换未闭合的代码块，添加流式指示器
                    processedText = processedText.replace(unclosedCodeBlockRegex,
                        `<div class="code-block my-3 streaming-code"><div class="code-header bg-muted/50 dark:bg-muted/70 px-3 py-1 text-xs text-muted-foreground border-b border-border flex items-center gap-2">${lang}<span class="text-xs text-primary animate-pulse">● 正在输入...</span></div><pre class="bg-muted dark:bg-muted/80 p-3 overflow-x-auto border border-border border-t-0 rounded-b-md"><code class="text-sm text-foreground">${highlightedCode}</code></pre></div>`
                    );
                }
            }

            // 处理内联代码
            const inlineCodeRegex = /`([^`]+)`/g;
            processedText = processedText.replace(inlineCodeRegex, (_match, code) => {
                return `<code class="bg-muted dark:bg-muted/80 px-1.5 py-0.5 rounded text-sm font-mono text-foreground border border-border/50">${code}</code>`;
            });

            // 处理标题
            processedText = processedText.replace(/^### (.*$)/gm, '<h3 class="text-lg font-semibold mt-4 mb-2 text-foreground">$1</h3>');
            processedText = processedText.replace(/^## (.*$)/gm, '<h2 class="text-xl font-semibold mt-4 mb-2 text-foreground">$1</h2>');
            processedText = processedText.replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-4 mb-2 text-foreground">$1</h1>');

            // 处理列表
            processedText = processedText.replace(/^\* (.*$)/gm, '<li class="ml-4 text-foreground">• $1</li>');
            processedText = processedText.replace(/^\d+\. (.*$)/gm, '<li class="ml-4 list-decimal text-foreground">$1</li>');

            // 处理粗体和斜体
            processedText = processedText.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-foreground">$1</strong>');
            processedText = processedText.replace(/\*(.*?)\*/g, '<em class="italic text-foreground">$1</em>');

            // 处理链接
            processedText = processedText.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary hover:text-primary/80 hover:underline transition-colors" target="_blank" rel="noopener noreferrer">$1</a>');

            // 处理引用
            processedText = processedText.replace(/^> (.*$)/gm, '<blockquote class="border-l-4 border-primary/30 dark:border-primary/50 pl-4 italic text-muted-foreground bg-muted/20 dark:bg-muted/30 py-2 rounded-r">$1</blockquote>');

            // 处理换行
            processedText = processedText.replace(/\n\n/g, '</p><p class="mb-2">');
            processedText = processedText.replace(/\n/g, '<br>');

            // 包装段落
            if (processedText && !processedText.startsWith('<')) {
                processedText = `<p class="mb-2">${processedText}</p>`;
            }

            return processedText;
        };
    }, []);

    // 简单的代码高亮函数
    const highlightCode = (code: string, language: string): string => {
        // 不进行复杂的语法高亮，避免颜色冲突
        // 保持代码的原始格式，使用统一的颜色
        return code;
    };

    return (
        <div
            className={cn(
                'prose prose-sm max-w-none',
                'prose-headings:text-foreground prose-p:text-foreground',
                'prose-strong:text-foreground prose-em:text-foreground',
                'prose-code:text-foreground prose-pre:bg-muted',
                'prose-a:text-primary prose-a:no-underline hover:prose-a:underline',
                className
            )}
        >
            <div
                dangerouslySetInnerHTML={{
                    __html: renderContent(content)
                }}
            />
            {isStreaming && (
                <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
            )}
        </div>
    );
};

export default MarkdownRenderer;