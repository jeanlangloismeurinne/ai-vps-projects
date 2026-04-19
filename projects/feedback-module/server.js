const express = require('express');
const cors = require('cors');
const path = require('path');
const feedbackRouter = require('./routes/feedback');

const PORT = process.env.FEEDBACK_PORT || 3333;
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || '*').split(',');

const app = express();

app.use(cors({
  origin: ALLOWED_ORIGINS[0] === '*' ? '*' : ALLOWED_ORIGINS,
  methods: ['GET', 'POST'],
}));

app.use(express.json({ limit: '50kb' }));

app.use('/widget', express.static(path.join(__dirname, 'widget')));

app.use('/api/feedback', feedbackRouter);

app.get('/health', (_, res) => res.json({ ok: true }));

app.listen(PORT, () => {
  console.log(`Feedback service running on http://localhost:${PORT}`);
  console.log(`  Widget : http://localhost:${PORT}/widget/feedback-widget.js`);
  console.log(`  API    : http://localhost:${PORT}/api/feedback`);
});
