// newsletter-forward-api v1.1.0
const VERSION = '1.1.0';
const MAX_RULES = 50;
const MAX_SENDERLESS = 5; // règles sans expéditeur
const TS_WINDOW_S = 60;
const NONCE_TTL_S = 600;
const LIMITS = { read: 120, write: 30 }; // appels par heure
const WRITE_ACTIONS = ['create_rule', 'replace_rule', 'delete_rule'];
// Suffixes publics à deux niveaux : refusés comme domaines entiers (« @co.uk » couvrirait un pays).
const PUBLIC_SUFFIXES = ['co.uk', 'org.uk', 'ac.uk', 'gov.uk', 'me.uk', 'com.au', 'net.au', 'org.au', 'co.nz',
  'co.jp', 'ne.jp', 'or.jp', 'com.br', 'com.mx', 'com.ar', 'co.za', 'co.in', 'com.cn', 'com.hk', 'com.sg',
  'com.tr', 'co.kr', 'com.tw'];

function doGet() { return out_(fail_('invalid_action', 'POST uniquement')); }

function doPost(e) {
  const props = PropertiesService.getScriptProperties();
  const secret = props.getProperty('HMAC_SECRET') || '';
  let req;
  try { req = JSON.parse(e.postData.contents); }
  catch (err) { return out_(fail_('invalid_payload', 'JSON illisible')); }
  if (secret.length < 32) return out_(fail_('internal', 'Secret absent ou trop court'));
  if (!req || req.v !== 1 || typeof req.ts !== 'number' || typeof req.action !== 'string' ||
      typeof req.payload !== 'string' || typeof req.sig !== 'string' ||
      !/^[0-9a-f]{16,64}$/.test(String(req.nonce))) {
    return out_(fail_('invalid_payload', 'Enveloppe invalide'));
  }
  // Authentification : rien d'autre n'est lu ni exécuté avant cette vérification
  const expected = hmac_(secret, [req.v, req.ts, req.nonce, req.action, req.payload].join('.'));
  if (!equal_(expected, req.sig)) return out_(fail_('bad_signature', 'Signature invalide'));

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) return signed_(fail_('busy', 'Verrou non obtenu'), req.nonce, secret);
  try {
    if (Math.abs(Date.now() / 1000 - req.ts) > TS_WINDOW_S) throw err_('stale_timestamp', 'Horodatage hors fenêtre');
    const cache = CacheService.getScriptCache();
    if (cache.get('n:' + req.nonce)) throw err_('replayed_nonce', 'Nonce déjà utilisé');
    cache.put('n:' + req.nonce, '1', NONCE_TTL_S);
    if (props.getProperty('DISABLED') === 'true' && req.action !== 'ping') throw err_('disabled', 'Script coupé');
    if (!Object.prototype.hasOwnProperty.call(HANDLERS, req.action)) throw err_('invalid_action', 'Action inconnue');
    if (!allow_(req.action)) throw err_('rate_limited', 'Quota horaire atteint');
    let payload;
    try { payload = req.payload ? JSON.parse(req.payload) : {}; }
    catch (err) { throw err_('invalid_payload', 'Payload illisible'); }
    return signed_({ ok: true, result: HANDLERS[req.action](payload || {}) }, req.nonce, secret);
  } catch (err) {
    if (!err.code) console.error(String(err && err.stack ? err.stack : err)); // jamais le payload
    return signed_(fail_(err.code || 'internal', err.code ? err.message : 'Erreur interne'), req.nonce, secret);
  } finally {
    lock.releaseLock();
  }
}

const HANDLERS = {
  ping: () => ({ version: VERSION, time: new Date().toISOString(),
    enabled: PropertiesService.getScriptProperties().getProperty('DISABLED') !== 'true' }),
  list_forwarding_addresses: () =>
    forwarding_().map(a => ({ email: a.forwardingEmail, status: a.verificationStatus })),
  list_rules: p => {
    const managed = getManaged_();
    return (Gmail.Users.Settings.Filters.list('me').filter || [])
      .filter(f => managed[f.id] || p.include_foreign === true)
      .map(f => ({ id: f.id, managed: !!managed[f.id], client_request_id: managed[f.id] || null,
        criteria: f.criteria || {}, action: f.action || {} }));
  },
  get_limits: () => ({ managed: Object.keys(getManaged_()).length, max_rules: MAX_RULES, quota: quota_() }),
  create_rule: p => insert_(p, null),
  replace_rule: p => {
    const oldId = String(p.gmail_filter_id || '');
    if (!getManaged_()[oldId]) throw err_('not_managed', 'Filtre non géré');
    const res = insert_(p, oldId);   // créer d'abord...
    removeFilter_(oldId);            // ...supprimer ensuite
    const m = getManaged_(); delete m[oldId]; setManaged_(m);
    return res;
  },
  delete_rule: p => {
    const id = String(p.gmail_filter_id || '');
    if (!getManaged_()[id]) throw err_('not_managed', 'Filtre non géré');
    removeFilter_(id);
    const m = getManaged_(); delete m[id]; setManaged_(m);
    return { deleted: true };
  }
};

function insert_(p, replacingId) {
  const crid = String(p.client_request_id || '');
  if (!/^[A-Za-z0-9-]{8,64}$/.test(crid)) throw err_('invalid_payload', 'client_request_id invalide');
  const managed = getManaged_();
  const known = Object.keys(managed).find(id => managed[id] === crid);
  if (known) return { gmail_filter_id: known, replayed: true };
  if (!replacingId && Object.keys(managed).length >= MAX_RULES) throw err_('rule_limit', 'Plafond de règles atteint');
  const v = validate_(p);
  if (!v.from && countSenderless_(managed, replacingId) >= MAX_SENDERLESS) throw err_('rule_limit', 'Trop de règles sans expéditeur');
  const dup = (Gmail.Users.Settings.Filters.list('me').filter || [])
    .some(f => managed[f.id] && f.id !== replacingId && same_(f, v));
  if (dup) throw err_('duplicate', 'Règle déjà existante');
  const created = Gmail.Users.Settings.Filters.create(toFilter_(v), 'me');
  managed[created.id] = crid;
  setManaged_(managed);
  return { gmail_filter_id: created.id };
}

function validate_(p) {
  const from = String(p.from || '').trim().toLowerCase();
  const okFrom = /^(@[a-z0-9-]+(\.[a-z0-9-]+)+|[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+)$/.test(from);
  const domain = from.split('@')[1] || '';
  if (from && (!okFrom || csv_('DENY_FROM').some(d => domain === d || domain.endsWith('.' + d)))) {
    throw err_('criteria_too_broad', 'Expéditeur invalide, trop large ou interdit');
  }
  if (from.charAt(0) === '@' && PUBLIC_SUFFIXES.indexOf(domain) >= 0) {
    throw err_('criteria_too_broad', 'Suffixe public refusé comme domaine entier');
  }
  const subject = clean_(p.subject_contains, 120);
  if (!from && subject.length < 6) throw err_('criteria_too_broad', 'Critère insuffisant : expéditeur, ou sujet de 6 caractères');
  const dest = String(p.destination || '').trim().toLowerCase();
  if (!/^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(dest) ||
      csv_('DEST_ALLOWED_DOMAINS').indexOf(dest.split('@')[1]) < 0) {
    throw err_('destination_not_allowed', 'Domaine de destination non autorisé');
  }
  const verified = forwarding_().some(a =>
    String(a.forwardingEmail).toLowerCase() === dest && a.verificationStatus === 'accepted');
  if (!verified) throw err_('destination_not_verified', 'Adresse non validée dans Gmail');
  return { from: from, dest: dest, subject: subject,
    exclude: negated_(clean_(p.exclude_words, 120)), skipInbox: p.skip_inbox === true };
}

function negated_(exclude) {
  const deny = csv_('DENY_FROM');
  const clause = deny.length ? 'from:(' + deny.map(d => '@' + d).join(' OR ') + ')' : '';
  return [exclude ? '(' + exclude + ')' : '', clause].filter(Boolean).join(' OR ');
}

function countSenderless_(managed, replacingId) {
  return (Gmail.Users.Settings.Filters.list('me').filter || [])
    .filter(f => managed[f.id] && f.id !== replacingId && !(f.criteria || {}).from).length;
}

function toFilter_(v) {
  const criteria = {};
  if (v.from) criteria.from = v.from;
  if (v.subject) criteria.subject = v.subject;
  if (v.exclude) criteria.negatedQuery = v.exclude;
  const action = { forward: v.dest };
  if (v.skipInbox) action.removeLabelIds = ['INBOX'];
  return { criteria: criteria, action: action };
}

function same_(f, v) {
  const c = f.criteria || {}, a = f.action || {};
  return String(c.from || '').toLowerCase() === v.from && (c.subject || '') === v.subject &&
    String(a.forward || '').toLowerCase() === v.dest;
}

function clean_(s, max) {
  const t = String(s || '').trim();
  if (t.length > max || !/^[\p{L}\p{N} .,:'’!?%€_-]*$/u.test(t)) throw err_('invalid_payload', 'Texte invalide');
  return t;
}

function removeFilter_(id) {
  try { Gmail.Users.Settings.Filters.remove('me', id); }
  catch (e) { if (!/not found|404/i.test(String(e))) throw e; }
}

function forwarding_() { return Gmail.Users.Settings.ForwardingAddresses.list('me').forwardingAddresses || []; }

function readQuota_() {
  const hour = Utilities.formatDate(new Date(), 'UTC', 'yyyyMMddHH');
  const q = JSON.parse(PropertiesService.getScriptProperties().getProperty('QUOTA') || '{}');
  return q.hour === hour ? q : { hour: hour, read: 0, write: 0 };
}
function quota_() { const q = readQuota_(); return { read_left: LIMITS.read - q.read, write_left: LIMITS.write - q.write }; }
function allow_(action) {
  const kind = WRITE_ACTIONS.indexOf(action) >= 0 ? 'write' : 'read';
  const q = readQuota_();
  if (q[kind] >= LIMITS[kind]) return false;
  q[kind] += 1;
  PropertiesService.getScriptProperties().setProperty('QUOTA', JSON.stringify(q));
  return true;
}

function getManaged_() { return JSON.parse(PropertiesService.getScriptProperties().getProperty('MANAGED') || '{}'); }
function setManaged_(m) { PropertiesService.getScriptProperties().setProperty('MANAGED', JSON.stringify(m)); }
function csv_(k) {
  return (PropertiesService.getScriptProperties().getProperty(k) || '').split(',')
    .map(s => s.trim().toLowerCase().replace(/^@/, '')).filter(Boolean);
}

function hmac_(secret, msg) {
  return Utilities.computeHmacSha256Signature(msg, secret)
    .map(b => ((b + 256) % 256).toString(16).padStart(2, '0')).join('');
}
function equal_(a, b) { // comparaison à durée constante
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
function fail_(code, message) { return { ok: false, error: { code: code, message: message } }; }
function err_(code, message) { const e = new Error(message); e.code = code; return e; }
function signed_(r, nonce, secret) {
  if (r.ok) {
    const body = JSON.stringify(r.result);
    return out_({ ok: true, result: body, nonce: nonce, sig: hmac_(secret, [nonce, 'true', body].join('.')) });
  }
  return out_({ ok: false, error: r.error, nonce: nonce, sig: hmac_(secret, [nonce, 'false', r.error.code].join('.')) });
}

// À lancer à la main depuis l'éditeur
function authorize() { forwarding_(); } // déclenche l'écran d'autorisation
function panic() {
  Object.keys(getManaged_()).forEach(id => { try { removeFilter_(id); } catch (e) { console.error('panic ' + id); } });
  setManaged_({});
  PropertiesService.getScriptProperties().setProperty('DISABLED', 'true');
}
