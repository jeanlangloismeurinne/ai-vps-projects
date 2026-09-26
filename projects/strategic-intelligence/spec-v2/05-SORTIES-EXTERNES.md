# Sorties externes : confidentialité, transparence, budget

Détenteur unique des règles qui s'appliquent à **tout ce qui quitte le serveur** : appels LLM,
embeddings, recherches web, courriels, messages Slack, exports de livrables.

**Principe** : les sources sont publiques ; ce qui est sensible, ce sont **les saisies de
l'utilisateur**. On ne s'appuie pas sur un isolement réseau mais sur trois mécanismes :
1. un **point de passage unique** (le routeur de sortie) qui refuse ce qui ne doit pas sortir ;
2. la **segmentation** de ce qui sort, pour qu'aucune conviction ne soit reconstituable ;
3. la **transparence** : l'utilisateur voit ce qui est parti, le revoit chaque semaine, et valide
   chaque nouveau type d'envoi touchant ses données.

## 1. Trois niveaux de sensibilité

| Niveau | Ce que c'est | Objets | Peut sortir ? |
|---|---|---|---|
| `green` | Information publique ou dérivée de sources publiques | contenus collectés, signaux, observations, entités, taxonomies, description publique du périmètre, pack sectoriel | **oui**, librement |
| `amber` | Ce que l'utilisateur **cherche** : ses sujets d'intérêt | libellés de mandats, questions clés, indicateurs, sondes, énoncés de scénarios, relations acteur ↔ périmètre, retours (`feedback`) | **oui, segmenté** (§3), avec gabarit validé |
| `red` | Ce que l'utilisateur **pense** ou **sait en propre** | énoncés et justifications de thèses, niveaux de confiance, vraisemblances de scénarios, probabilités (`forecast`), décision éclairée par un mandat, annotations, notes terrain | **jamais** |

**Propagation** : la sensibilité d'un envoi est le maximum de celles de ses composants. Un envoi
contenant un seul élément `red` est refusé en entier.

*Analogie* : on peut dire à une bibliothécaire « trouvez-moi tout sur les nouvelles usines de ce
secteur » ; on ne lui dit pas « je parie que notre concurrent va rater son industrialisation ».
Et on ne lui pose pas toutes ses questions le même jour.

### Traitement par canal

| Canal | `green` | `amber` | `red` |
|---|---|---|---|
| LLM (DeepInfra) | oui | segmenté, gabarit validé | refusé |
| Embeddings (DeepInfra) | oui | oui, un objet par appel (un texte court) | refusé : les objets `red` ne sont pas vectorisés à l'extérieur ; ils se rapprochent des signaux par leurs indicateurs |
| Recherche web (Exa) | oui | sondes segmentées | refusé |
| Courriel (comms-gateway / Resend) | oui | décompte + lien | décompte + lien |
| Slack (comms-gateway) | oui | décompte + lien | refusé (pas même un décompte nominatif) |
| Export de livrable | selon rôle du destinataire | `owner`, `analyst` | `owner` seulement |

## 2. Qui est `amber`, précisément

Le tableau de `01` §2 porte la sensibilité de chaque objet. Deux précisions :
- `key_question.current_confidence` est l'estimation **du système** (amber) ; la probabilité
  **de l'utilisateur** est un `forecast` (red).
- `actor_relation` (qui est concurrent, client, avec quelle intensité) est `amber` : un
  prompt peut dire « X est un acteur suivi », jamais « X est notre concurrent d'intensité 3 ».

## 3. Règles de segmentation (`amber`)

Formule : **on envoie ce qu'on observe, jamais ce qu'on en pense.**

| # | Règle | Contrôle par le routeur |
|---|---|---|
| S1 | **Un seul objet `amber` par appel** (une question, ou un indicateur, ou une sonde) | compte des références `amber` du payload |
| S2 | **Jamais de position** : ni sens (`confirms`/`refutes`), ni poids, ni confiance, ni lien vers une thèse ou un scénario | champs interdits dans les parties `amber` |
| S3 | **Jamais l'identité du périmètre** avec un objet `amber` : pas de nom d'entreprise, pas de relation acteur ↔ périmètre | les termes d'identité (réglage `noyau.identity_terms`, saisi dans l'interface, non versionné) sont refusés dans un envoi `amber` |
| S4 | **Forme neutre et fermée** : l'indicateur est envoyé sous sa `check_question` (« ce texte annonce-t-il… ? ») | le gabarit `indicator_check` n'accepte que `check_question` + texte du signal |
| S5 | **Contexte minimal** : le texte du signal candidat et la question, rien d'autre | taille maximale et parties déclarées par le gabarit |
| S6 | **Pas de rafale thématique** : les appels `amber` sont étalés et mêlés aux appels `green` du traitement courant | file dédiée, débit plafonné par objet |

**Résidu accepté (D4)** : un fournisseur qui recouperait tous les appels d'une même clé API
pourrait déduire les **sujets** suivis. Il ne peut pas reconstituer les **convictions**, qui ne
sortent jamais. La revue hebdomadaire (§5) rend ce résidu visible.

### Usages `amber` prévus

| Usage (gabarit) | Objet `amber` envoyé | Module |
|---|---|---|
| `indicator_check` | une `check_question` + un signal `green` | questions_cles |
| `probe_generation` | une question clé | questions_cles |
| `probe_execution` | une requête de recherche | questions_cles (via `search`) |
| `question_assistant` | un brouillon de question (falsifiabilité, reformulation) | questions_cles |
| `embedding` | un énoncé de question ou d'indicateur | questions_cles, scenarios |

Les usages `green` (extraction, so-what à partir de la description publique du périmètre,
fiche d'une source, assistant de pack, sections « Lecture » des fiches) n'ont pas de contrainte
de segmentation.

## 4. Le routeur de sortie (`noyau.sorties`)

Seul module autorisé à appeler un fournisseur externe (I2, `check_sorties.py`).

```python
@dataclass
class EgressPart:
    text: str
    sensitivity: Sensitivity          # déclarée par l'appelant, recalculée par le routeur
    ref: ObjectRef | None             # (kind, id) de l'objet d'origine

@dataclass
class EgressRequest:
    channel: Literal["llm", "embedding", "search", "email", "slack"]
    purpose: str
    prompt_code: str | None           # obligatoire pour llm
    parts: list[EgressPart]
    module_id: str
    function_id: str
```

Étapes, dans l'ordre :
1. **Recalcul** de la sensibilité de chaque partie à partir de `ref` (l'appelant ne peut pas
   déclasser) ; sensibilité effective = maximum.
2. `red` → **refus**, ligne `egress_log` `allowed = false`, erreur nommée à l'appelant.
3. `amber` → vérifications S1 à S5 ; gabarit `prompt_template` avec `max_sensitivity = amber`
   et `validated_at` non nul ; sinon refus nommé (« gabarit non validé »).
4. **Budget** (§6) : en mode `enforce`, refus si plafond atteint ; en mode `observe`, jamais de refus.
5. **Journalisation** `egress_log` (hash, taille, aperçu exact conservé 30 jours, références
   `amber`), puis envoi, puis `api_usage`.
6. **Mode simulation** : pour un nouveau gabarit ou un nouveau fournisseur, le routeur rend ce
   qui serait envoyé sans l'envoyer.

## 5. Informer l'utilisateur

1. **Validation initiale** : tout gabarit de prompt pouvant porter une donnée `amber` est
   présenté à l'utilisateur avec **un exemple réel rendu** (ce qui partirait exactement) avant sa
   première utilisation. Toute nouvelle version redemande la validation.
2. **Revue hebdomadaire** (dans la revue du vendredi) : la liste des objets `amber` sortis dans
   la semaine, regroupés par objet et par usage (« KQ-EX1 : 14 vérifications d'indicateurs,
   2 générations de sondes, 6 requêtes Exa »), avec accès à l'aperçu exact. L'utilisateur coche
   « revu » ; les éléments non revus restent en tête de la revue suivante.
3. **Journal consultable** à tout moment (administration > sorties externes), filtrable par
   canal, niveau, module, objet.
4. **Alerte** immédiate sur tout refus `red` : c'est le signe d'un défaut de code.

## 6. Budget

- **Plafond configurable** (global et par usage), dans l'interface.
- **Mode `observe` au démarrage (D7)** : le garde-budget compte, projette la fin de mois,
  affiche un bandeau à 80 % du plafond, alerte à 100 % et en cas d'anomalie (coût d'une journée
  supérieur à 3 fois la médiane des 14 derniers jours) — **sans jamais bloquer**.
- **Mode `enforce`**, activé par l'utilisateur dans l'interface quand le système tourne : à 100 %,
  les appels payants sont refusés, la collecte continue, les contenus attendent en file et le
  brief le signale.
- **Estimation avant traitement de masse** (rejeu, rattrapage, nouvelle source volumineuse) :
  toujours affichée ; en mode `enforce`, refus au-delà d'un seuil par lot.
- Valeur de départ du plafond : 40 €/mois, à réévaluer après 30 jours de mesure réelle.

## 7. Stockage des données `red`

`shared-postgres` héberge plusieurs projets : un dump de la base ne doit pas exposer une
conviction. Les colonnes `*_enc` sont chiffrées applicativement (AES-GCM) avec une clé de données
stockée dans le coffre, lui-même chiffré par la clé maîtresse du `.env`. Copie de la clé maîtresse
dans `/root/secrets/` (sans elle, les données `red` sont perdues).

## 8. Courriel et Slack

- Via `comms-gateway` (SDK `templates/comms-client/`, variables `GATEWAY_URL`, `GATEWAY_TOKEN`),
  jamais en direct.
- Le module `diffusion` compose le message **puis** le soumet au routeur comme n'importe quelle
  sortie : les sections `amber` et `red` sont remplacées par un décompte et un lien avant l'envoi.
- **Prérequis externes** (état 2026-09-26, `CLAUDE.md` du dépôt) : pas de domaine d'envoi
  vérifié chez Resend (livraison réelle impossible, mode dev), app Slack du gateway à créer.
  Tant qu'ils ne sont pas levés, le brief est consultable dans l'interface et le courriel part en
  mode dev ; ce n'est pas un blocage des lots.

## 9. Ce que garde `check_sensibilite.py`

- un envoi contenant une référence `red` est refusé, pour chaque canal, même si l'appelant la
  déclare `green` ;
- un envoi `amber` avec deux objets `amber` est refusé (S1) ; avec un champ de position (S2) ;
  avec un terme d'identité du pack (S3) ; avec un gabarit non validé ;
- tout envoi autorisé produit exactement une ligne `egress_log`, tout refus aussi ;
- un brief courriel composé à partir d'une base contenant des thèses ne contient aucun texte `red` ;
- en mode `observe`, aucun refus budgétaire ; en mode `enforce` au-delà du plafond, aucun appel émis.

Chaque cas a sa mutation dans `negatif_sensibilite.sh`.
