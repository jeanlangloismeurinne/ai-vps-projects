# Spec — Pilotage des règles de transfert Gmail (newsletter-summary)

Oct 31, 2026 · @P

## Statut et contexte

Cette spec décrit une idée discutée en conversation : rien de ce qui suit n'est implémenté ni vérifié sur le VPS. Elle sert de cahier des charges à Claude Code pour le sous-projet newsletter-summary, qui envoie chaque matin un digest résumé par IA via Resend.

La chaîne visée : abonnement aux newsletters avec l'adresse Gmail personnelle, filtre Gmail qui transfère vers une adresse de réception Resend (adresse standard de type xxx@id.resend.app, ou domaine personnel plus tard), webhook `email.received` vers le VPS. Il manque l'outil qui crée et gère ces filtres sans ouvrir Gmail.

Trois décisions déjà prises :

- **Gmail personnel**, pas de Google Workspace.
- **Adresses de transfert validées à la main** dans Gmail. Le système ne peut que choisir parmi elles, jamais en ajouter.
- **Pilotage par une web app Apps Script**, pas par un client OAuth Google Cloud : pas de jeton qui expire, pas de scope Gmail restreint à faire vérifier, et le code s'exécute dans le compte Gmail lui-même.

## Objectifs et périmètre

L'utilisateur doit pouvoir créer, lister, modifier, désactiver et supprimer des règles de transfert Gmail depuis une interface web sur le VPS, sans jamais ouvrir Gmail.

**Une règle** dit : les mails qui répondent à ces critères (expéditeur, sujet) sont transférés à cette adresse, choisie dans la liste des adresses de transfert déjà validées dans Gmail.

**Dans le périmètre**

- CRUD des règles, avec activation et désactivation sans perte.
- Liste des adresses de transfert autorisées et de leur statut, lue depuis Gmail.
- Synchronisation : détecter et corriger l'écart entre la base du VPS et les filtres réellement présents dans Gmail.
- Journal d'audit de chaque action.
- Tutoriel de paramétrage Gmail et Apps Script, fourni plus bas.

**Hors périmètre**

- Lire le contenu des mails depuis ce système (le script n'en a ni le droit ni le besoin).
- Ajouter ou valider une adresse de transfert : cela reste une action manuelle dans Gmail.
- Gérer d'autres paramètres Gmail (libellés, réponse automatique, délégués).
- Plusieurs comptes Gmail ou plusieurs utilisateurs (une seule instance, un seul propriétaire).

## Architecture

&#91;embedded content: architecture · 6 composants, 2 flux\]

Le VPS ne parle qu'au script, par un appel signé ; le script ne touche qu'aux filtres de Gmail. Le courrier suit un autre chemin : Gmail le transfère vers Resend, qui prévient le VPS par webhook. Le point de contrôle décisif est en surbrillance : seules les adresses validées à la main dans Gmail peuvent recevoir un transfert.

## Modèle de règle

Une règle a au moins un critère de sélection (expéditeur ou sujet), des exclusions optionnelles et une destination unique. La base du VPS est la source de vérité ; le filtre Gmail n'en est que la projection.

| Champ | Type | Contrainte | Correspondance Gmail |
| --- | --- | --- | --- |
| `id` | uuid | généré par le VPS | aucune |
| `name` | texte | libre, 80 caractères max | aucune |
| `enabled` | booléen | une règle désactivée n'a pas de filtre Gmail | existence du filtre |
| `from` | texte | adresse exacte ou domaine `@exemple.com` ; optionnel si le sujet est renseigné | `criteria.from` |
| `subject_contains` | texte | obligatoire si l'expéditeur est vide (6 caractères minimum), 120 maximum | `criteria.subject` |
| `exclude_words` | texte | optionnel, 120 caractères max | `criteria.negatedQuery` |
| `skip_inbox` | booléen | défaut faux : le mail reste dans la boîte de réception | `action.removeLabelIds: ["INBOX"]` |
| `destination` | texte | doit figurer dans les adresses de transfert au statut `accepted` | `action.forward` |
| `gmail_filter_id` | texte | renvoyé par le script, vide si désactivée | id du filtre |
| `sync_status` | liste | `synced`, `pending`, `drift`, `error` | calculé à la synchronisation |
| `created_at`, `updated_at` | dates | gérées par le VPS | aucune |

**Contraintes de validité, appliquées deux fois** (VPS puis script) :

- Au moins un critère positif : `from` ou `subject_contains`. `exclude_words` seul ne suffit pas, puisqu'il ne fait que retirer des mails.
- Si `from` est présent, il ne peut être ni un joker (`*`), ni un domaine nu de premier niveau (`@com`).
- Une règle sans expéditeur (sujet seul) est une règle large : sujet de 6 caractères minimum, 5 règles de ce type au plus, confirmation explicite dans l'interface. Le script ajoute lui-même à la règle l'exclusion des domaines de `DENY_FROM`, pour qu'elle ne puisse pas capter leurs mails.
- Pas de requête Gmail libre en v1 : les champs ci-dessus suffisent et limitent l'effet d'une règle trop large.
- Une seule règle par triplet `from` + `subject_contains` + `destination`.
- 50 règles actives au maximum.

**Modifier une règle.** L'API Gmail ne permet pas de mettre un filtre à jour. Le script crée d'abord le nouveau filtre, puis supprime l'ancien. Si la création réussit et la suppression échoue, la règle passe en `drift` et la synchronisation nettoie l'ancien filtre. Le contraire (supprimer d'abord) est interdit : il ouvrirait une fenêtre sans transfert.

**Les filtres étrangers.** Les filtres créés à la main dans Gmail n'appartiennent pas au système. Il peut les lister en lecture seule, jamais les modifier ni les supprimer.

## Contrat d'API du script

Le script expose sept actions et rien d'autre, toutes en POST sur l'URL `/exec` de la web app, avec une signature HMAC dans le corps. Apps Script ne donne pas accès aux en-têtes HTTP et renvoie toujours le statut 200 : l'authentification et les erreurs passent donc par le corps JSON.

**Enveloppe de requête** (`Content-Type: text/plain`, corps JSON) :

```json
{
  "v": 1,
  "ts": 1761900000,
  "nonce": "9f3a1c0b5d7e2a48",
  "action": "create_rule",
  "payload": "{\"client_request_id\":\"...\",\"from\":\"news@exemple.com\",\"destination\":\"veille@xxxx.resend.app\"}",
  "sig": "<hex>"
}
```

- `ts` : secondes Unix ; le script refuse tout écart supérieur à 60 secondes.
- `nonce` : 16 octets aléatoires en hexadécimal, jamais réutilisé dans les 10 minutes.
- `payload` : une chaîne JSON, pas un objet. On signe donc les octets exacts envoyés, sans canonisation.
- `sig` : HMAC-SHA256, en hexadécimal, de la chaîne `v.ts.nonce.action.payload` avec le secret partagé.

**Enveloppe de réponse** : `{"ok": true, "result": "<chaîne JSON>", "nonce": "...", "sig": "<hex>"}`, où `sig` est le HMAC de `nonce.true.result`. En cas d'erreur : `{"ok": false, "error": {"code": "...", "message": "..."}, "nonce": "...", "sig": "<hex>"}`, où `sig` est le HMAC de `nonce.false.code`. Le VPS vérifie cette signature avant d'utiliser la réponse. Seule une requête dont la signature est invalide reçoit une erreur non signée.

**Redirection.** Apps Script répond à un POST par une redirection 302 vers `script.googleusercontent.com`. Le client HTTP du VPS doit la suivre (comportement par défaut de `fetch`).

| Action | Payload | Résultat |
| --- | --- | --- |
| `ping` | aucun | version du script, heure serveur, état activé ou coupé |
| `list_forwarding_addresses` | aucun | liste `{email, status}` ; seules les adresses `accepted` sont sélectionnables |
| `list_rules` | `include_foreign` (booléen, défaut faux) | filtres gérés par le script, et en lecture seule les autres si demandé |
| `create_rule` | champs de la règle + `client_request_id` | `gmail_filter_id` |
| `replace_rule` | `gmail_filter_id` + nouveaux champs + `client_request_id` | nouvel `gmail_filter_id` (création puis suppression de l'ancien) |
| `delete_rule` | `gmail_filter_id` | `deleted: true` ; refus si le filtre n'est pas géré |
| `get_limits` | aucun | nombre de règles gérées, plafond, quota d'appels restant |

Le champ `client_request_id` rend la création idempotente : un rejeu avec le même identifiant renvoie le filtre déjà créé au lieu d'en créer un second.

**Codes d'erreur**

| Code | Cause |
| --- | --- |
| `bad_signature`, `stale_timestamp`, `replayed_nonce` | authentification refusée |
| `disabled` | interrupteur d'urgence activé |
| `rate_limited` | plus de 30 appels en écriture par heure, ou 120 en lecture |
| `invalid_action`, `invalid_payload` | action inconnue, champ manquant ou mal formé |
| `criteria_too_broad` | critères trop larges (voir Sécurité) |
| `destination_not_verified`, `destination_not_allowed` | adresse absente de Gmail ou hors liste blanche |
| `not_managed` | filtre non créé par le script |
| `rule_limit`, `duplicate` | plafond de 50 règles (ou de 5 sans expéditeur), ou doublon |
| `busy`, `internal` | verrou non obtenu, erreur Gmail ou interne |

## Sécurité

Le pire scénario est une personne qui obtient le droit d'appeler le script et crée un filtre qui transfère tout votre courrier vers son adresse. Les mesures ci-dessous s'empilent pour que ce scénario exige de franchir plusieurs barrières indépendantes, dont une (la validation manuelle des adresses) que le script ne peut pas contourner.

La web app doit être déployée avec **Exécuter en tant que : moi** et **Accès : tout le monde**. Le second réglage est imposé puisque le VPS n'a pas de session Google ; la protection repose donc entièrement sur ce qui suit.

| Menace | Mesure |
| --- | --- |
| URL de la web app découverte | Toute requête sans signature HMAC valide est rejetée avant le moindre appel Gmail. L'URL n'est jamais exposée au navigateur ni au dépôt. |
| Secret volé | Destinations limitées aux adresses validées à la main dans Gmail **et** à une liste blanche de domaines (`DEST_ALLOWED_DOMAINS`) : un attaquant ne peut rediriger que vers votre propre domaine de réception Resend. Rotation du secret possible à tout moment. |
| Rejeu d'une requête interceptée | Horodatage à 60 secondes près et nonce mémorisé 10 minutes (`CacheService`). |
| Règle trop large | `from` ou sujet requis (6 caractères minimum sans expéditeur), sans joker ni domaine de premier niveau. Règles sans expéditeur plafonnées à 5. Liste d'expéditeurs interdits (`DENY_FROM`) : banques, impôts, messagerie professionnelle, tout domaine du cabinet. Ces domaines sont aussi exclus automatiquement de chaque filtre. Refus `criteria_too_broad`. |
| Suppression de filtres manuels | Le script tient dans `PropertiesService` la liste des identifiants qu'il a créés. `delete_rule` et `replace_rule` refusent tout autre identifiant. |
| Abus ou boucle | 30 écritures et 120 lectures par heure, 50 règles au plus, `LockService` sur les écritures pour éviter les courses. |
| Permissions excessives | Le manifeste déclare le seul scope `gmail.settings.basic`. Le script ne peut ni lire ni envoyer de mail. |
| Secret en clair | Stocké dans les propriétés du script côté Google, et comme secret chiffré du déploiement côté VPS. 32 octets aléatoires, jamais dans le dépôt, les journaux ni le navigateur. |
| Interface du VPS attaquée | HTTPS, authentification propre à l'interface, cookies `HttpOnly` `Secure` `SameSite=Strict`, jeton CSRF sur chaque écriture, limitation des tentatives de connexion. Seul le backend appelle le script. |
| Modification silencieuse | Le VPS compare chaque jour `list_rules` à sa base. Tout écart non expliqué passe la règle en `drift` et déclenche une alerte. Les exécutions restent visibles dans la page Exécutions d'Apps Script. |
| Compte Google compromis | Hors du script, mais décisif : validation en deux étapes ou clé d'accès sur le compte, aucun collaborateur sur le projet Apps Script. |

**Coupure d'urgence** (à tester une fois à blanc) :

1. Dans l'éditeur Apps Script, exécuter `panic()` : elle supprime tous les filtres gérés et active `DISABLED`.
2. Menu Déployer, Gérer les déploiements : archiver le déploiement. L'URL cesse de répondre.
3. Générer un nouveau secret et le remplacer des deux côtés.
4. Dans Gmail, supprimer l'adresse de transfert si elle est en cause.
5. Sur la page des accès du compte Google, révoquer l'autorisation du script.

## Interface

L'interface tient en quatre écrans, utilisables sur téléphone, et ajoute une page dans le sous-projet newsletter-summary plutôt qu'une application séparée.

**1. Liste des règles** (page d'accueil)

- Tableau : nom, expéditeur, destination, interrupteur activé, état de synchronisation (`synced`, `pending`, `drift`, `error`), actions modifier et supprimer.
- Recherche par expéditeur ou par nom, filtre par destination et par état.
- Bandeau d'état : réponse du script au dernier `ping`, date de la dernière synchronisation, nombre de règles sur 50.

**2. Formulaire de règle** (création et édition)

- Champs : nom, expéditeur, sujet contient, mots à exclure, case « ne pas laisser dans la boîte de réception », destination. L'expéditeur ou le sujet doit être rempli.
- La destination est un menu alimenté par `list_forwarding_addresses`. Les adresses non `accepted` apparaissent grisées, avec le renvoi vers le tutoriel.
- Avertissement si l'expéditeur est un domaine entier, refus immédiat s'il contient un joker ou figure dans `DENY_FROM`.
- Règle sans expéditeur : bandeau d'alerte et case de confirmation obligatoire (« cette règle peut transférer des mails de n'importe quel expéditeur »), dans la limite de 5 règles de ce type.
- Aperçu en clair de ce que Gmail va faire : « Les mails de X sont transférés à Y ».

**3. Synchronisation**

- Bouton « Synchroniser maintenant » : appelle `list_rules` et classe les écarts.
- Règle de la base absente de Gmail : recréer ou supprimer de la base.
- Filtre géré par le script mais inconnu de la base : supprimer ou adopter.
- Filtres étrangers : liste en lecture seule, sans action.

**4. Adresses et journal**

- Adresses de transfert avec leur statut, et rappel de la procédure pour en ajouter une dans Gmail.
- Journal d'audit filtrable : date, action, règle, résultat, code d'erreur éventuel.
- Bouton « Tester la connexion » et date de la dernière rotation du secret, avec un rappel visuel après six mois.

**Parcours d'écriture.** Créer : l'interface enregistre la règle en `pending`, appelle `create_rule`, puis passe en `synced` ou en `error` avec un bouton Réessayer. Modifier : `replace_rule`. Désactiver : `delete_rule` sur le filtre, la règle reste en base ; réactiver rappelle `create_rule`. Supprimer : confirmation, puis `delete_rule` et suppression en base, l'historique restant dans le journal.

## Backend VPS

Le backend valide chaque demande, écrit son intention en base, puis signe et envoie l'appel au script. Il réutilise la pile, le stockage et l'authentification déjà présents dans newsletter-summary (à vérifier, voir la dernière section) ; à défaut, une base SQLite suffit pour 50 règles.

| Route | Rôle |
| --- | --- |
| `GET /api/rules` | liste des règles avec leur état |
| `POST /api/rules` | création (`pending`, puis `create_rule`) |
| `PUT /api/rules/{id}` | modification (`replace_rule`) |
| `PATCH /api/rules/{id}/enabled` | activation ou désactivation |
| `DELETE /api/rules/{id}` | suppression (`delete_rule`, puis base) |
| `GET /api/forwarding-addresses` | adresses de transfert, mises en cache 5 minutes |
| `POST /api/sync` | synchronisation à la demande |
| `GET /api/audit` | journal d'audit |
| `POST /api/script/ping` | test de la connexion au script |

**Configuration** (variables d'environnement, secrets dans le gestionnaire de secrets du déploiement) : `GMAIL_SCRIPT_URL`, `GMAIL_SCRIPT_SECRET`, `DEST_ALLOWED_DOMAINS`, `DENY_FROM`, `SECRET_ROTATED_AT`.

**Robustesse des appels.** Le client attend au plus 30 secondes, suit la redirection et vérifie la signature de la réponse. Il ne réessaie que les appels idempotents : création avec le même `client_request_id`, suppression (un filtre déjà absent compte comme un succès). Une écriture jamais confirmée laisse la règle en `pending`, jamais en `synced` par hypothèse.

**Réconciliation.** Elle compare la base à `list_rules` :

- Règle active, filtre présent et critères identiques : `synced`.
- Règle active dont le filtre manque ou a été modifié : `drift`.
- Règle désactivée dont le filtre existe encore : `drift`.
- Filtre géré sans règle en base : orphelin, signalé à l'utilisateur.

La tâche quotidienne ne fait que détecter et alerter. Toute correction passe par un clic de l'utilisateur.

La comparaison porte sur `from`, `subject` et la destination. `negatedQuery` est exclu du test, car le script y ajoute lui-même la clause `DENY_FROM`.

**Journal d'audit.** Une ligne par action : horodatage, acteur, action, identifiant de règle, `client_request_id`, résultat, code d'erreur, empreinte du payload. Jamais le secret ni la signature. Conservation de douze mois.

**Alertes.** Un écart non expliqué, trois échecs d'authentification consécutifs du script ou un secret de plus de six mois produisent une alerte par e-mail Resend à l'adresse du propriétaire.

## Tutoriel de paramétrage Gmail et Apps Script

Ce tutoriel se fait une fois, dans l'ordre. Il faut environ 20 minutes. Une attente de propagation DNS n'intervient que si vous utilisez votre propre domaine.

### Étape 1 — Préparer la réception chez Resend

1. Dans Resend, ouvrir la page des e-mails reçus (onglet Receiving), puis le menu à trois points et **Inbound address** : Resend fournit un domaine de la forme `xxxx.resend.app`, créé automatiquement. Tout mail envoyé à n'importe quel nom devant ce domaine est reçu par Resend.
2. Choisir le nom avant le `@`, par exemple `veille@xxxx.resend.app`. Aucun enregistrement DNS n'est nécessaire.
3. Créer dans Resend (page Webhooks) un webhook sur l'événement `email.received` pointant vers le VPS. Tant qu'il n'est pas en place, les mails restent visibles dans le tableau de bord.
4. Option pour plus tard, avec votre propre domaine : ajouter dans Resend un sous-domaine de réception (`inbound.<votre domaine>`), créer chez l'hébergeur DNS l'enregistrement MX indiqué par Resend sur ce sous-domaine, jamais sur le domaine racine, puis faire vérifier le domaine. Les adresses deviennent alors `xxx@inbound.<votre domaine>`.

### Étape 2 — Autoriser l'adresse de transfert dans Gmail

C'est l'étape manuelle que le système ne peut pas faire à votre place, et c'est voulu.

1. Dans Gmail, ouvrir Paramètres (la roue), puis **Voir tous les paramètres**, onglet **Transfert et POP/IMAP**.
2. Cliquer sur **Ajouter une adresse de transfert**, saisir `veille@xxxx.resend.app`, puis valider.
3. Gmail envoie un mail de confirmation à cette adresse. Il arrive chez Resend : l'ouvrir dans le tableau de bord (réception) et cliquer sur le lien de confirmation, connecté au compte Gmail concerné.
4. Revenir dans l'onglet Transfert et POP/IMAP : l'adresse doit apparaître comme confirmée.
5. **Laisser la case « Désactiver le transfert » cochée.** Ne jamais activer « Transférer une copie des mails entrants » : cela enverrait tout le courrier. Seuls les filtres du système doivent transférer.
6. Répéter pour chaque autre destination utile.

### Étape 3 — Créer le projet Apps Script

1. Ouvrir script.google.com avec le compte Gmail concerné, cliquer sur **Nouveau projet** et le nommer `newsletter-forward-api`.
2. À gauche, à côté de **Services**, cliquer sur **+**, choisir **Gmail API**, laisser l'identifiant `Gmail`, puis **Ajouter**.
3. Dans **Paramètres du projet** (la roue), cocher **Afficher le fichier manifeste « appsscript.json » dans l'éditeur**.
4. Ouvrir `appsscript.json` et le remplacer par le manifeste de la section suivante, qui réduit les autorisations au strict nécessaire.
5. Dans `Code.gs`, coller le script de référence de la section suivante.

### Étape 4 — Configurer les secrets et les listes

1. Générer un secret de 32 octets aléatoires sur le VPS, par exemple avec `openssl rand -hex 32`. Le conserver dans le gestionnaire de secrets du déploiement, pas dans le dépôt.
2. Dans Apps Script, **Paramètres du projet**, section **Propriétés du script**, ajouter :
   - `HMAC_SECRET` : le secret généré ;
   - `DEST_ALLOWED_DOMAINS` : `xxxx.resend.app` (plusieurs valeurs séparées par des virgules) ;
   - `DENY_FROM` : les domaines à ne jamais transférer, par exemple celui de votre messagerie professionnelle et vos banques ;
   - `DISABLED` : `false`.

### Étape 5 — Autoriser et déployer

1. Dans l'éditeur, sélectionner la fonction `authorize` et cliquer sur **Exécuter**. Google affiche « application non vérifiée » : c'est votre propre script, choisir **Avancé**, puis **Accéder à newsletter-forward-api**, et accepter. L'unique autorisation demandée doit concerner les paramètres Gmail (filtres et transferts). Si l'écran liste la lecture des mails, le manifeste n'a pas été appliqué : refuser et corriger.
2. Cliquer sur **Déployer**, puis **Nouveau déploiement**, type **Application Web**.
3. Régler **Exécuter en tant que : Moi** et **Qui a accès : Tout le monde**, puis déployer.
4. Copier l'URL se terminant par `/exec` dans `GMAIL_SCRIPT_URL` sur le VPS, avec le secret dans `GMAIL_SCRIPT_SECRET`.
5. Pour toute modification ultérieure du code : **Déployer**, **Gérer les déploiements**, modifier le déploiement existant et choisir une nouvelle version. Un nouveau déploiement génère une autre URL.

### Étape 6 — Vérifier

1. Depuis l'interface, bouton **Tester la connexion** : le `ping` doit répondre avec la version du script.
2. L'écran des adresses doit lister `veille@xxxx.resend.app` au statut `accepted`.
3. Créer une règle de test avec une de vos autres adresses comme expéditeur, s'envoyer un mail depuis celle-ci, et vérifier qu'il arrive dans la réception Resend.
4. Dans Gmail, Paramètres, **Filtres et adresses bloquées** : le filtre créé doit apparaître avec l'action de transfert. Supprimer ensuite la règle de test depuis l'interface et vérifier que le filtre a disparu.
5. Tester la coupure d'urgence une fois à blanc : exécuter `panic()`, constater que l'interface signale le script coupé, puis remettre `DISABLED` à `false`.

### Entretien

- Tourner le secret tous les six mois : le générer, le remplacer d'abord dans Apps Script, puis dans le déploiement du VPS, puis mettre à jour `SECRET_ROTATED_AT`.
- Garder la validation en deux étapes (ou une clé d'accès) sur le compte Google : le script s'exécute avec ses droits.

## Script de référence

Ce code est une base à relire et à tester avant usage, pas un produit validé : il n'a jamais été exécuté. Il applique le contrat et les mesures des sections précédentes. Claude Code doit le reprendre, l'exécuter contre un compte Gmail de test et corriger les écarts avec l'API réelle.

**`appsscript.json`** : un seul scope, aucun accès à la lecture des mails.

```json
{
  "timeZone": "Europe/Paris",
  "runtimeVersion": "V8",
  "exceptionLogging": "STACKDRIVER",
  "dependencies": {
    "enabledAdvancedServices": [
      { "userSymbol": "Gmail", "serviceId": "gmail", "version": "v1" }
    ]
  },
  "oauthScopes": ["https://www.googleapis.com/auth/gmail.settings.basic"],
  "webapp": { "executeAs": "USER_DEPLOYING", "access": "ANYONE_ANONYMOUS" }
}
```

**`Code.gs`**

```javascript
// newsletter-forward-api v1.0.0
const VERSION = '1.0.0';
const MAX_RULES = 50;
const MAX_SENDERLESS = 5; // règles sans expéditeur
const TS_WINDOW_S = 60;
const NONCE_TTL_S = 600;
const LIMITS = { read: 120, write: 30 }; // appels par heure
const WRITE_ACTIONS = ['create_rule', 'replace_rule', 'delete_rule'];

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
      .map(f => ({ id: f.id, managed: !!managed[f.id], criteria: f.criteria || {}, action: f.action || {} }));
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
  const subject = clean_(p.subject_contains, 120);
  if (!from && subject.length < 6) throw err_('criteria_too_broad', 'Critère insuffisant : expéditeur, ou sujet de 6 caractères');
  const dest = String(p.destination || '').trim().toLowerCase();
  if (csv_('DEST_ALLOWED_DOMAINS').indexOf(dest.split('@')[1] || '') < 0) {
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
    .map(s => s.trim().toLowerCase()).filter(Boolean);
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
```

**Choix de conception à conserver**

- La signature est vérifiée avant tout accès à Gmail, avec une comparaison à durée constante.
- Les erreurs après authentification sont elles aussi signées (`nonce.false.code`), pour que le VPS ne se fie jamais à une réponse non authentifiée.
- Le cache des nonces est un mécanisme au mieux (Google peut le vider) ; la fenêtre de 60 secondes sur l'horodatage borne le risque de rejeu même dans ce cas.
- Le quota horaire est conservé dans les propriétés du script, donc durable.
- Si la création d'un filtre réussit mais que l'enregistrement de son identifiant échoue, le filtre apparaît comme étranger : la synchronisation le signale, et le rejeu avec le même `client_request_id` ne le retrouve pas. C'est un cas rare à traiter dans les tests.
- Rien n'est journalisé hormis les erreurs internes, sans payload ni secret.

## Tests et critères d'acceptation

Le système est accepté quand une règle créée depuis le téléphone fait arriver un vrai mail de test dans la réception Resend sans ouvrir Gmail, et que tous les tests de sécurité ci-dessous passent. Les tests du script se font sur un compte Gmail de test, pas sur le compte réel.

**Script (sécurité et robustesse)**

| Test | Résultat attendu |
| --- | --- |
| Requête sans signature, ou avec une signature fausse | `bad_signature`, aucune trace d'appel Gmail dans la page Exécutions |
| Horodatage décalé de 120 secondes | `stale_timestamp` |
| Même nonce envoyé deux fois | `replayed_nonce` à la seconde |
| Destination hors liste blanche de domaines | `destination_not_allowed` |
| Destination du bon domaine mais non validée dans Gmail | `destination_not_verified` |
| Expéditeur vide, `*`, `@com` ou dans `DENY_FROM` | `criteria_too_broad` |
| `delete_rule` sur un filtre créé à la main | `not_managed`, filtre intact |
| `create_rule` rejouée avec le même `client_request_id` | un seul filtre dans Gmail |
| 31e écriture dans l'heure, 51e règle | `rate_limited`, `rule_limit` |
| `replace_rule` avec panne simulée après la création | ancien et nouveau filtres présents, `drift` côté VPS, nettoyage à la synchronisation |
| `panic()` | filtres gérés supprimés, filtres manuels intacts, appels suivants refusés avec `disabled` |
| Écran d'autorisation Google | demande uniquement les paramètres Gmail |
| Filtre sur un domaine entier (`@exemple.com`) | un mail réel de ce domaine est bien transféré |
| Règle sans expéditeur avec un sujet de moins de 6 caractères, puis 6e règle sans expéditeur | criteria\_too\_broad, puis rule\_limit |
| Règle sans expéditeur : mail d'un domaine de DENY\_FROM dont le sujet correspond | mail non transféré (clause d'exclusion ajoutée par le script) |

**Backend et interface**

| Test | Résultat attendu |
| --- | --- |
| Cycle complet : créer, modifier, désactiver, réactiver, supprimer | filtre Gmail cohérent à chaque étape, journal d'audit complet |
| Réponse du script avec signature falsifiée | rejetée par le VPS, règle laissée en `pending` |
| Script injoignable ou timeout | message clair, règle en `pending` ou `error`, bouton Réessayer |
| Filtre supprimé à la main dans Gmail | détecté en `drift`, alerte, correction à la demande seulement |
| Filtre géré inconnu de la base | signalé comme orphelin |
| Requête d'écriture sans jeton CSRF, ou session expirée | refus 403 ou retour à la connexion |
| Recherche du secret dans le dépôt, les journaux et les réponses HTTP | aucune occurrence |
| Rotation du secret | l'ancien secret est refusé par le script |
| Utilisation sur téléphone | formulaire et liste utilisables sans zoom horizontal |

## Points ouverts et vérifications à faire

Rien de ce qui suit n'a été vérifié : ce sont des hypothèses de la spec que Claude Code doit confirmer ou corriger avant d'écrire du code, en notant dans le dépôt ce qui est constaté et ce qui reste une idée.

**À constater sur le VPS (phase 0)**

1. La pile du sous-projet newsletter-summary : langage, framework, base de données, structure du dépôt.
2. L'authentification de l'interface existante. Sans elle, en créer une avant toute route d'écriture (session, HTTPS, CSRF) : l'interface pilote l'accès à votre courrier.
3. Le gestionnaire de secrets du déploiement et la façon d'y poser `GMAIL_SCRIPT_SECRET`.
4. L'état de la réception Resend : domaine de réception déjà en place ou non, webhook `email.received` déjà traité ou non, et où.
5. L'envoi d'alertes : réutiliser l'envoi Resend déjà utilisé pour le digest, si c'est bien le cas.

**À confirmer au premier test côté Gmail et Apps Script**

6. Que le seul scope `gmail.settings.basic` suffit pour lister les adresses de transfert, créer un filtre avec transfert et le supprimer. Sinon, documenter le scope minimal réel.
7. Que `criteria.from` accepte bien la forme `@domaine.tld`.
8. Qu'avec un compte personnel et l'accès « Tout le monde », l'URL répond sans connexion Google, et le délai habituel d'un appel (redirection comprise).
9. Les quotas d'exécution d'Apps Script du compte et les limites de Gmail sur le nombre de filtres et d'adresses de transfert.
10. La forme exacte des erreurs de l'API Gmail, pour affiner `removeFilter_` et les messages.

**Risque propre au domaine `.resend.app`** : certaines newsletters peuvent refuser ou classer en spam un domaine générique. Tester avec trois ou quatre abonnements réels avant de généraliser ; en cas de refus, passer au domaine personnel (tutoriel, étape 1, option).

**À tester aussi** : que `negatedQuery` accepte la clause `from:(@domaine1 OR @domaine2)` ajoutée par le script, et que sa longueur reste acceptée par Gmail quand `DENY_FROM` est long.

**Décisions à prendre par l'utilisateur**

- Contenu initial de `DENY_FROM` : quels domaines ne jamais transférer.
- Une seule adresse de destination au départ, ou plusieurs par famille de sources.
- Faut-il appliquer un libellé Gmail aux mails transférés pour les retrouver ?
- Refuser les suffixes publics à deux niveaux (`@co.uk`) comme domaines entiers, ou les accepter ?

**Idée pour une version 2** : afficher, pour chaque règle, la date du dernier mail reçu par le webhook. Une newsletter qui change d'adresse d'expédition cesse d'arriver sans erreur, et cet indicateur la rend visible.

**Ordre de réalisation**

1. Audit du VPS et de l'existant (phase 0).
2. Script et tutoriel, testés de bout en bout sur un compte Gmail de test.
3. Backend : routes, client signé, journal d'audit.
4. Interface : liste, formulaire, adresses.
5. Synchronisation, alertes et rotation du secret.
6. Recette avec les tests de la section précédente, puis mise en service sur le compte réel.
