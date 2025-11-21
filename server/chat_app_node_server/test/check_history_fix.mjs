import { databaseFactory, getDatabase } from '../src/models/database-factory.js';
import { MessageManager } from '../src/services/v2/message-manager.js';

(async () => {
  try {
    // init DB
    await databaseFactory.getAdapter();
    const db = await getDatabase();

    const rows = await db.fetchall(
      'SELECT session_id, COUNT(*) AS cnt FROM messages GROUP BY session_id ORDER BY cnt DESC LIMIT 1',
      []
    );

    if (!rows || rows.length === 0) {
      console.log('No messages in DB to verify.');
      process.exit(0);
    }

    const sessionId = rows[0].session_id;
    console.log('Using session:', sessionId);

    // Fetch all in ASC for ground truth
    const allAsc = await db.fetchall(
      'SELECT id, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC',
      [sessionId]
    );

    console.log('Total messages:', allAsc.length);
    const lastTwoTruth = allAsc.slice(-2);

    const mgr = new MessageManager();
    const recentTwo = await mgr.getSessionMessages(sessionId, 2);

    const view = (list) => list.map(m => ({ id: m.id, created_at: m.created_at }));

    console.log('Expected last two (ASC):', lastTwoTruth);
    console.log('Manager.getSessionMessages(2):', view(recentTwo));

    const ok = recentTwo.length === lastTwoTruth.length && recentTwo.every((m, i) => m.id === lastTwoTruth[i].id);
    console.log('Matches last two?', ok);
  } catch (e) {
    console.error('Error verifying:', e);
    process.exit(1);
  }
})();
