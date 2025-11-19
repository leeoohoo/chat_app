/**
 * 应用管理 API
 * 复刻自 Python: app/api/applications.py
 */

import express from 'express';
import { getDatabaseSync } from '../models/database-factory.js';
import { logger } from '../utils/logger.js';
import { v4 as uuidv4 } from 'uuid';

const router = express.Router();

/**
 * GET /applications - 获取应用列表
 */
router.get('/', async (req, res) => {
  try {
    const { user_id } = req.query;
    const db = getDatabaseSync();

    let query = 'SELECT * FROM applications';
    const params = [];

    if (user_id) {
      query += ' WHERE user_id = ?';
      params.push(user_id);
    }

    query += ' ORDER BY created_at DESC';

    const applications = db.fetchallSync(query, params);
    logger.info(`获取到 ${applications.length} 个应用`);
    res.json(applications);
  } catch (error) {
    logger.error('获取应用列表失败:', error);
    res.status(500).json({ error: '获取应用列表失败' });
  }
});

/**
 * POST /applications - 创建应用
 */
router.post('/', async (req, res) => {
  try {
    const { name, url, description, user_id, enabled } = req.body;

    if (!name || !url) {
      return res.status(400).json({ error: 'name 和 url 为必填项' });
    }

    const db = getDatabaseSync();
    const id = uuidv4();
    const now = new Date().toISOString();

    db.executeSync(
      `INSERT INTO applications (id, name, url, description, user_id, enabled, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [id, name, url, description || null, user_id || null, enabled !== false ? 1 : 0, now, now]
    );

    const newApp = db.fetchoneSync('SELECT * FROM applications WHERE id = ?', [id]);
    logger.info(`创建应用成功: ${id}`);
    res.status(201).json(newApp);
  } catch (error) {
    logger.error('创建应用失败:', error);
    res.status(500).json({ error: '创建应用失败' });
  }
});

/**
 * GET /applications/:application_id - 获取特定应用
 */
router.get('/:application_id', async (req, res) => {
  try {
    const { application_id } = req.params;
    const db = getDatabaseSync();

    const application = db.fetchoneSync('SELECT * FROM applications WHERE id = ?', [application_id]);

    if (!application) {
      return res.status(404).json({ error: 'Application 不存在' });
    }

    res.json(application);
  } catch (error) {
    logger.error('获取应用失败:', error);
    res.status(500).json({ error: '获取应用失败' });
  }
});

/**
 * PUT /applications/:application_id - 更新应用
 */
router.put('/:application_id', async (req, res) => {
  try {
    const { application_id } = req.params;
    const { name, url, description, enabled } = req.body;
    const db = getDatabaseSync();

    const existing = db.fetchoneSync('SELECT * FROM applications WHERE id = ?', [application_id]);
    if (!existing) {
      return res.status(404).json({ error: 'Application 不存在' });
    }

    const updates = [];
    const params = [];

    if (name !== undefined) {
      updates.push('name = ?');
      params.push(name);
    }
    if (url !== undefined) {
      updates.push('url = ?');
      params.push(url);
    }
    if (description !== undefined) {
      updates.push('description = ?');
      params.push(description);
    }
    if (enabled !== undefined) {
      updates.push('enabled = ?');
      params.push(enabled ? 1 : 0);
    }

    if (updates.length > 0) {
      updates.push('updated_at = ?');
      params.push(new Date().toISOString());
      params.push(application_id);

      db.executeSync(
        `UPDATE applications SET ${updates.join(', ')} WHERE id = ?`,
        params
      );
    }

    const updated = db.fetchoneSync('SELECT * FROM applications WHERE id = ?', [application_id]);
    logger.info(`更新应用成功: ${application_id}`);
    res.json(updated);
  } catch (error) {
    logger.error('更新应用失败:', error);
    res.status(500).json({ error: '更新应用失败' });
  }
});

/**
 * DELETE /applications/:application_id - 删除应用
 */
router.delete('/:application_id', async (req, res) => {
  try {
    const { application_id } = req.params;
    const db = getDatabaseSync();

    const existing = db.fetchoneSync('SELECT * FROM applications WHERE id = ?', [application_id]);
    if (!existing) {
      return res.status(404).json({ error: 'Application 不存在' });
    }

    db.executeSync('DELETE FROM applications WHERE id = ?', [application_id]);
    logger.info(`删除应用成功: ${application_id}`);
    res.json({ ok: true });
  } catch (error) {
    logger.error('删除应用失败:', error);
    res.status(500).json({ error: '删除应用失败' });
  }
});

export default router;
