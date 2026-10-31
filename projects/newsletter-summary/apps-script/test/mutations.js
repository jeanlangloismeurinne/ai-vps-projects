// node apps-script/test/mutations.js → mute chaque garde de Code.gs et exige qu'au moins un test rougisse
// (et nomme lequel). Une mutation qui laisse la suite verte = garde non éprouvée.
const fs = require('fs'), os = require('os'), path = require('path'), { spawnSync } = require('child_process');
const src = fs.readFileSync(path.join(__dirname, '..', 'Code.gs'), 'utf8');
const M = [
  ['signature non vérifiée', s => s.replace('if (!equal_(expected, req.sig)) return', 'if (false) return')],
  ['comparaison de signature toujours vraie', s => s.replace('if (a.length !== b.length) return false;', 'return true;')],
  ['fenêtre d\'horodatage retirée', s => s.replace('> TS_WINDOW_S', '> 1e12')],
  ['nonce non mémorisé', s => s.replace("cache.put('n:' + req.nonce, '1', NONCE_TTL_S);", '')],
  ['interrupteur DISABLED ignoré', s => s.replace("props.getProperty('DISABLED') === 'true' &&", 'false &&')],
  ['liste blanche de domaines ignorée', s => s.replace('.indexOf(dest.split(\'@\')[1]) < 0', '.indexOf(dest.split(\'@\')[1]) < -5')],
  ['validation Gmail de la destination ignorée', s => s.replace('if (!verified) throw', 'if (false) throw')],
  ['delete_rule sans contrôle de gestion', s => s.replace("if (!getManaged_()[id]) throw err_('not_managed', 'Filtre non géré');\n    removeFilter_(id);", 'removeFilter_(id);')],
  ['replace_rule sans contrôle de gestion', s => s.replace("if (!getManaged_()[oldId]) throw err_('not_managed', 'Filtre non géré');", '')],
  ['replace : suppression avant création', s => s.replace('const res = insert_(p, oldId);   // créer d\'abord...\n    removeFilter_(oldId);            // ...supprimer ensuite', 'removeFilter_(oldId); const res = insert_(p, oldId);')],
  ['DENY_FROM ignoré sur l\'expéditeur', s => s.replace("csv_('DENY_FROM').some(d => domain === d || domain.endsWith('.' + d))", 'false')],
  ['sous-domaine de DENY_FROM toléré', s => s.replace("|| domain.endsWith('.' + d)", '')],
  ['exclusion DENY_FROM non ajoutée au filtre', s => s.replace("const deny = csv_('DENY_FROM');", 'const deny = [];')],
  ['plafond sans expéditeur retiré', s => s.replace('>= MAX_SENDERLESS', '>= 1e9')],
  ['plafond de règles retiré', s => s.replace("Object.keys(managed).length >= MAX_RULES", 'false')],
  ['quota d\'écriture relevé', s => s.replace('write: 30', 'write: 3000')],
  ['quota de lecture relevé', s => s.replace('read: 120', 'read: 12000')],
  ['idempotence retirée', s => s.replace('if (known) return', 'if (false) return')],
  ['404 à la suppression non toléré', s => s.replace("if (!/not found|404/i.test(String(e))) throw e;", 'throw e;')],
  ['suffixe public accepté', s => s.replace('PUBLIC_SUFFIXES.indexOf(domain) >= 0', 'false')],
  ['sujet de 6 caractères non exigé', s => s.replace('subject.length < 6', 'subject.length < 0')],
  ['doublon non détecté', s => s.replace('if (dup) throw', 'if (false) throw')],
  ['réponse d\'erreur non signée correctement', s => s.replace("[nonce, 'false', r.error.code].join('.')", "[nonce, 'true', r.error.code].join('.')")],
  ['garde hasOwnProperty retirée', s => s.replace("!Object.prototype.hasOwnProperty.call(HANDLERS, req.action)", 'false')],
  ['texte non assaini', s => s.replace('!/^[\\p{L}\\p{N} .,:\'’!?%€_-]*$/u.test(t)', 'false')],
  ['panic ne supprime pas', s => s.replace("try { removeFilter_(id); } catch (e) { console.error('panic ' + id); }", '')],
  ['panic n\'active pas DISABLED', s => s.replace("PropertiesService.getScriptProperties().setProperty('DISABLED', 'true');", 'void 0;')],
  ['filtres étrangers listés par défaut', s => s.replace('managed[f.id] || p.include_foreign === true', 'true')],
];
let bad = 0;
for (const [name, fn] of M) {
  const out = fn(src);
  if (out === src) { console.log('INERTE ' + name + ' (le motif ne mute rien)'); bad++; continue; }
  const f = path.join(os.tmpdir(), 'mut-' + process.pid + '.gs'); fs.writeFileSync(f, out);
  const r = spawnSync('node', [path.join(__dirname, 'run.js')], { env: Object.assign({}, process.env, { CODE_GS: f }), encoding: 'utf8' });
  fs.unlinkSync(f);
  const reds = r.stdout.split('\n').filter(l => l.startsWith('ROUGE')).map(l => l.slice(7, 60));
  if (!reds.length) { console.log('VIVANTE ' + name + '  ← aucune garde n\'a rougi'); bad++; } else console.log('TUÉE   ' + name + '  ← ' + reds[0]);
}
console.log(`BILAN mutations : ${M.length - bad}/${M.length} tuées`);
process.exit(bad ? 1 : 0);
