# DECISIONS.md — faits durables, réutilisables d'un projet à l'autre

> Gotchas vérifiés, chacun avec **une** mesure en preuve. Versionné, greppable, jamais
> auto-chargé. Le récit reste dans les `00-REPRISE-ARCHIVE.md` ; ici, seulement ce qui
> changerait ce qu'un agent fait sur un autre fichier ou un autre projet.
> Conventions (ce qu'on fait) → `CLAUDE.md`. Gotchas (ce qui pique) → ici.

---

## #1 — FastAPI : une valeur de `Form` vide est traitée comme un champ ABSENT (422)

Un `<option value="">` dans un formulaire posté vers une route déclarant `champ: str = Form(...)`
renvoie **422**, pas une chaîne vide : FastAPI assimile la valeur vide à un champ manquant.

**Mesuré** (Hub, `app/roadmap.py`, 2026-09-05) : la même requête de sauvegarde renvoie **422 avec
`status=`** et **303 avec `status=__inchange__`**, corps identique par ailleurs. L'utilisateur
aurait perdu la sauvegarde entière en choisissant l'option « inchangé » du sélecteur.

**Conséquence** : pour une option « ne rien changer », utiliser un **sentinel non vide**
(`__inchange__`) — et non `value=""` — ou déclarer le champ `Form(default=…)`. Vaut pour toutes
les apps FastAPI du repo qui ont des formulaires (hub, assistant-ia, bank-review, ev-prices).

⚠️ Ce défaut est **invisible au check statique** : il ne se voit qu'en postant réellement le
formulaire. Un test qui n'observe que l'état du fichier après coup le lit comme un succès — le
fichier est bien intact, mais parce que la requête a été rejetée en entier.

---

## #2 — Faire produire les balises structurantes par un LLM : la troncature devient une imbrication

Un modèle à qui on demande d'émettre lui-même l'enveloppe (`<div>` ouvrant/fermant, en-tête) rend
du HTML **déséquilibré dès que la sortie est coupée** par `max_tokens`. Le fragment suivant ne se
juxtapose pas : il **s'imbrique** dans le précédent, et le rendu part en cascade.

**Mesuré** (newsletter-summary, digest du 2026-09-04, 7 newsletters) : le modèle produisait ~1200
mots pour une consigne de 600, la sortie était coupée à `max_tokens=2500` → **5 blocs sur 7
tronqués** et un `<div>` non fermé → la carte Geopolitechs rendue *à l'intérieur* de la carte
Euractiv. **Une seule cause racine expliquait trois symptômes** qu'on lisait comme trois bugs
(texte coupé, mise en forme cassée, cartes collées).

**Conséquence** — deux règles, la seconde étant la seule qui protège vraiment :
1. Journaliser `finish_reason=length` en WARNING : sans ça la troncature est **silencieuse**.
2. **Le LLM ne renvoie que le contenu ; l'enveloppe est émise par le code.** Un sanitizer déballe
   un wrapper éventuel, coupe une balise finale tronquée et **équilibre les balises** → l'imbrication
   devient impossible *par construction*, pas « improbable si le prompt est bien suivi ». Durcir le
   prompt seul ne fait que déplacer le seuil.

Vaut pour tout rendu structuré produit par un modèle (HTML, XML, JSON en concaténation).

---

## #3 — Une URL de webhook reçoit AUSSI les événements de votre propre trafic sortant

Chez Resend (et le motif vaut pour Twilio, SendGrid, Stripe…), **une seule URL** reçoit tous les
types d'événements : `email.received` mais aussi `email.sent`, `email.delivered`, `email.opened`,
`bounced`, `complained`… Un handler qui ne trie pas sur le type ingère donc **les notifications de
ses propres envois** — et si le produit de l'app est lui-même un email, la boucle se referme.

**Mesuré** (newsletter-summary, digest du 2026-09-05) : le digest quotidien s'ingérait lui-même,
créant **une ligne fantôme par jour** (corps vide, sujet = le sujet du digest de la veille),
resservie le lendemain en carte vide. Symptôme vu par l'utilisateur : objet « 2 newsletter(s) »,
en-tête de première carte « 8 newsletter(s) — Friday 04 », **un seul vrai bloc**. Trois
observations contradictoires, un seul bug. Auto-entretenu : 4 fantômes accumulés depuis le 03/09.

**Conséquence** : trier sur **liste blanche** (`type === "email.received"`), jamais sur liste
noire — le provider ajoute des types, et chaque nouveau serait ingéré par défaut. Tolérer
l'absence de `type` seulement si un format « plano » sans enveloppe est réellement supporté.

⚠️ **Le symptôme ressemble à s'y méprendre à une régression du rendu.** Ici il a d'abord été lu
comme un retour du bug d'imbrication (#2), corrigé la veille — alors que la carte fautive était
*vide*, pas imbriquée. Vérifier **ce qui est en base** avant d'accuser la couche de rendu.

⚠️ **Jumeau connu, dormant** : `comms-gateway` (`src/routes/webhooks.ts`, `POST /webhooks/resend`)
ne trie pas non plus. Sans effet aujourd'hui — zéro trafic en 72 h, Resend pointe sur
newsletter-summary — mais à corriger avant de lui router de l'inbound réel.

---

## #4 — Activer la capacité d'un agent ne change rien tant que son prompt la nie

Sur un agent piloté par prompt, la liste des outils réellement exposés et ce que le modèle **croit**
pouvoir faire sont deux états distincts. Le second gouverne le comportement, et il ne se met pas à
jour tout seul quand on corrige le premier.

**Mesuré** (assistant-ia, 2026-09-05) : `SEARCH_PROVIDER=exa` posé par le commit `90f0531` du
**2026-08-24 19:25** ; `web_search` exposé par `registry.available_specs()`. Le **2026-09-01**,
huit jours plus tard, l'agent répondait encore « Je ne peux pas rechercher des startups spatiales ».
`agent_tool_calls` : **2 lignes en 24 tours, zéro `web_search`**. Le prompt système
(`agent_system_doc`, seule source du prompt — `agent_chat.py:191`) était resté sur sa v1, qui dit
« Tu n'exécutes aucune action et ne disposes d'aucun outil ».

**Conséquence** : après avoir câblé ou activé un outil, la livraison n'est pas la variable
d'environnement — c'est la **mise à jour du prompt** qui le nomme. Vérifier par une **trace
d'exécution** (ligne d'audit, appel journalisé), jamais par la configuration : `SEARCH_PROVIDER=exa`
était vrai et l'agent aveugle en même temps.

⚠️ **Le déni est plus coûteux qu'une erreur d'outil.** Un outil qui échoue produit une trace ; un
outil que le modèle croit inexistant ne produit rien du tout — ni appel, ni log, ni ticket. Le
défaut ne se voit qu'en relisant les conversations réelles. Corollaire : sur tout agent
conversationnel, **relire périodiquement les tours en base** est un contrôle, pas de la curiosité.

⚠️ **Une roadmap peut hériter du même retard.** La roadmap d'assistant-ia écrite le 2026-08-27
posait « `SEARCH_PROVIDER=none` aujourd'hui » comme décision ouverte — c'était déjà faux depuis
trois jours. Une spec qui décrit l'état de la config sans le requêter fabrique du travail imaginaire.
