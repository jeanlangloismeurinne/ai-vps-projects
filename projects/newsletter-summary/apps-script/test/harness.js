// Harnais : exécute Code.gs tel quel dans un contexte V8 isolé, avec des doublures de Google
// (Properties/Cache/Lock/Utilities/ContentService/Gmail). Ce qui est réel : Code.gs, le HMAC (crypto Node).
const vm = require('vm');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const SECRET = 'a'.repeat(64);
const GOOD_DEST = 'veille@xxxx.resend.app';

function makeEnv(opts = {}) {
  const store = Object.assign({
    HMAC_SECRET: SECRET, DEST_ALLOWED_DOMAINS: 'xxxx.resend.app', DENY_FROM: 'banque.fr,cabinet.com', DISABLED: 'false',
  }, opts.props || {});
  const cache = {};
  const filters = [];
  const gmailCalls = [];
  let seq = 0;
  const forwarding = opts.forwarding || [
    { forwardingEmail: GOOD_DEST, verificationStatus: 'accepted' },
    { forwardingEmail: 'attente@xxxx.resend.app', verificationStatus: 'pending' },
  ];
  const env = { store, filters, gmailCalls, cache, failNextRemove: false, failNextSetManaged: false, now: Date.now() };
  const ctx = vm.createContext({
    console: { error() {}, log() {} },
    PropertiesService: { getScriptProperties: () => ({
      getProperty: k => (k in store ? store[k] : null),
      setProperty: (k, v) => {
        if (k === 'MANAGED' && env.failNextSetManaged) { env.failNextSetManaged = false; throw new Error('props indisponibles'); }
        store[k] = String(v);
      },
    }) },
    CacheService: { getScriptCache: () => ({ get: k => cache[k] || null, put: (k, v) => { cache[k] = v; } }) },
    LockService: { getScriptLock: () => ({ tryLock: () => !env.lockBusy, releaseLock() {} }) },
    Utilities: {
      computeHmacSha256Signature: (msg, secret) =>
        Array.from(crypto.createHmac('sha256', secret).update(msg).digest()).map(b => (b > 127 ? b - 256 : b)),
      formatDate: (d) => d.toISOString().slice(0, 13).replace(/[-T]/g, ''),
    },
    ContentService: { MimeType: { JSON: 'json' }, createTextOutput: s => ({ text: s, setMimeType() { return this; } }) },
    Gmail: { Users: { Settings: {
      Filters: {
        list: () => { gmailCalls.push('filters.list'); return { filter: filters.slice() }; },
        create: (f) => {
          gmailCalls.push('filters.create');
          if (env.failCreate) throw new Error('boom');
          const created = Object.assign({ id: 'F' + (++seq) }, JSON.parse(JSON.stringify(f)));
          filters.push(created); return created;
        },
        remove: (u, id) => {
          gmailCalls.push('filters.remove');
          if (env.failNextRemove) { env.failNextRemove = false; throw new Error('Erreur 500 transitoire'); }
          const i = filters.findIndex(x => x.id === id);
          if (i < 0) throw new Error('Not Found');
          filters.splice(i, 1);
        },
      },
      ForwardingAddresses: { list: () => { gmailCalls.push('fwd.list'); return { forwardingAddresses: forwarding }; } },
    } } },
    Date: class extends Date { constructor(...a) { super(...(a.length ? a : [env.now])); } static now() { return env.now; } },
  });
  vm.runInContext(fs.readFileSync(path.resolve(__dirname, '..', process.env.CODE_GS || 'Code.gs'), 'utf8'), ctx);
  env.ctx = ctx;
  return env;
}

function hmac(secret, msg) { return crypto.createHmac('sha256', secret).update(msg).digest('hex'); }
function nonce() { return crypto.randomBytes(8).toString('hex'); }

// Appel signé ; `tweak` permet de falsifier l'enveloppe. Renvoie { raw, body, sigOk }.
function call(env, action, payload = {}, tweak = {}) {
  const payloadStr = typeof payload === 'string' ? payload : JSON.stringify(payload);
  const req = { v: 1, ts: Math.floor(env.now / 1000) + (tweak.tsOffset || 0), nonce: tweak.nonce || nonce(), action, payload: payloadStr };
  req.sig = hmac(tweak.secret || SECRET, [req.v, req.ts, req.nonce, req.action, req.payload].join('.'));
  if (tweak.badSig) req.sig = '0'.repeat(64);
  if (tweak.noSig) delete req.sig;
  const out = env.ctx.doPost({ postData: { contents: tweak.rawBody || JSON.stringify(req) } });
  const body = JSON.parse(out.text);
  let sigOk = null;
  if (body.sig) {
    const msg = body.ok ? [body.nonce, 'true', body.result].join('.') : [body.nonce, 'false', body.error.code].join('.');
    sigOk = hmac(SECRET, msg) === body.sig;
  }
  return { body, sigOk, req, result: body.ok ? JSON.parse(body.result) : null, code: body.ok ? null : body.error.code };
}

const rule = (o = {}) => Object.assign({ client_request_id: 'req-' + nonce(), from: 'news@exemple.com', destination: GOOD_DEST }, o);

module.exports = { makeEnv, call, rule, SECRET, GOOD_DEST, hmac };
