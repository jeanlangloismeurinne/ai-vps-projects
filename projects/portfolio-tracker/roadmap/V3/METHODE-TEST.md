# Méthode de test & de mesure — un guide, pas un gabarit

> La boucle *écrire un check → le prouver rouge → mesurer → déjouer les faux-verts → vérifier contre
> le réel* domine ~90 % du coût d'un lot. Ce document la rend **frictionnelle et outillée**. Il ne
> **rigidifie rien** : le décideur ci-dessous est une heuristique, jamais un classifieur câblé.

## 1. Choisir la méthode — par DÉCIDABILITÉ, pas par coût

Un appel modèle ne coûte quasi rien (une acceptation ≈ 0,005 $). Le vrai critère n'est donc pas la
dépense mais : **quelle étape peut TRANCHER la question, avec la bonne ATTRIBUTION** (un résultat qui
distingue « le modèle a échoué » de « la couche en dessous a échoué »).

Heuristique — **ouverte**, à lire comme une aide au jugement :

- **Une source déterministe/inspectable peut produire OU vérifier l'entrée ?** (EDGAR sous contrôle,
  un producteur, un plan) → **dry-run d'abord**, et lire la sortie **EN TEXTE**. Non pour économiser,
  mais pour l'**attribution** (un défaut en amont devient visible, cf. F15/F16 trouvés à 0 $) et la
  **stabilité** (déterministe = reproductible ; un modèle bascule entre deux passages à T=0).
- **La question porte intrinsèquement sur le modèle** (refus, jugement, tool-calling, adhérence JSON)
  **ou aucune source déterministe n'existe** (seul le web/le modèle crée l'entrée) → **test vrai-modèle
  direct** : il n'y a pas de frontière à gagner.
- **Autre cas, ou tu hésites** → **NE PAS forcer** dans une des deux cases. **Nomme** le cas, écris
  pourquoi il n'y rentre pas, prends la méthode la plus décisive du moment, et re-mesure. Les deux
  catégories ci-dessus **ne sont pas closes** : on ne connaît pas aujourd'hui tous les cas traitables
  de façon déterministe ni tous ceux qui exigeront une autre méthode. Cf.
  `feedback_decision_figee_a_remesurer`, `feedback_blocage_classifieur_non_permanent`,
  `feedback_rigidite_revocabularisee`.

**Toujours vrai, quel que soit le chemin : re-jouer l'étape qui a tranché après CHAQUE correctif.**

> Ce décideur est de la **documentation**. Aucun code ne l'applique à ta place — le forcer en
> classifieur reproduirait la rigidité qu'il met en garde.

## 2. Les outils, sans friction (une commande chacun)

| Besoin | Commande | Note |
|---|---|---|
| Frontière déterministe (lire la sortie en TEXTE) | `tools/rejeu_producteurs.sh`, `… --plan-only` / `--dry-run` | à 0 $, avant toute dépense |
| Ligne de base (re-**requêtée**, versionnée, jamais `/tmp`) | `tools/ligne_de_base_frameworks.sh`, `tools/mesure_*.sh` | se mesure AVANT le lot, ne se souvient pas |
| Vrai-modèle bon marché (hors prod) | `tools/acceptation_*.sh` (`acceptation_analyste.sh` ≈ 0,005 $, `acceptation_gate.sh`, …) | **jamais dans `portfolio-backend`** (code déployé) |
| Suite hors-ligne complète | `bash checks/run_all.sh` | ligne de base **2388 / 0** |
| Test négatif d'un check neuf | `checks/_negatif.sh` (harnais) + `checks/_harness.py` (garde-fous py) | **obligatoire : prouver rouge une fois** |

## 3. Écrire un test négatif — le harnais fait le gros

La boucle de mutation vit dans **`checks/_negatif.sh`** (détenteur unique, #46). Un `negatif_*.sh`
neuf = ses **mutations** + `source _negatif.sh` + `run_mutations` (cf. `negatif_framework_contract.sh`).
Le harnais impose les trois conditions : exit ≠ 0 · l'assert **nommé** rougit (pas un autre) · le
script atteint son **bilan**.

Garde-fous côté check (dans **`checks/_harness.py`**) :
- `strip_code()` — retire commentaires + docstrings par `tokenize` avant un grep d'interdit (sinon il
  lit sa propre énonciation) ;
- `imports_symbol()` — « le fichier importe X » vérifié par **AST**, jamais par `"X" in source` ;
- `Bilan.require(seq, n, …)` — exige la **cardinalité** avant tout `all(...)`/`any(...)` (un `all()`
  sur liste vide est vert sur rien).

## 4. Les faux-verts à connaître (chacun a déjà coûté ici)

1. **Fixture non discriminante** — rend 100 % ok avant mutation ? Sinon elle est aveugle. Se **copie
   du réel** (`COPY`), jamais écrite à la main (une fixture plus favorable que la prod ne voit rien).
2. **Script mort avant ses asserts** — le bilan doit être atteint ; un filet `try` transforme une
   exception en **FAIL nommé**.
3. **Assert à côté du point de lecture** — tester la valeur REÇUE au GET, pas le helper en isolation.
4. **Assert écrit depuis sa propre constante** — la référence d'un contrôle ne doit pas être bougée
   par le fichier qu'il contrôle (comparer au socle, pas à la valeur contrôlée).
5. **`all(...)` sur liste vide** — cf. `Bilan.require`.
6. **Grep qui lit sa propre énonciation** — cf. `strip_code`, et asserter aussi **en positif**.
7. **`__pycache__` périmé / mesureur joué dans `portfolio-backend`** — le runtime exécute un autre
   code que celui qu'on lit.

## 5. La structure elle-même est gardée

`check_architecture.py` (+ `negatif_architecture.sh`) tient l'organisation : bijection registre
`ARCHITECTURE-CIBLE.md` ↔ docs sur disque, pointeurs de checks vivants, **aucune garde orpheline**
(tout `check_*.py` adossé à une cible), discipline de dossier `roadmap/`, autonomie de `/V3`.

Il tourne en conteneur (via `run_all.sh`) **et sur l'hôte** (`python3 checks/check_architecture.py`,
stdlib seule). Un **hook pré-commit** host (sans docker, instant) le joue à chaque commit touchant
portfolio-tracker — `checks/pre-commit.sh`. Installation (le contenu de `.git/hooks` n'est pas
versionné, à refaire après un clone) :

```bash
ln -sf ../../projects/portfolio-tracker/backend/checks/pre-commit.sh "$(git rev-parse --git-dir)/hooks/pre-commit"
```

Contournement ponctuel : `git commit --no-verify`.
