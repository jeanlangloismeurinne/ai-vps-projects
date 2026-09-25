---
project: newsletter-summary
updated: 2026-09-25
role: >
  Prompt de reprise du moteur de résumé de mails. État : en production ; la newsletter (8h) et les alias
  à la demande (`summary@…`) passent par un moteur unique. Aucun chantier en cours — un 360° est proposé.
---

# Prompt de reprise — newsletter-summary

> **Roadmap active : aucune.**

**Carte de l'archive** : le récit des lots livrés est dans `00-REPRISE-ARCHIVE.md`. Le seul fait
réutilisable ailleurs est en `DECISIONS.md` **#2**. L'état stable du projet — flux, alias, endpoints,
variables, sécurité, vérification, commande de déploiement — est dans le **`README.md`**, seul détenteur :
ce fichier ne le redit pas.

## État

En production. Newsletters transférées → inbound Resend → PostgreSQL ; digest à 8h (Europe/Paris) résumé par
DeepInfra, un appel par mail, envoyé via **comms-gateway** (le projet ne détient aucune clé de provider).
Depuis le **2026-09-25**, la newsletter est l'**alias par défaut** d'un moteur unique (`app/alias_digest.py`) ;
on peut créer d'autres alias depuis le Hub (`/newsletter/aliases`) : fréquence, expéditeurs autorisés, prompt.
Déploiement : ce projet reste **hors** de `infrastructure/compose-deploy.sh` (comme `kb-viewer`) — commande dans le `README.md`.

**À faire au prochain démarrage de session — le 1er digest 8h du nouveau moteur est le 2026-09-26.** Tout a été
éprouvé (suite 8/8, 29 mutations, test d'or, exécution réelle d'une newsletter comparée octet à octet au digest de
l'ancien code), mais **aucun digest de 5 à 8 mails réels n'est encore passé par le nouveau moteur**. Vérifier :
objet « 📬 Résumé hebdo-news — N newsletter(s) », cartes séparées, aucun `failed` :
`select status, count(*) from emails where alias_id = 1 group by 1;`

## Reste à faire / dettes ouvertes

- **Hypothèse non vérifiable depuis le VPS** : que Resend accepte *n'importe quelle* partie locale — dont `summary` et
  `aaa+bbb` — sur `*.resend.app` (seul `newsletter@` a été observé en prod ; le webhook synthétique ne teste pas Resend).
  → **Acceptation utilisateur** : créer l'alias dans le Hub avec **son** adresse d'expéditeur, écrire un vrai mail à
  `summary@oozeenaru.resend.app`, puis à un `aaa+bbb@`. Penser au dossier spam (`onboarding@resend.dev`, dette ci-dessous).
- **Quota gateway : 60 e-mails/jour pour tout le client** `newsletter-summary` (`client_policies.rate_limit_per_day`).
  `ALIAS_MAX_PER_DAY=40` garde de la marge au digest newsletter ; relever la policy (UPDATE en base gateway) si l'usage grandit.
- **`system` du LLM encore « newsletter »** (`summarizer.summarize_html` : 600 mots, sans pub) : suffisant tant que le prompt des
  alias est le même ; à rendre par alias le jour où un prompt « de gestion » diverge vraiment.
- **Repli « `+tag` → alias de base » non inclus** (décision : correspondance exacte, sinon la liste blanche d'un alias couvrirait un
  espace d'adresses illimité). À rouvrir seulement si l'utilisateur le demande.
- **Dates en anglais** dans l'objet et l'en-tête (« Friday 25 September ») : héritage du digest d'origine, gelé par le test d'or.
- **Risque SSRF résiduel** : ré-résolution DNS entre la validation et la connexion (fenêtre étroite ; atténuée par la liste blanche).
- **Le corps d'un mail arrivé trop tôt** : traité pour la cadence `minute` (re-essais sur 3 tours) ; en cadence matin/soir, un corps
  absent produit la carte « Corps non reçu » + `failed` (pas de re-essai différé) — à traiter si le cas se répète sur un vrai mail.
- **Domaine d'envoi Resend non vérifié** → gateway en `RESEND_DEV_MODE=1` : tous les envois (digest **et** réponses d'alias) vont à
  `RESEND_DEV_TO`, expédiés par `onboarding@resend.dev`, que Gmail filtre en spam (confirmé le 17/09). Blocage hors-code, l'utilisateur
  gère la vérification de domaine lui-même — ne pas relancer ce chantier de soi-même.
- **Code mort** : `SUMMARIZATION_PROMPT` et `summarize()` (`config.py`, `summarizer.py`) ne sont jamais appelés — à retirer.
- **Repli « Option A »** (coquille HTML 100 % côté code) : décidé comme repli, pas comme cible — ne l'ouvrir que si le rendu d'un vrai lot déçoit.
- **Fédération KB** : `kb_documents` est à l'enveloppe `KNOWLEDGE_ARCHITECTURE.md` §3 (tag `alias:<nom>` sur les résumés récents).
  Brancher le connecteur `mailbox` → `db_knowledge_federation` le jour où une recherche multi-source est demandée, jamais par anticipation.

## Rollback

Sauvegarde pré-migration : `/root/secrets/newsletter-summary-pre-alias-2026-09-25.sql`. Le schéma est additif (colonnes nullables) :
revert du commit + `docker compose up -d --build` suffit. Réserve : après un revert, les mails d'alias `new` seraient pris par l'ancien digest.

## Où démarrer

Vérifier le digest du 26/09 (ci-dessus), puis proposer le diagnostic 360° (`CONTROL_SYSTEM.md` §4) et attendre le choix de l'utilisateur.
