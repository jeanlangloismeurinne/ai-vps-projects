const fs = require('fs').promises;
const path = require('path');

const TICKETS_DIR = path.join(__dirname, 'tickets');
const TICKETS_MD = path.join(__dirname, 'TICKETS.md');

const TYPE_EMOJI = { bug: '🐛', feature: '✨', suggestion: '💡', error: '🔴' };
const TYPE_LABEL = { bug: 'Bug', feature: 'Feature', suggestion: 'Suggestion', error: 'Erreur JS' };

async function saveFeedback(data) {
  const id = Date.now();
  const date = new Date().toISOString();
  const slug = (data.message || data.description || 'no-message')
    .slice(0, 40)
    .replace(/[^a-zA-Z0-9\u00C0-\u024F ]/g, '')
    .trim()
    .replace(/ +/g, '-')
    .toLowerCase();

  const filename = `${id}-${data.type}-${slug}.md`;
  const filepath = path.join(TICKETS_DIR, filename);

  const content = [
    `---`,
    `id: ${id}`,
    `type: ${data.type}`,
    `status: open`,
    `date: ${date}`,
    `project: ${data.project || 'unknown'}`,
    `url: ${data.url || ''}`,
    `---`,
    ``,
    `## ${TYPE_EMOJI[data.type] || '📝'} ${TYPE_LABEL[data.type] || data.type}`,
    ``,
    `**Date** : ${new Date(date).toLocaleString('fr-FR')}`,
    `**URL** : \`${data.url || 'N/A'}\``,
    `**Projet** : ${data.project || 'N/A'}`,
    ``,
    `### Description`,
    ``,
    data.message || data.description || '_Aucune description_',
    ``,
  ];

  if (data.stack) {
    content.push(`### Stack trace`, ``, `\`\`\``, data.stack, `\`\`\``, ``);
  }

  if (data.userAgent) {
    content.push(`### Contexte`, ``, `- **User-Agent** : ${data.userAgent}`, ``);
  }

  await fs.writeFile(filepath, content.join('\n'));
  await regenerateTickets();
  return { id, filename };
}

async function loadAllTickets() {
  const files = await fs.readdir(TICKETS_DIR);
  const mdFiles = files.filter(f => f.endsWith('.md')).sort().reverse();

  const tickets = await Promise.all(
    mdFiles.map(async (file) => {
      const raw = await fs.readFile(path.join(TICKETS_DIR, file), 'utf8');
      const frontmatter = {};
      const fmMatch = raw.match(/^---\n([\s\S]*?)\n---/);
      if (fmMatch) {
        fmMatch[1].split('\n').forEach(line => {
          const [k, ...v] = line.split(': ');
          if (k) frontmatter[k.trim()] = v.join(': ').trim();
        });
      }
      const descMatch = raw.match(/### Description\n\n([\s\S]*?)(?:\n###|\n*$)/);
      frontmatter.description = descMatch ? descMatch[1].trim().slice(0, 120) : '';
      frontmatter.file = file;
      return frontmatter;
    })
  );

  return tickets;
}

async function regenerateTickets() {
  const tickets = await loadAllTickets();
  const open = tickets.filter(t => t.status === 'open');
  const closed = tickets.filter(t => t.status !== 'open');

  const byType = (type) => open.filter(t => t.type === type);
  const bugs = byType('bug');
  const errors = byType('error');
  const features = byType('feature');
  const suggestions = byType('suggestion');

  const tableRows = (items) => {
    if (!items.length) return '_Aucun_\n';
    const rows = items.map(t => {
      const date = t.date ? new Date(t.date).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '?';
      const desc = (t.description || '').replace(/\|/g, '\\|').slice(0, 80);
      return `| \`${t.id}\` | ${date} | \`${(t.url || '').slice(0, 50)}\` | ${desc} |`;
    });
    return `| ID | Date | URL | Description |\n|---|---|---|---|\n${rows.join('\n')}\n`;
  };

  const lines = [
    `# TICKETS — Feedback`,
    ``,
    `> Généré automatiquement le ${new Date().toLocaleString('fr-FR')}. **Lire au début de chaque session.**`,
    ``,
    `## Résumé`,
    ``,
    `| Type | Ouverts | Fermés |`,
    `|---|---|---|`,
    `| ${TYPE_EMOJI.bug} Bugs | ${bugs.length} | ${closed.filter(t => t.type === 'bug').length} |`,
    `| ${TYPE_EMOJI.error} Erreurs JS | ${errors.length} | ${closed.filter(t => t.type === 'error').length} |`,
    `| ${TYPE_EMOJI.feature} Features | ${features.length} | ${closed.filter(t => t.type === 'feature').length} |`,
    `| ${TYPE_EMOJI.suggestion} Suggestions | ${suggestions.length} | ${closed.filter(t => t.type === 'suggestion').length} |`,
    ``,
  ];

  if (bugs.length || errors.length) {
    lines.push(`## 🐛 Bugs & Erreurs JS ouverts`, ``);
    lines.push(tableRows([...bugs, ...errors]));
  }

  if (features.length) {
    lines.push(`## ✨ Features demandées`, ``);
    lines.push(tableRows(features));
  }

  if (suggestions.length) {
    lines.push(`## 💡 Suggestions ouvertes`, ``);
    lines.push(tableRows(suggestions));
  }

  if (closed.length) {
    lines.push(`## ✅ Fermés (${closed.length})`, ``);
    lines.push(tableRows(closed));
  }

  if (!open.length && !closed.length) {
    lines.push(`_Aucun ticket pour l'instant._`, ``);
  }

  await fs.writeFile(TICKETS_MD, lines.join('\n'));
}

module.exports = { saveFeedback, loadAllTickets, regenerateTickets };
