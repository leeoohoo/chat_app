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
        return `<div class="math-block bg-muted/50 p-3 rounded-md my-2 text-center font-mono text-sm border">${formula.trim()}</div>`;
      });
      
      // 处理内联数学公式 ($...$)
      const mathInlineRegex = /\$([^$]+)\$/g;
      processedText = processedText.replace(mathInlineRegex, (_match, formula) => {
        return `<span class="math-inline bg-muted/30 px-1 py-0.5 rounded font-mono text-sm">${formula}</span>`;
      });
      
      // 处理代码块，支持语言标识
      const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
      processedText = processedText.replace(codeBlockRegex, (_match, language, code) => {
        const lang = language || 'text';
        const highlightedCode = highlightCode(code.trim(), lang);
        return `<div class="code-block my-3"><div class="code-header bg-muted/50 px-3 py-1 text-xs text-muted-foreground border-b">${lang}</div><pre class="bg-muted p-3 overflow-x-auto"><code class="text-sm">${highlightedCode}</code></pre></div>`;
      });
      
      // 处理内联代码
      const inlineCodeRegex = /`([^`]+)`/g;
      processedText = processedText.replace(inlineCodeRegex, (_match, code) => {
        return `<code class="bg-muted px-1.5 py-0.5 rounded text-sm font-mono">${code}</code>`;
      });
      
      // 处理标题
      processedText = processedText.replace(/^### (.*$)/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>');
      processedText = processedText.replace(/^## (.*$)/gm, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>');
      processedText = processedText.replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-4 mb-2">$1</h1>');
      
      // 处理列表
      processedText = processedText.replace(/^\* (.*$)/gm, '<li class="ml-4">• $1</li>');
      processedText = processedText.replace(/^\d+\. (.*$)/gm, '<li class="ml-4 list-decimal">$1</li>');
      
      // 处理粗体和斜体
      processedText = processedText.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>');
      processedText = processedText.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>');
      
      // 处理链接
      processedText = processedText.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary hover:underline" target="_blank" rel="noopener noreferrer">$1</a>');
      
      // 处理引用
      processedText = processedText.replace(/^> (.*$)/gm, '<blockquote class="border-l-4 border-primary/30 pl-4 italic text-muted-foreground">$1</blockquote>');
      
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
    // 基础的语法高亮，可以后续集成 Prism.js 或其他库
    let highlighted = code;
    
    if (language === 'javascript' || language === 'js' || language === 'typescript' || language === 'ts') {
      // 高亮关键字
      highlighted = highlighted.replace(/\b(const|let|var|function|return|if|else|for|while|class|import|export|from|async|await)\b/g, '<span class="text-blue-600 dark:text-blue-400 font-semibold">$1</span>');
      // 高亮字符串
      highlighted = highlighted.replace(/(['"`])([^'"\`]*?)\1/g, '<span class="text-green-600 dark:text-green-400">$1$2$1</span>');
      // 高亮注释
      highlighted = highlighted.replace(/(\/\/.*$)/gm, '<span class="text-gray-500 italic">$1</span>');
    } else if (language === 'python' || language === 'py') {
      // Python 关键字
      highlighted = highlighted.replace(/\b(def|class|import|from|return|if|else|elif|for|while|try|except|with|as|pass|break|continue)\b/g, '<span class="text-blue-600 dark:text-blue-400 font-semibold">$1</span>');
      // 字符串
      highlighted = highlighted.replace(/(['"`])([^'"\`]*?)\1/g, '<span class="text-green-600 dark:text-green-400">$1$2$1</span>');
      // 注释
      highlighted = highlighted.replace(/(#.*$)/gm, '<span class="text-gray-500 italic">$1</span>');
    }
    
    return highlighted;
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