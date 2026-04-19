const express = require('express');
const router = express.Router();
const { saveFeedback, loadAllTickets } = require('../storage');

router.post('/', async (req, res) => {
  const { type, message, description, url, project, userAgent, stack } = req.body;

  const validTypes = ['bug', 'feature', 'suggestion', 'error'];
  if (!validTypes.includes(type)) {
    return res.status(400).json({ error: 'Invalid type' });
  }

  const text = message || description || '';
  if (!text.trim() && type !== 'error') {
    return res.status(400).json({ error: 'Message required' });
  }

  try {
    const result = await saveFeedback({
      type,
      message: text,
      description: text,
      url: url || '',
      project: project || 'unknown',
      userAgent: userAgent || req.headers['user-agent'] || '',
      stack: stack || '',
    });
    res.json({ ok: true, id: result.id });
  } catch (err) {
    console.error('Failed to save feedback:', err);
    res.status(500).json({ error: 'Storage error' });
  }
});

router.get('/', async (req, res) => {
  try {
    const tickets = await loadAllTickets();
    res.json(tickets);
  } catch (err) {
    res.status(500).json({ error: 'Could not load tickets' });
  }
});

module.exports = router;
