# `app/modules/` — la charte d'un module et la garde des accès

Le système est reconstruit module par module dans ce paquet. L'ancien code (`app/agents`,
`app/knowledge`, `app/modele_entreprise`, `app/valorisation`, `app/contracts`, `app/api`…) reste en
place comme carrière : on y reprend des pièces, on n'y ajoute pas de dépendance cachée.

Le texte normatif est ailleurs et n'est pas recopié ici : la constitution
`roadmap/V3/principe-directeur.md`, et « La charte d'un module » (8 points) dans
`roadmap/V3/07-avant-comite.md`. Ce document dit seulement **comment le code tient la charte** et
**quel assert la garde**.

## Structure d'un module

```
app/modules/
  registre.py            détenteur unique de la déclaration des modules (stdlib seulement)
  <nom>/
    contrat.py           l'objet de sortie versionné (VERSION_CONTRAT) + LA fonction de lecture
    …                    l'intérieur : libre, invisible du dehors
    adaptateurs/         (facultatif) ce qui est propre à UNE source ou à une juridiction
    ARCHITECTURE.md      ce que le module fait réellement, et ses gardes
```

- `contrat.py` est **le seul fichier** qu'un autre module, l'ancien code ou l'API a le droit
  d'importer. Tout le reste du dossier peut changer sans prévenir personne.
- Un module lit le contrat d'un autre seulement s'il le **déclare** (`lit=` au registre). Le chef
  de dossier est le seul à lire tous les contrats (`lit_tous_les_contrats`) ; il n'en écrit aucun.
- Un module **possède ses tables**, toutes au préfixe déclaré (`prefixe_tables`). Personne d'autre
  ne les nomme : qui veut la donnée passe par la fonction de lecture du contrat.
- Ce qu'un module reprend de l'ancien code est écrit au registre (`reprises=`) : une dette visible,
  à vider, pas un import discret.
- Rien de propre à une société, à un pays ou à une place de cotation dans le cœur d'un module :
  c'est une donnée des référentiels, ou le contenu d'un sous-dossier `adaptateurs/`.

## Ajouter un module

1. Une entrée `Module(...)` dans `registre.py` (`nom`, `rend`, `prefixe_tables`, `lit`, `reprises`).
2. Le dossier `app/modules/<nom>/` avec `__init__.py` et `contrat.py` (`VERSION_CONTRAT = "1.0.0"`
   et la fonction de lecture).
3. Son `ARCHITECTURE.md`, et sa ligne dans `roadmap/V3/ARCHITECTURE-CIBLE.md`.
4. `python3 checks/check_charte_modules.py` (tourne sur l'hôte, sans dépendance) : vert.

Un préfixe de tables se choisit en **mesurant** d'abord qu'il ne percute rien dans l'ancien code ;
s'il percute, on change le préfixe, pas la règle. (`chef_` : 0 occurrence dans `app/` et `tools/`
au 2026-11-13 ; `emetteurs_` : 0 ; `fiche_` écarté : il percutait des noms de fonctions.)

Un module qui offre un écran : la route vit dans `app/api/` et n'importe que `contrat` ; les gestes
qui écrivent sont donc exposés PAR le contrat (qui délègue à l'intérieur), jamais importés à côté.

## Invariant → assert garant

Contrôle : `checks/check_charte_modules.py` (AST et système de fichiers, sans base ni réseau).
Preuve qu'il rougit : `checks/negatif_charte_modules.sh` (au moins une mutation par invariant, plus
les cas permis qui doivent rester verts).

| # | Invariant | Assert (libellé stable) | Charte |
|---|---|---|---|
| C0 | Le contrôle a lu quelque chose : registre présent et chargeable, modules scannés = modules déclarés, au moins un fichier Python par module | `[C0] registre présent`, `[C0] registre chargeable`, `[C0] modules scannés = modules déclarés`, `[C0] <nom> : au moins un fichier Python lu` | — |
| C1 | Bijection registre ↔ disque ; registre cohérent | `[C1] dossier sur disque mais non déclaré au registre`, `[C1] module déclaré au registre mais absent du disque`, `[C1] registre incohérent` | — |
| C2 | Un contrat versionné par module | `[C2] <nom> : contrat.py présent`, `[C2] <nom> : contrat.py expose VERSION_CONTRAT` | point 2 |
| C3 | D'un autre module, on n'importe que `contrat`, et on le déclare | `[C3] accès interdit`, `[C3] lecture non déclarée` | point 2 |
| C4 | Un module n'importe l'ancien code que par ses `reprises` ; le registre n'importe rien de `app` | `[C4] ancien code importé`, `[C4] le registre reste autonome` | point 7 |
| C5 | L'ancien code ne lit d'un module que son contrat | `[C5] l'ancien code lit l'intérieur d'un module` | point 2 |
| C6 | Les tables d'un module ne sont nommées que chez lui ; préfixes sans collision | `[C6] table d'un autre`, `[C6] préfixes de tables en collision` | point 1 |
| C7 | Ni jeton de juridiction ni symbole de société dans le cœur d'un module | `[C7] jeton de juridiction`, `[C7] symbole de société` | point 5 |

Précisions de lecture :

- **C3/C5** résolvent les imports relatifs et jugent les trois formes (`import a.b`, `from a import b`,
  `from . import b`). Importer le paquet entier d'un module (`import app.modules.<nom>`) est refusé :
  ce n'est pas son contrat. `app.modules.registre` est toujours permis.
- **C6** lit les chaînes littérales (morceaux fixes de f-strings compris), pas les docstrings. Le
  **nom** d'un module n'est pas une table (`chef_de_dossier` commence par `chef_`).
- **C7** lit le code et ses chaînes, pas les commentaires ni les docstrings. `adaptateurs/` est
  exempté des jetons de juridiction, **pas** des symboles de société. La liste est un filet : elle
  attrape l'oubli grossier, elle ne prouve pas qu'un module est neutre.
- `checks/` n'est pas soumis à C3–C5 : le contrôle d'un module éprouve son intérieur, c'est son rôle.

## Limites — ce que la garde ne voit PAS

- **L'accès dynamique** : `importlib.import_module("app.modules.x.interne")`, `getattr`, `__import__`
  ne sont pas des nœuds d'import. Un objet interne rendu PAR le contrat puis utilisé ailleurs non plus.
- **Le SQL construit par morceaux** : `"chef" + "_etats"`, un nom de table passé en variable, ou une
  requête sans chaîne littérale échappent à C6. C6 ne lit ni les fichiers `.sql` (les migrations
  vivent dans `app/db/migrations/`, hors du module qui possède la table) ni le frontend.
- **L'écriture** n'est pas distinguée de la lecture : C6 refuse de NOMMER la table, il ne sait pas ce
  que la requête en fait. Et rien ne vérifie qu'une table d'un module porte bien son préfixe : c'est
  la base qui le dirait, et ce contrôle ne s'y connecte pas.
- **Le sens** : un contrat peut exposer trop, la « seule fonction de lecture » n'est pas comptée, une
  règle propre à un pays peut s'écrire sans aucun jeton de la liste (un seuil, un calendrier fiscal).
  La garde tient la structure et la relation, jamais le sens.
- **Les imports hors du préfixe `app.`** (un `sys.path` modifié) et les fichiers d'un outil qui ne
  compile pas (lus en texte brut pour C6 seulement, et signalés par une note).
- **`tools/`** n'est soumis qu'à C6, pas à C5.
