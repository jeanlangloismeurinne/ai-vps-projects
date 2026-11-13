---
id: spec-lot-b4f-explorateur
status: spec v1 2026-10-22 (Opus) — options arbitrées le même jour (C + B′, F en garde-fou) ; à exécuter par Sonnet APRÈS B4d
created: 2026-10-22
project: portfolio-tracker
role: >
  Spec d'EXÉCUTION du lot B4f (plan `07-avant-comite.md`) : l'explorateur du dossier, brique commune aux
  agents, branchée d'abord sur l'architecte. Le dossier est un graphe à trois étages (notes d'analyste →
  pièces → documents d'origine) avec deux horloges (remplacement, péremption) ; l'agent y descend à la
  granularité dont sa mission a besoin.
---

# Lot B4f — l'explorateur du dossier

> **Ce que ferait un vrai fonds** : l'analyste qui bâtit le classeur a le dossier sous la main — la table
> des matières, les notes de ses collègues, et derrière chaque note les pièces qui la fondent. Il ouvre
> l'original quand une note ne suffit pas ; il voit qu'une note a été écrite avant un événement et la lit
> comme l'état d'avant ; il consulte l'ancien seulement comme historique. Ce qui manque au dossier, il le
> DEMANDE au chargé de recherche, qui le vérifie et le range : il ne cite pas un résultat de moteur de
> recherche dans le modèle.

## 0. Mesure (2026-10-22) — à RE-MESURER à l'étape 0

| Fait | Mesure |
|---|---|
| Dossier en vigueur | NVDA 411 pièces (≈ 385 000 caractères, titres ≈ 40 000), RVMD 473 (≈ 451 000 / 46 000), toutes vectorisées (bge-m3) |
| Coût | un passage de l'architecte ≈ 15 000 jetons ≈ 0,004 $ ; tout le dossier en contexte ≈ 100 000 jetons ≈ 0,03 $ : le frein n'est pas le coût mais la lecture (attention diluée, instabilité) |
| Briques existantes | boucle d'outils bornée `runner.run_tool_json_agent` (clôture en JSON strict, coûts cumulés) ; `query_knowledge` (vectoriel sur les pièces COURANTES, repli texte, jamais de fusion RRF) ; `document_search.select_relevant` (chercher dans un long texte, #134) ; `RetrievalLog` ; liens réponse → pièces (`cited_entry_ids`), pièce → remplaçante (`superseded_by`), note flash → réponses rouvertes ; actualité d'une réponse calculée à la lecture (`charger_etat_dossier`) |
| Manque | aucun moyen pour un agent de se DÉPLACER d'un étage à l'autre ; l'état temporel d'une PIÈCE n'est jamais servi à un agent |

## 1. Périmètre et interdits

- **Livré** : module `app/knowledge/explorateur.py` (exécuteurs d'outils, purs côté rendu) ; branchement
  sur l'architecte avec un interrupteur à trois positions ; demandes de recherche (B′) ; checks, négatifs,
  cas fictifs.
- **Pas livré** : explorateur pour les analystes et la valorisation (même brique, branchements ultérieurs) ;
  graphe d'entités (option E, après le comité) ; aucun accès Internet pour l'architecte.
- **Interdits** : aucun état temporel STOCKÉ (calculé à la lecture, #53/#77) ; aucune fusion des signaux
  vectoriel et texte ; aucun ticker ni libellé dans le code ; la portée de lecture est fixée par le mandat
  (le `ticker_id` n'est jamais un argument du modèle, comme `make_query_knowledge_executor`).

## 2. Les outils (exécuteurs, `ticker_id` fermé dans l'exécuteur)

Chaque élément rendu porte son **état au jour de la lecture** : `en vigueur` ; `remplacé par #id (date)` ;
`écrit avant <fait daté>` (péremption, pour une note) ; et ses deux dates (fait, document, #79).

| Outil | Ce qu'il rend | Bornes |
|---|---|---|
| `table_des_matieres(etage?, sujet?)` | la liste des notes (question, statut, date, actualité) et des pièces EN VIGUEUR (numéro, titre, dates, type de source), filtrable par étage et par mots du titre | 200 lignes par appel, paginée |
| `ouvrir_note(question_id)` | la réponse en vigueur (verbatim, encadré, actualité, faits postérieurs) et la liste de ses pièces avec titre et état | — |
| `ouvrir_piece(numero, chercher?)` | le contenu de la pièce (et son état) ; au-delà de 6 000 caractères, les passages qui répondent à `chercher` (`select_relevant`) ; une pièce REMPLACÉE s'ouvre, marquée « historique », avec sa remplaçante | 6 000 caractères |
| `rechercher(sujet, limite?)` | les pièces en vigueur les plus proches (vectoriel, sinon texte, mode tracé), titre + 300 caractères + état | 10 résultats |

Budget par passage : `max_iterations` paramètre du fonds au référentiel du classeur (défaut 8) ; au-delà,
clôture sur ce qui a été lu, motif nommé dans le rendu (jamais un blocage muet). Chaque ouverture est
journalisée (`RetrievalLog`) : **numéros ouverts**.

## 3. Les citations

`pieces_citables` d'un passage = celles de la matière (B4d §2) ∪ les numéros OUVERTS ou rendus par un outil
pendant le passage. [S6] contrôle contre cette union (un seul détenteur). Une pièce historique (remplacée)
n'est pas citable pour fonder un bloc : [S6] le dit avec sa remplaçante.

## 4. Les demandes de recherche (B′)

`ArchitecteSortie.demandes_de_recherche: list[{sujet (≥ 20), pourquoi (≥ 20), blocs: list[id]}]` : ce que
le dossier ne contient pas et dont le classeur a besoin. À blanc : rendues. À l'écriture : chacune devient
une demande au collecteur par le mécanisme EXISTANT des demandes de recherche (point 14 du plan, closes à la
livraison) — Sonnet identifie son détenteur à l'étape 0 et n'en crée pas un second. Le comité les voit.

## 5. L'interrupteur et les deux temps (garde-fou F)

Référentiel du classeur, `acces_au_dossier: aucun | deux_temps | explorateur` :
- `aucun` : l'architecte actuel (matière seule) — l'ordre 0 ;
- `deux_temps` : premier appel sans outil, qui rend sa proposition ET `besoins_d_information` (sujets) ; le
  CODE exécute `rechercher` pour chaque besoin (sans modèle), ajoute les résultats à la matière, et le second
  appel rend l'architecture. Coût et durée bornés, besoins visibles ;
- `explorateur` : la boucle d'outils §2, puis la clôture en JSON strict.
Le refus nommé et le renvoi unique s'appliquent dans les trois modes. Défaut à la livraison : `aucun` (le
banc B4e décide, sur chaque entreprise, en comparant les trois).

## 6. Gardes

- Cas fictifs (base de test, aucun nom réel) : un dossier à trois étages avec une note périmée par un fait,
  une pièce remplacée, une pièce longue ; attendus : états rendus exacts, pièce remplacée marquée historique
  et non citable, `chercher` qui rend le passage attendu, pagination, borne d'itérations qui clôt avec motif.
- Citations : un numéro jamais montré ni ouvert → [S6] ; un numéro ouvert → admis.
- Portée : un exécuteur ne rend jamais une pièce d'un autre titre (assert sur un dossier fictif à deux titres).
- `negatif_explorateur.sh` : une mutation par règle (état non rendu, pièce remplacée citable, borne levée,
  portée élargie, fusion des signaux).
- Suite ENTIÈRE.

## 7. Étapes et ce que Sonnet rend à Opus

0. Mesurer : détenteur des demandes de recherche ; forme de `tools_json` des agents et où vit la consigne de
   l'architecte ; taille d'une table des matières NVDA/RVMD en jetons.
1. `explorateur.py` + checks + négatifs (sans modèle).
2. Branchement architecte (trois modes) ; contrat (`demandes_de_recherche`, `besoins_d_information`) ;
   consigne et exemple (#121).
3. Suite ; bilan par `grep -E`.
4. À blanc, NVDA et RVMD, une fois par mode (~0,05 $ en tout) : pièces ouvertes, itérations, coût, issue,
   et ce que l'architecte a trouvé que la matière seule ne lui donnait pas.
5. Rendre ; ne pas committer, ne pas déployer, aucun `--ecrire`.

## 8. Addendum du 2026-10-23 (Opus, après le diagnostic B4d et #143) — À LIRE AVANT L'ÉTAPE 0

**Ce qui a changé depuis la v1.** L'architecte tourne sur DeepSeek-V4-Pro (`MODELE_ARCHITECTE`, ≈ 0,10 $
par passage, pas 0,004 $ : refaire le calcul de budget §0) ; le critère #143 (une ligne propre se décide
par les données de marché et de concurrence à aller chercher) est dans sa consigne ; `me_7` déclare
`nombre_de_programmes` ET `nombre_de_programmes_non_nommes` ; [S15] exige un décompte exact quand les deux
sont établis. Journal du plan : lignes « B4d (diagnostic) » et « #143 (construit, éprouvé) ».

**Pourquoi ce lot est maintenant le chemin critique.** Mesuré (`mesures/2026-10-23/banc-modeles/`,
`apres-143/`) : trois erreurs de l'architecte viennent de ce qu'il ne voit que les TITRES des pièces et le
résumé de `me_7` — l'IA souveraine (la pièce #1012 dit : usines Vera Rubin vendues à des États = clients de
Data Center), Vera CPU déjà vendu (#1004 : ~20 Md$ de revenus CPU visibles), et les molécules que la
réponse `me_7` RVMD #2624 a PERDUES alors que la pièce #1546 qu'elle cite les nomme (RMC-0708, RMC-8839 ;
essais RASolute 308, RASolve 301). L'analyste de `me_7` (Flash) est instable : mêmes pièces, 7 molécules
le 22/10, 5 le 23/10.

**Ajout au périmètre (§3 bis) — [S14]/[S15] lisent aussi ce qui a été OUVERT.** Sans cela l'explorateur
trouverait les programmes oubliés et les contrôles les refuseraient :
- [S14] : un nom de programme est admis s'il figure littéralement dans le verbatim de `me_7` OU dans une
  pièce ouverte pendant le passage (et sa référence est dite dans le motif de l'entrée : « #1546 ») ; même
  règle de passage continu ; le NOM est le passage le plus court qui désigne le programme (le motif du
  refus le dit — mesuré : avec le format « nom — détails » de `me_7`, l'architecte recopiait des phrases
  entières comme noms).
- [S15] : les entrées dont le nom n'est PAS dans `me_7` mais dans une pièce ouverte s'ajoutent au décompte
  attendu (elles ne le faussent pas) et sont SIGNALÉES au comité (« absent de `me_7`, trouvé dans #… ») —
  c'est aussi le moyen de voir l'instabilité de l'analyste.
- Détenteur : `structure.py` (pas un second contrôle) ; la matière porte la liste des pièces ouvertes et
  leur texte rendu, comme `pieces_citables` (§3).

**Ce que l'étape 4 doit vérifier, à la lecture (pas au code de sortie).** En mode `explorateur`, une fois
par entreprise : (a) NVDA — l'IA souveraine n'est plus une ligne propre ni une extension (clients de Data
Center) ; Vera CPU est une activité VENDUE à marché propre (bloc estimé `metier_actuel`, enfant de Data
Center), pas `en_developpement` ; Vera Rubin rattachée ; (b) RVMD — les molécules et essais absents de
#2624 réapparaissent, signalés « absent de `me_7` » ; chaque extension d'indication de daraxonrasib a sa
ligne (#143). Noter pour chaque cas la pièce ouverte qui l'a permis. Ce qui reste faux après ouverture des
pièces est un défaut de CONSIGNE (formulation du critère #143 — la « probabilité de succès » citée parmi
les données propres a fait garder Vera Rubin en ligne propre) ou de MODÈLE, pas d'information : le dire.

**Hors de ce lot (en attente de l'utilisateur).** Corriger la formulation du critère #143, l'élément
« par indication » dans `me_7`, le passage de l'analyste de `me_7` sur V4-Pro : NE PAS les faire ici — la
mesure de l'étape 4 doit d'abord dire ce que l'ouverture des pièces règle seule.

**Budget.** Étape 4 : 2 passages en mode `explorateur` (≈ 0,15-0,30 $ avec V4-Pro et les pièces
ouvertes) ; `deux_temps` et `aucun` : un passage chacun seulement si l'explorateur réussit (règle : un
essai avant toute série, annoncer le coût avant de lancer).
