/**
 * 配置读取器 - 环境变量和配置文件管理
 * 复刻自 Python: app/utils/config_reader.py
 */

import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 加载 .env 文件
dotenv.config();

/**
 * 配置类
 */
export class Config {
  constructor() {
    // OpenAI 配置
    this.OPENAI_API_KEY = process.env.OPENAI_API_KEY || '';
    this.OPENAI_BASE_URL = process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1';

    // 服务器配置
    this.PORT = parseInt(process.env.PORT || '3001', 10);
    this.NODE_ENV = process.env.NODE_ENV || 'development';
    this.HOST = process.env.HOST || '0.0.0.0';

    // 日志配置
    this.LOG_LEVEL = process.env.LOG_LEVEL || 'info';
    this.LOG_MAX_FILES = process.env.LOG_MAX_FILES || '7d';
    this.LOG_MAX_SIZE = process.env.LOG_MAX_SIZE || '10m';

    // CORS 配置
    this.CORS_ORIGINS = process.env.CORS_ORIGINS
      ? process.env.CORS_ORIGINS.split(',')
      : ['*'];
  }

  /**
   * 验证必需的配置项
   */
  validate() {
    const required = [];

    // OpenAI API Key 不是必需的，因为可以从请求中传入
    // if (!this.OPENAI_API_KEY) {
    //   required.push('OPENAI_API_KEY');
    // }

    if (required.length > 0) {
      throw new Error(`缺少必需的环境变量: ${required.join(', ')}`);
    }
  }

  /**
   * 打印配置信息（隐藏敏感信息）
   */
  print() {
    console.log('当前配置:');
    console.log(`  - NODE_ENV: ${this.NODE_ENV}`);
    console.log(`  - PORT: ${this.PORT}`);
    console.log(`  - HOST: ${this.HOST}`);
    console.log(`  - OPENAI_BASE_URL: ${this.OPENAI_BASE_URL}`);
    console.log(`  - OPENAI_API_KEY: ${this.OPENAI_API_KEY ? '已设置' : '未设置'}`);
    console.log(`  - LOG_LEVEL: ${this.LOG_LEVEL}`);
  }
}

// 导出单例实例
export const config = new Config();
export default config;
