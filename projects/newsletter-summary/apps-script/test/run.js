// node apps-script/test/run.js  → BILAN script : N/N verts   (CODE_GS=… pour exécuter une variante mutée)
const assert = require('assert');
const { makeEnv, call, rule, GOOD_DEST } = require('./harness');

const tests = [];
const t = (name, fn) => tests.push([name, fn]);
const create = (env, o) => call(env, 'create_rule', rule(o));

t('requête sans signature ou signature fausse → bad_signature, Gmail intact', () => {
  const env = makeEnv();
  for (const tweak of [{ badSig: true }, { noSig: true }, { secret: 'b'.repeat(64) }]) {
    const r = call(env, 'list_rules', {}, tweak);
    assert.strictEqual(r.body.ok, false);
    assert.ok(['bad_signature', 'invalid_payload'].includes(r.code), r.code);
    assert.strictEqual(r.body.sig, undefined, 'une erreur d\'authentification ne doit pas être signée');
  }
  assert.deepStrictEqual(env.gmailCalls, [], 'aucun appel Gmail avant authentification');
});
t('JSON illisible → invalid_payload non signé, Gmail intact', () => {
  const env = makeEnv();
  const r = call(env, 'ping', {}, { rawBody: '{pas du json' });
  assert.strictEqual(r.code, 'invalid_payload'); assert.deepStrictEqual(env.gmailCalls, []);
});
t('secret absent ou trop court → internal', () => {
  const env = makeEnv({ props: { HMAC_SECRET: 'court' } });
  assert.strictEqual(call(env, 'ping', {}, { secret: 'court' }).code, 'internal');
});
t('horodatage décalé de 120 s → stale_timestamp (réponse signée)', () => {
  const env = makeEnv();
  const r = call(env, 'ping', {}, { tsOffset: -120 });
  assert.strictEqual(r.code, 'stale_timestamp'); assert.strictEqual(r.sigOk, true);
  assert.strictEqual(call(env, 'ping', {}, { tsOffset: 30 }).body.ok, true);
});
t('même nonce deux fois → replayed_nonce', () => {
  const env = makeEnv();
  assert.strictEqual(call(env, 'ping', {}, { nonce: 'abcdef0123456789' }).body.ok, true);
  assert.strictEqual(call(env, 'ping', {}, { nonce: 'abcdef0123456789' }).code, 'replayed_nonce');
});
t('verrou occupé → busy signé', () => {
  const env = makeEnv(); env.lockBusy = true;
  const r = call(env, 'ping'); assert.strictEqual(r.code, 'busy'); assert.strictEqual(r.sigOk, true);
});
t('action inconnue (dont héritée de Object) → invalid_action', () => {
  const env = makeEnv();
  for (const a of ['rm_rf', 'constructor', '__proto__', 'toString']) assert.strictEqual(call(env, a).code, 'invalid_action', a);
});
t('payload non-JSON authentifié → invalid_payload signé', () => {
  const env = makeEnv(); const r = call(env, 'create_rule', '{oups');
  assert.strictEqual(r.code, 'invalid_payload'); assert.strictEqual(r.sigOk, true);
});
t('ping et réponse de succès signées', () => {
  const env = makeEnv(); const r = call(env, 'ping');
  assert.strictEqual(r.sigOk, true); assert.strictEqual(r.result.enabled, true); assert.ok(r.result.version);
});
t('destination hors liste blanche de domaines → destination_not_allowed', () => {
  const env = makeEnv();
  assert.strictEqual(create(env, { destination: 'pirate@evil.com' }).code, 'destination_not_allowed');
  assert.strictEqual(create(env, { destination: 'pirate@evil.com@xxxx.resend.app' }).code, 'destination_not_allowed');
  assert.strictEqual(env.filters.length, 0);
});
t('destination du bon domaine mais non validée → destination_not_verified', () => {
  const env = makeEnv();
  assert.strictEqual(create(env, { destination: 'inconnue@xxxx.resend.app' }).code, 'destination_not_verified');
  assert.strictEqual(create(env, { destination: 'attente@xxxx.resend.app' }).code, 'destination_not_verified');
  assert.strictEqual(env.filters.length, 0);
});
t('expéditeur invalide : *, @com, @co.uk, DENY_FROM (domaine et sous-domaine) → criteria_too_broad', () => {
  const env = makeEnv();
  for (const from of ['*', '@com', 'com', '@co.uk', '@ac.uk', 'a@banque.fr', '@banque.fr', '@mail.banque.fr', '@cabinet.com', 'x y@z.fr'])
    assert.strictEqual(create(env, { from }).code, 'criteria_too_broad', from);
  assert.strictEqual(env.filters.length, 0);
  assert.strictEqual(create(env, { from: '@exemple.co.uk' }).body.ok, true);
});
t('ni expéditeur ni sujet / sujet < 6 caractères → criteria_too_broad', () => {
  const env = makeEnv();
  assert.strictEqual(create(env, { from: '' }).code, 'criteria_too_broad');
  assert.strictEqual(create(env, { from: '', subject_contains: 'abc' }).code, 'criteria_too_broad');
  assert.strictEqual(create(env, { from: '', exclude_words: 'promo mots' }).code, 'criteria_too_broad');
  assert.strictEqual(create(env, { from: '', subject_contains: 'abcdef' }).body.ok, true);
});
t('texte avec caractères de requête Gmail (guillemets, parenthèses) → invalid_payload', () => {
  const env = makeEnv();
  for (const exclude_words of ['a" OR from:(x', 'a) OR (b', '-{x}'])
    assert.strictEqual(create(env, { exclude_words }).code, 'invalid_payload', exclude_words);
  assert.strictEqual(create(env, { subject_contains: 'x'.repeat(121) }).code, 'invalid_payload');
});
t('create_rule : filtre Gmail conforme (forward, from, exclusion DENY_FROM, skip_inbox)', () => {
  const env = makeEnv();
  const r = create(env, { from: '@exemple.com', subject_contains: 'Edition', exclude_words: 'promo', skip_inbox: true });
  assert.strictEqual(r.body.ok, true);
  const f = env.filters[0];
  assert.strictEqual(f.action.forward, GOOD_DEST); assert.deepStrictEqual(f.action.removeLabelIds, ['INBOX']);
  assert.strictEqual(f.criteria.from, '@exemple.com'); assert.strictEqual(f.criteria.subject, 'Edition');
  assert.strictEqual(f.criteria.negatedQuery, '(promo) OR from:(@banque.fr OR @cabinet.com)');
  const g = create(env, { from: 'autre@exemple.com' }); assert.strictEqual(g.body.ok, true);
  assert.strictEqual(env.filters[1].action.removeLabelIds, undefined, 'skip_inbox faux par défaut');
});
t('règle sans expéditeur : exclusion DENY_FROM ajoutée par le script', () => {
  const env = makeEnv();
  create(env, { from: '', subject_contains: 'Newsletter hebdo' });
  assert.strictEqual(env.filters[0].criteria.negatedQuery, 'from:(@banque.fr OR @cabinet.com)');
  assert.strictEqual(env.filters[0].criteria.from, undefined);
});
t('create_rule rejouée avec le même client_request_id → un seul filtre', () => {
  const env = makeEnv(); const p = rule();
  const a = call(env, 'create_rule', p), b = call(env, 'create_rule', p);
  assert.strictEqual(a.result.gmail_filter_id, b.result.gmail_filter_id); assert.strictEqual(b.result.replayed, true);
  assert.strictEqual(env.filters.length, 1);
});
t('doublon from+sujet+destination → duplicate', () => {
  const env = makeEnv(); create(env, { from: 'a@b.fr' });
  assert.strictEqual(create(env, { from: 'A@B.fr' }).code, 'duplicate'); assert.strictEqual(env.filters.length, 1);
});
t('delete_rule / replace_rule sur filtre étranger → not_managed, filtre intact', () => {
  const env = makeEnv();
  env.filters.push({ id: 'MAIN', criteria: { from: 'ami@x.fr' }, action: { addLabelIds: ['STARRED'] } });
  assert.strictEqual(call(env, 'delete_rule', { gmail_filter_id: 'MAIN' }).code, 'not_managed');
  assert.strictEqual(call(env, 'replace_rule', rule({ gmail_filter_id: 'MAIN' })).code, 'not_managed');
  assert.strictEqual(call(env, 'delete_rule', { gmail_filter_id: '' }).code, 'not_managed');
  assert.strictEqual(env.filters.length, 1);
});
t('list_rules : filtres étrangers masqués par défaut, visibles en lecture seule sur demande', () => {
  const env = makeEnv();
  env.filters.push({ id: 'MAIN', criteria: { from: 'ami@x.fr' }, action: {} });
  const mine = create(env).result.gmail_filter_id;
  const a = call(env, 'list_rules', {}).result; assert.deepStrictEqual(a.map(x => x.id), [mine]);
  assert.ok(a[0].client_request_id);
  const b = call(env, 'list_rules', { include_foreign: true }).result;
  assert.deepStrictEqual(b.map(x => [x.id, x.managed]).sort(), [['MAIN', false], [mine, true]].sort());
});
t('delete_rule : supprime, puis un filtre déjà absent compte comme un succès', () => {
  const env = makeEnv(); const id = create(env).result.gmail_filter_id;
  assert.deepStrictEqual(call(env, 'delete_rule', { gmail_filter_id: id }).result, { deleted: true });
  assert.strictEqual(env.filters.length, 0);
  env.store.MANAGED = JSON.stringify({ GONE: 'req-xxxxxxxx' });
  assert.deepStrictEqual(call(env, 'delete_rule', { gmail_filter_id: 'GONE' }).result, { deleted: true });
  assert.strictEqual(env.store.MANAGED, '{}');
});
t('replace_rule : crée d\'abord, supprime ensuite (ordre des appels Gmail)', () => {
  const env = makeEnv(); const old = create(env).result.gmail_filter_id;
  env.gmailCalls.length = 0;
  const r = call(env, 'replace_rule', rule({ gmail_filter_id: old, from: 'nouveau@exemple.com' }));
  assert.strictEqual(r.body.ok, true);
  assert.ok(env.gmailCalls.indexOf('filters.create') < env.gmailCalls.indexOf('filters.remove'), env.gmailCalls.join());
  assert.deepStrictEqual(env.filters.map(f => f.criteria.from), ['nouveau@exemple.com']);
});
t('replace_rule avec panne de suppression → ancien ET nouveau présents, tous deux gérés', () => {
  const env = makeEnv(); const old = create(env).result.gmail_filter_id;
  env.failNextRemove = true;
  const r = call(env, 'replace_rule', rule({ gmail_filter_id: old, from: 'nouveau@exemple.com' }));
  assert.strictEqual(r.code, 'internal');
  assert.strictEqual(env.filters.length, 2, 'jamais de fenêtre sans transfert');
  const listed = call(env, 'list_rules', {}).result;
  assert.strictEqual(listed.length, 2, 'le nouveau filtre créé est connu comme géré (orphelin détectable)');
});
t('panne de création → aucune fenêtre ouverte, ancien filtre intact', () => {
  const env = makeEnv(); const old = create(env).result.gmail_filter_id;
  env.failCreate = true;
  assert.strictEqual(call(env, 'replace_rule', rule({ gmail_filter_id: old, from: 'n@exemple.com' })).code, 'internal');
  assert.strictEqual(env.filters.length, 1); assert.strictEqual(env.filters[0].id, old);
});
t('31e écriture dans l\'heure → rate_limited ; la lecture a son propre quota', () => {
  const env = makeEnv();
  for (let i = 0; i < 30; i++) assert.strictEqual(call(env, 'delete_rule', { gmail_filter_id: 'X' + i }).code, 'not_managed');
  assert.strictEqual(call(env, 'delete_rule', { gmail_filter_id: 'X' }).code, 'rate_limited');
  assert.strictEqual(call(env, 'ping').body.ok, true);
  env.now += 3600 * 1000 + 1000;
  assert.strictEqual(call(env, 'delete_rule', { gmail_filter_id: 'X' }).code, 'not_managed', 'le quota repart à l\'heure suivante');
});
t('121e lecture dans l\'heure → rate_limited', () => {
  const env = makeEnv();
  for (let i = 0; i < 120; i++) assert.strictEqual(call(env, 'ping').body.ok, true);
  assert.strictEqual(call(env, 'ping').code, 'rate_limited');
});
t('51e règle → rule_limit', () => {
  const env = makeEnv();
  env.store.MANAGED = JSON.stringify(Object.fromEntries(Array.from({ length: 50 }, (_, i) => ['F' + i, 'req-' + String(i).padStart(8, '0')])));
  assert.strictEqual(create(env, { from: 'z@z.fr' }).code, 'rule_limit');
});
t('6e règle sans expéditeur → rule_limit (la 5e passe)', () => {
  const env = makeEnv();
  for (let i = 0; i < 5; i++) assert.strictEqual(create(env, { from: '', subject_contains: 'Sujet numéro ' + i }).body.ok, true, 'règle ' + i);
  assert.strictEqual(create(env, { from: '', subject_contains: 'Sujet numéro 6' }).code, 'rule_limit');
  assert.strictEqual(create(env, { from: 'a@b.fr' }).body.ok, true, 'avec expéditeur, pas concerné');
});
t('panic() : filtres gérés supprimés, manuels intacts, appels suivants refusés (sauf ping)', () => {
  const env = makeEnv();
  env.filters.push({ id: 'MAIN', criteria: { from: 'ami@x.fr' }, action: {} });
  create(env, { from: 'a@b.fr' }); create(env, { from: 'c@d.fr' });
  env.ctx.panic();
  assert.deepStrictEqual(env.filters.map(f => f.id), ['MAIN']);
  assert.strictEqual(call(env, 'create_rule', rule()).code, 'disabled'); assert.strictEqual(call(env, 'list_rules').code, 'disabled');
  const p = call(env, 'ping'); assert.strictEqual(p.result.enabled, false);
});
t('échec d\'enregistrement de l\'identifiant : le filtre apparaît comme étranger (cas documenté)', () => {
  const env = makeEnv(); env.failNextSetManaged = true;
  assert.strictEqual(create(env).code, 'internal');
  assert.strictEqual(env.filters.length, 1);
  assert.strictEqual(call(env, 'list_rules', {}).result.length, 0);
  assert.strictEqual(call(env, 'list_rules', { include_foreign: true }).result[0].managed, false);
});
t('get_limits et list_forwarding_addresses', () => {
  const env = makeEnv(); create(env);
  const l = call(env, 'get_limits').result; assert.strictEqual(l.managed, 1); assert.strictEqual(l.max_rules, 50);
  assert.deepStrictEqual(call(env, 'list_forwarding_addresses').result.map(a => a.status), ['accepted', 'pending']);
});

let ok = 0;
for (const [name, fn] of tests) {
  try { fn(); ok++; console.log('VERT   ' + name); }
  catch (e) { console.log('ROUGE  ' + name + '\n       ' + String(e.message).split('\n')[0]); }
}
console.log(`BILAN script : ${ok}/${tests.length} verts`);
process.exit(ok === tests.length ? 0 : 1);
