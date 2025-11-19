/**
 * 抽象数据库接口 - 定义所有数据库适配器必须实现的接口
 * 复刻自 Python: app/models/database_interface.py
 */

export class AbstractDatabaseAdapter {
  /**
   * 初始化数据库（创建表、索引等）
   */
  async initDatabase() {
    throw new Error('initDatabase() must be implemented');
  }

  /**
   * 关闭数据库连接
   */
  async close() {
    throw new Error('close() must be implemented');
  }

  /**
   * 执行 SQL 查询（异步）
   * @param {string} query - SQL 查询语句
   * @param {Array} params - 查询参数
   * @returns {Promise<any>} 查询结果
   */
  async execute(query, params = []) {
    throw new Error('execute() must be implemented');
  }

  /**
   * 获取单行数据（异步）
   * @param {string} query - SQL 查询语句
   * @param {Array} params - 查询参数
   * @returns {Promise<Object|null>} 单行数据或 null
   */
  async fetchone(query, params = []) {
    throw new Error('fetchone() must be implemented');
  }

  /**
   * 获取所有行数据（异步）
   * @param {string} query - SQL 查询语句
   * @param {Array} params - 查询参数
   * @returns {Promise<Array<Object>>} 所有行数据
   */
  async fetchall(query, params = []) {
    throw new Error('fetchall() must be implemented');
  }

  /**
   * 执行 SQL 查询（同步） - 用于非异步上下文
   * @param {string} query - SQL 查询语句
   * @param {Array} params - 查询参数
   * @returns {any} 查询结果
   */
  executeSync(query, params = []) {
    throw new Error('executeSync() must be implemented');
  }

  /**
   * 获取单行数据（同步）
   * @param {string} query - SQL 查询语句
   * @param {Array} params - 查询参数
   * @returns {Object|null} 单行数据或 null
   */
  fetchoneSync(query, params = []) {
    throw new Error('fetchoneSync() must be implemented');
  }

  /**
   * 获取所有行数据（同步）
   * @param {string} query - SQL 查询语句
   * @param {Array} params - 查询参数
   * @returns {Array<Object>} 所有行数据
   */
  fetchallSync(query, params = []) {
    throw new Error('fetchallSync() must be implemented');
  }

  /**
   * 批量执行 SQL 查询（异步）
   * @param {string} query - SQL 查询语句
   * @param {Array<Array>} paramsList - 参数列表
   * @returns {Promise<any>} 查询结果
   */
  async executeMany(query, paramsList) {
    throw new Error('executeMany() must be implemented');
  }

  /**
   * 检查表是否存在（异步）
   * @param {string} tableName - 表名
   * @returns {Promise<boolean>} 表是否存在
   */
  async tableExists(tableName) {
    throw new Error('tableExists() must be implemented');
  }

  /**
   * 创建表（异步）
   * @param {string} tableName - 表名
   * @param {string} schema - 表结构定义
   * @returns {Promise<void>}
   */
  async createTable(tableName, schema) {
    throw new Error('createTable() must be implemented');
  }

  /**
   * 删除表（异步）
   * @param {string} tableName - 表名
   * @returns {Promise<void>}
   */
  async dropTable(tableName) {
    throw new Error('dropTable() must be implemented');
  }

  /**
   * 开始事务（异步）
   * @returns {Promise<void>}
   */
  async beginTransaction() {
    throw new Error('beginTransaction() must be implemented');
  }

  /**
   * 提交事务（异步）
   * @returns {Promise<void>}
   */
  async commitTransaction() {
    throw new Error('commitTransaction() must be implemented');
  }

  /**
   * 回滚事务（异步）
   * @returns {Promise<void>}
   */
  async rollbackTransaction() {
    throw new Error('rollbackTransaction() must be implemented');
  }

  /**
   * 创建索引（异步）
   * @param {string} tableName - 表名
   * @param {string} indexName - 索引名
   * @param {Array<string>} fields - 字段列表
   * @returns {Promise<void>}
   */
  async createIndex(tableName, indexName, fields) {
    throw new Error('createIndex() must be implemented');
  }
}
