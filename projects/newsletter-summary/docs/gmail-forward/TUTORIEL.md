# Tutoriel — brancher le pilotage Gmail (état réel du chantier)

Complète l'étape-par-étape de `SPEC.md` § Tutoriel avec ce qui a été réellement construit. À faire une fois, ~20 min. **Rien de ceci n'a encore tourné contre un vrai Gmail** : la recette (`RECETTE.md`) sert à le constater.

## Ce que fait le système

```mermaid
flowchart LR
  H[Hub : /newsletter/gmail] -->|HUB_API_TOKEN| N[newsletter-summary]
  N -->|requête signée HMAC| S[Apps Script]
  S -->|filtre + transfert| G[Gmail]
  G -->|mail d'une newsletter| R[alias@oozeenaru.resend.app]
  R -->|webhook| N
```

Vous décrivez une règle (« les mails de `@exemple.com` vont vers l'alias `veille` »). Le script la crée comme filtre Gmail avec transfert. Le moteur de résumé reçoit le mail par l'alias correspondant.

## Étapes

1. **Alias de réception.** Dans le Hub, onglet Newsletter → Alias : créer un alias par famille de sources (partie locale + `@oozeenaru.resend.app`). Ce sont les seules destinations proposées dans le formulaire de règle.
2. **Autoriser chaque adresse dans Gmail** (Paramètres → Transfert et POP/IMAP → Ajouter une adresse de transfert). Gmail envoie un lien de confirmation à l'alias : il arrive chez Resend, ouvrez-le depuis le tableau de bord. **Laisser « Désactiver le transfert » coché** : seuls les filtres du système doivent transférer.
3. **Projet Apps Script** (script.google.com, compte Gmail concerné) : service Gmail API ajouté, manifeste affiché, puis coller `apps-script/appsscript.json` et `apps-script/Code.gs` de ce dépôt. Le manifeste ne demande que `gmail.settings.basic`.
4. **Propriétés du script** : `HMAC_SECRET` (`openssl rand -hex 32`), `DEST_ALLOWED_DOMAINS` = `oozeenaru.resend.app`, `DENY_FROM` (domaines jamais transférés : banque, impôts, messagerie pro…), `DISABLED` = `false`.
5. **Autoriser et déployer** : exécuter `authorize` (l'écran ne doit citer que les paramètres Gmail), puis Déployer → Application Web, « Exécuter en tant que : Moi », « Accès : Tout le monde ». Copier l'URL `/exec`.
6. **Variables du VPS** (`projects/newsletter-summary/.env`, chmod 600, jamais committé) :

| Variable | Valeur |
| --- | --- |
| `GMAIL_SCRIPT_URL` | URL `/exec` (c'est un secret : accès anonyme) |
| `GMAIL_SCRIPT_SECRET` | le même secret que `HMAC_SECRET` |
| `DEST_ALLOWED_DOMAINS` | `oozeenaru.resend.app` |
| `DENY_FROM` | la même liste que dans le script |
| `SECRET_ROTATED_AT` | date du jour (AAAA-MM-JJ) |
| `HUB_API_TOKEN` | déjà posé ; obligatoire (sans lui, les routes Gmail répondent 503) |

7. **Déployer** newsletter-summary puis le Hub (`infrastructure/compose-deploy.sh`).
8. **Vérifier** : Hub → Gmail → « Script & secret » → *Tester la connexion* (ping) ; la page de synchronisation ne doit montrer aucun écart.

## Règles à connaître

- Une règle porte un expéditeur (adresse ou `@domaine`), éventuellement un sujet et des mots exclus. Domaine entier à deux niveaux (`@co.uk`) : refusé. Règle sans expéditeur : plafonnée (sujet ≥ 6 caractères, 5 au plus).
- Créer/modifier se fait en deux temps : **Aperçu** (rien n'est écrit) puis **Confirmer**. Une règle large demande une case de confirmation en plus.
- Seuls les filtres créés par le système sont modifiables ; les vôtres sont affichés en lecture seule.
- La synchronisation **détecte** les écarts (filtre supprimé à la main, orphelin) ; elle ne corrige jamais seule. Un contrôle quotidien tourne à 06:30 et alerte.

## Coupure d'urgence et entretien

- **Coupure** : exécuter `panic()` dans Apps Script (supprime les filtres gérés, laisse les vôtres, passe `DISABLED` à `true`). Remettre `DISABLED` à `false` pour reprendre.
- **Rotation du secret (tous les 6 mois)** : Hub → Script & secret → *Faire tourner*. Le nouveau secret s'affiche **une seule fois** : le coller dans `HMAC_SECRET` du script, puis *Confirmer* ; ensuite mettre à jour `GMAIL_SCRIPT_SECRET` et `SECRET_ROTATED_AT` dans le `.env` du VPS. *Annuler* abandonne sans rien changer.
- Toute modification de `Code.gs` : Gérer les déploiements → nouvelle version du déploiement existant (un nouveau déploiement change l'URL).
- Garder la validation en deux étapes sur le compte Google.
