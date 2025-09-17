import React from 'react';
import StandaloneChatInterface from '../src';
import '../src/styles/index.css';

/**
 * 基础使用示例 - 独立聊天组件
 * 不需要任何props，开箱即用
 */
function BasicExample() {
  return (
    <div className="h-screen w-full">
      <StandaloneChatInterface className="h-full" />
    </div>
  );
}

export default BasicExample;