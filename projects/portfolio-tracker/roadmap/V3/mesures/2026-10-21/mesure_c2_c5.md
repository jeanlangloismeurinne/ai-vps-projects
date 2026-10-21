# Mesure C2 + C5 — 2026-10-21 — lecture seule, aucun commit, aucune écriture en base

## C2 — Plafond de pièces

### Où le plafond est défini

Il existe **deux constantes indépendantes**, chacune lue d'une variable d'environnement, toutes
deux par défaut à 40 — ce ne sont PAS la même variable :

- `backend/tools/acceptation_analyste.py:81`
  `PLAFOND = int(os.environ.get("ACCEPTATION_CORPUS_MAX", "40"))`
  → utilisée par l'outil d'admissibilité à blanc (celui qui a produit `nvda_admissibilite.txt`).
- `backend/tools/executer_chaine.py:80`
  `PLAFOND = int(os.environ.get("CHAINE_CORPUS_MAX", "40"))`
  → utilisée par la VRAIE chaîne (`preparer_dossier_analyste`, maillon 2, ligne 237-239).

Les deux sont réglables indépendamment (deux noms de variable distincts) ; par défaut elles valent
la même chose (40), donc en pratique les deux chemins reçoivent le même plafond sauf si on règle
l'une sans l'autre.

Le plafond lui-même (le nombre) est consommé par `assembler_dossier` dans
`backend/app/agents/v2/dossier.py:277-356`, détenteur UNIQUE de la règle d'assemblage (doc-string
lignes 1-19 : la règle était recopiée dans les deux outils ci-dessus, recopie supprimée).

### Ce que l'analyste reçoit RÉELLEMENT quand le dossier dépasse le plafond

**Rien n'est coupé.** Depuis le correctif référencé #108 (doc-string `dossier.py:69-76`, titrée
« LE PLAFOND NE PEUT PAS COUPER UNE PIÈCE EN VIGUEUR ») :

- `assembler_dossier` (dossier.py:343) calcule `plafond_insuffisant = len(en_vigueur) + len(jointes) > plafond`
  — un **booléen**, jamais une troncature.
- `retenues = list(dict.fromkeys([*en_vigueur, *jointes]))` (dossier.py:345) — **aucune**
  intersection avec `plafond`, aucun `[:plafond]`, aucun tri suivi d'une coupe. Toutes les pièces en
  vigueur (une par point du référentiel) + leurs sœurs (#107, même réponse) + les pièces jointes
  d'office (#103/#106/#139) partent au modèle, quel que soit leur nombre.
- `plafond_insuffisant` n'est lu QUE pour l'affichage (`dossier.py:234-239`, dans `bilan()`, imprimé
  par les deux outils et par `tools/montrer_dossier.py:89`) et dans les checks
  (`checks/check_dossier.py`). **Aucun appelant ne teste ce booléen pour refuser, retrancher ou
  avertir en base** — grep exhaustif de `plafond_insuffisant` dans `backend/` : seulement
  `dossier.py` (déclaration + calcul + bilan), `montrer_dossier.py` (outil d'affichage CLI) et
  `check_dossier.py` (tests). Ni `executer_chaine.py` ni `acceptation_analyste.py` ne le
  consultent après l'avoir obtenu dans `dossier.plafond_insuffisant` — ils se contentent d'imprimer
  `dossier.bilan()`.
- Vérifié en relisant `assembler_dossier` : si `plafond < 1` elle LÈVE (`dossier.py:302-305`,
  ValueError, "#25 : une erreur n'est jamais un résultat vide"). C'est le seul rôle actif restant
  du paramètre `plafond` — déclencher l'exception sur une valeur absurde et peupler le booléen
  diagnostique. Il ne filtre plus aucune pièce.

Donc, pour NVDA `qualite_financiere`/`management_capital` (51 pièces) et `secteur_concurrence`
(66 pièces) : **les 51 / 66 / 51 pièces partent intégralement au modèle**, pas les « 40 premières »
selon un tri quelconque, pas une erreur. Le plafond=40 n'a plus d'effet matériel sur ce qui est
transmis — c'est un vestige de l'ancien mécanisme (tri plat par `source_date` puis coupe,
documenté et abandonné dans `dossier.py:1-19`), gardé uniquement comme seuil d'alerte textuelle.

### Admissibilité à blanc vs chaîne réelle — y a-t-il une différence ?

**Non, chemin identique.** Les deux appellent la même fonction pure
`app.agents.v2.dossier.assembler_dossier` via le même détenteur `charger_dossier`
(`dossier.py:375-397`) :

- `tools/acceptation_analyste.py:127-130` (mode `--admissibilite`) et `:181-184` (mode réel) →
  `charger_dossier(..., plafond=PLAFOND)` directement.
- `tools/executer_chaine.py:237-239` → `preparer_dossier_analyste(..., plafond=PLAFOND)`
  (`backend/app/agents/v2/preparation.py:54-86`), qui à son tour appelle `charger_dossier(...,
  plafond=plafond, joindre=[...])` à la ligne 79-83 — **même fonction, même signature, même
  absence de troncature**. `preparation.py` ajoute des pièces jointes d'office (lectures de
  dépôts #106, socle des comptes #115, pièce du classement #139) que l'outil d'admissibilité
  reproduit lui-même via `piece_du_classement_de` (acceptation_analyste.py:126,179) pour mesurer
  le MÊME dossier que la chaîne (commentaire `preparation.py:48-49` : « un outil qui l'omettrait
  éprouverait l'analyste sur un dossier que la chaîne ne lui remet pas »).

Donc le rapport `nvda_admissibilite.txt` (51/66/51 pièces, « aucune n'a été coupée ») décrit
EXACTEMENT ce que la vraie chaîne enverrait au modèle pour ces trois chapitres NVDA — pas une
approximation de l'outil de mesure.

### NVDA · management_capital : les pièces qui tomberaient « hors des 40 » (lecture seule, gratuit)

Le plafond ne coupe rien aujourd'hui — il n'y a donc pas de « 40 premières » réellement calculées
en production. Pour répondre quand même à la question posée (quelles pièces un ancien tri par
fraîcheur aurait exclues), j'ai rejoué, à titre de mesure, l'ordre `_rang` (tri plat, le plus frais
d'abord, `dossier.py:243-274`) sur les 51 pièces que le dossier remet actuellement
(`assembler_dossier` avec plafond=40, jointe = pièce du classement). Script :
`c2_lister_hors_plafond.py` (ce scratchpad), exécuté en lecture seule dans un conteneur jetable
(jamais `portfolio-backend`), aucun appel modèle, aucune écriture.

Résultat — 11 pièces hors d'un top-40 par fraîcheur :

| id | source_date | tier | nature | portée temporelle |
|---|---|---|---|---|
| 1485 | 2026-01-25 | A | mesure | constatée |
| 1484 | 2026-01-25 | B- | interpretation | constatée |
| 1483 | 2026-01-25 | A | mesure | constatée |
| 1482 | 2026-01-25 | B- | interpretation | constatée |
| 1481 | 2026-01-25 | A | mesure | constatée |
| 1480 | 2026-01-25 | A | mesure | constatée |
| 1479 | 2026-01-25 | A | mesure | constatée |
| 1471 | 2026-01-25 | B- | interpretation | constatée |
| 1470 | 2026-01-25 | A | mesure | constatée |
| 1475 | 2026-01-20 | B- | interpretation | constatée |
| 1474 | 2026-01-20 | A | interpretation | constatée |

À noter : 7 de ces 11 sont tier A (dont 6 de nature `mesure`) — un tri plat par seule fraîcheur
aurait coupé des pièces de haute fiabilité simplement parce que d'autres pièces du 2026-01-25
avaient un `id` plus petit (la clef de tri départage par `-id` décroissant à date égale,
`dossier.py:274`). C'est un simple fait de mesure, pas un défaut puisque ce tri n'est PLUS celui
appliqué — `assembler_dossier` ne tronque rien aujourd'hui.

---

## C5 — Crédit DeepInfra

### Comment le projet appelle DeepInfra

- Clé : `backend/.env` → `DEEPINFRA_API_KEY` (chmod 600, hors git). Non reproduite ici.
- Endpoint : `backend/app/config.py:33` `DEEPINFRA_API_BASE = "https://api.deepinfra.com/v1/openai"`,
  consommé par `backend/app/agents/providers/deepinfra_provider.py:27-29` (`/chat/completions`,
  dialecte OpenAI).
- Modèle réellement utilisé par les agents V2 : interrogé en base (lecture seule,
  `docker exec shared-postgres psql -U admin -d db_portfolio -c "SELECT DISTINCT model FROM
  agent_prompts WHERE flow_version='v2';"`) → **`deepseek-ai/DeepSeek-V4-Flash-0731`** (valeur
  unique, une seule ligne).

### Appel minimal (max_tokens=5)

```
curl -X POST https://api.deepinfra.com/v1/openai/chat/completions \
  -H "Authorization: Bearer $DEEPINFRA_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-ai/DeepSeek-V4-Flash-0731","messages":[{"role":"user","content":"Dis juste: ok"}],"max_tokens":5}'
```

→ HTTP 200. Réponse : `"content":"ok"`, `usage.estimated_cost = 8.4e-7` USD (8 tokens prompt + 2
tokens completion). Le crédit répond, l'appel réel coûte une fraction de millième de dollar.

### Solde / facturation (lecture seule)

DeepInfra expose une API de facturation (`https://docs.deepinfra.com/api-reference/billing/*`),
pas de solde pur mais un « checklist » de compte :

```
curl https://api.deepinfra.com/payment/checklist -H "Authorization: Bearer $DEEPINFRA_API_KEY"
```
→ HTTP 200 :
`suspended: false` · `stripe_balance: -5.55` (négatif = fonds disponibles à dépenser, cf. doc
DeepInfra) · `recent: 3.21` (consommé ce mois) · `limit: 10.0` · `billing_type: "balance"` ·
`topup_failed: false` · `suspend_reason: null`.

Et le détail d'usage du mois (`GET /payment/usage?from=2026.10`) confirme : coût total du mois
= **$3.21**, dont `deepseek-ai/DeepSeek-V4-Flash-0731` (input/output/cached tokens) et
`BAAI/bge-m3` (embeddings). Cohérent avec `recent: 3.21` du checklist.

**Lecture** : compte NON suspendu, ~5,55 $ de crédit prêt à dépenser avant d'atteindre la limite
de 10 $, et l'appel réel confirme que le modèle répond. Aucune anomalie trouvée côté crédit avant
les relances D1.

Aucune clé n'a été loguée dans ce rapport ni dans les fichiers du scratchpad.

---

## Commandes exécutées (code de sortie)

1. `grep -rn "PLAFOND\|plafond" backend --include=*.py -i` → 0 (lecture)
2. Lecture de `backend/app/agents/v2/dossier.py`, `preparation.py`, `executer_chaine.py`,
   `acceptation_analyste.py`, `montrer_dossier.py` → 0 (lecture)
3. `docker exec shared-postgres psql -U admin -d db_portfolio -c "SELECT DISTINCT model FROM
   agent_prompts WHERE flow_version='v2';"` → 0 — `deepseek-ai/DeepSeek-V4-Flash-0731`
4. `docker run --rm --network coolify -v backend:/app:ro -v scratchpad:/scratch:ro ... python
   /scratch/c2_lister_hors_plafond.py` (conteneur jetable, jamais `portfolio-backend`, lecture
   seule, aucun appel modèle) → 0 — 51 pièces remises, 11 hors d'un top-40 par fraîcheur
5. `curl .../v1/openai/chat/completions` (max_tokens=5) → HTTP 200, exit 0
6. `curl .../v1/me` → HTTP 200, exit 0 (mais ne porte pas les champs de solde pour cette clé —
   seulement l'identité du compte)
7. `curl .../payment/checklist` → HTTP 200, exit 0 — solde et statut de suspension
8. `curl .../payment/usage?from=2026.10` → HTTP 200, exit 0 — détail de consommation du mois

Aucun échec. Aucune commande n'a modifié le dépôt ni la base (toutes les requêtes DB sont des
`SELECT` ; aucun `INSERT`/`UPDATE` n'a été émis ; aucun `git commit`).
