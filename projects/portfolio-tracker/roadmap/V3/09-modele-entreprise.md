---
id: spec-modele-entreprise
status: spec-v2-2026-10-21 (arbitrages de la v1 rendus ; 2 points résiduels en §11)
created: 2026-10-21
updated: 2026-10-21 (v2 : architecte dédié, modèle vivant, deux mailles, scénarios construits sur un inventaire de variables)
project: portfolio-tracker
role: >
  Spécification B1 du plan `07-avant-comite.md` : le MODÈLE DE L'ENTREPRISE (orientation de l'utilisateur
  du 2026-10-19, qui englobe le point 9 et l'option D de https://claude.ai/artifact/54kCtG66c9i5GNjL8gDWig).
  §0-§8 en termes de fonds ; §9-§10 notes d'implémentation et lots ; §11 points résiduels.
  Faits de départ : `mesures/2026-10-21/` (inventaire de l'existant, ventilation publiée M0).
  Page de lecture : https://claude.ai/artifact/Dx7LBBpsNAWAYzXroPiDiC
---

# Le modèle de l'entreprise — spec B1 (v2)

> Orientation de l'utilisateur (2026-10-19) : « un outil unique, le modèle de l'entreprise, avec autant
> d'onglets que nécessaire pour une modélisation complète ; chaque question de chaque framework y inscrit
> les informations pertinentes ; il sert à la fin à la valorisation ; il se remplit dans le BON ORDRE car
> les questions ultérieures dépendent de décisions de structuration prises en amont ; vérification qualité
> ad hoc à chaque étape ; puis signature globale du tableau, voire analyse de sensibilité ».
> Exigence du 2026-10-21 : l'architecture se réplique sur des entreprises très différentes.

## 0. Ce que ferait un vrai fonds

L'analyste ne remplit pas un gabarit figé : il **bâtit le classeur de l'entreprise** à partir de ce qu'il en
sait déjà (comptes, segments publiés, premières lectures), avec les briques maison du fonds (définitions
communes d'un marché, d'une part prise, d'une probabilité de succès…). Le directeur de la recherche valide
l'architecture ; l'analyste repart alors chercher, cellule par cellule, ce qui manque — **y compris là où il
croyait être déjà passé**. Le classeur est **vivant** : il se complète au fur et à mesure qu'on apprend sur
l'entreprise. Il montre l'historique et la projection **dans le même format que les comptes publiés**. Les
scénarios ne sont pas une grille de sensibilités : ce sont **quelques récits de risques réels**, choisis
parce qu'ils bougent la valeur de façon matérielle.

## 1. Arbitrages rendus le 2026-10-21 (sur la v1)

1. **Le gabarit est créé par un agent dédié, l'architecte**, propre à chaque entreprise, qui travaille
   avec en contexte les informations déjà récupérées par les autres agents — pour ne pas se tromper de
   structure. Une fois la structure stabilisée, les agents de collecte et d'analyse **repassent** chercher
   les informations nécessaires, de façon robuste et structurée. Le modèle se complète au fil de ce qu'on
   apprend, quitte à rechercher une information pour laquelle on pensait être déjà passé. *(Remplace la v1 :
   gabarit fixe par type d'entreprise ; architecture écrite par me_2.)*
2. **Deux signatures pour l'instant** (l'architecture, puis le classeur entier) ; **cible à terme : une
   seule signature finale**. → la signature de l'architecture est un **interrupteur** (principe fondateur
   n° 3) : on l'éteint quand l'architecte aura fait ses preuves, sans rien réécrire.
3. **Le jugement crée les scénarios, mais par un inventaire** : lister TOUTES les variables de scénario
   possibles, puis un agent ou un système construit les scénarios pertinents, sans en avoir trop. La
   sensibilité de tous les paramètres (version « vanilla ») est incompréhensible pour le métier : elle ne
   correspond pas à des risques réels ou jugés matériels.
4. **Un bloc peut être plus fin que la publication** (et donc que les comptes reconstitués), appuyé sur des
   recherches ad hoc et des hypothèses ; **mais le business plan agrégé est à la même maille que les comptes
   reconstitués**, pour lire l'historique et la projection dans un format comparable.

## 2. Ce qui est commun, ce qui est propre à l'entreprise

```mermaid
flowchart LR
  subgraph FONDS["Commun à tout le fonds (référentiel)"]
    CAT["Catalogue de variables<br/>définition · unité · période ·<br/>origines admises · contrôle"]
    PAT["Patrons de départ<br/>rentable · pré-revenus · financière"]
    AGR["Format agrégé<br/>= les lignes des comptes reconstitués"]
  end
  subgraph TITRE["Propre à l'entreprise"]
    ARC["Architecture de NVDA<br/>blocs · variables retenues par bloc ·<br/>passage du détail à l'agrégé"]
    CEL["Cellules<br/>une valeur, une origine, une pièce,<br/>la question ou la demande qui l'a écrite"]
  end
  CAT --> ARC
  PAT -. suggestion .-> ARC
  AGR --> ARC
  ARC --> CEL
```

- **Le catalogue de variables** (référentiel du fonds) : chaque variable a une définition maison, une unité,
  une période, les origines admises (pièce, réponse reprise, jugement ancré) et son contrôle. Exemples :
  taille du marché, part prise (calculée, jamais sur des revenus futurs), prix moyen, volume, part
  récurrente, marge contributive, probabilité de succès d'un programme (jugement ancré sur une classe de
  référence), date de lancement, ventes au pic, encours, coût du risque, fonds propres alloués.
- **Les patrons de départ** (rentable, pré-revenus, financière) : une suggestion de blocs et de variables que
  l'architecte reçoit, pas une cage. Il peut composer autre chose.
- **Une variable propre** à l'entreprise est admise si l'architecte la déclare avec la même fiche (définition,
  unité, période, origines) ; elle est marquée « propre au titre » pour le comité, et un ajout récurrent
  d'un titre à l'autre est un candidat au catalogue.
- **Le format agrégé** est celui des comptes reconstitués : mêmes lignes (chiffre d'affaires, coûts,
  résultat d'exploitation, impôt, capital employé, flux de trésorerie disponible…), historique et projection
  côte à côte.

## 3. Le cycle de vie du classeur

```mermaid
flowchart TB
  M["① Matière déjà là<br/>comptes reconstitués · ventilation publiée ·<br/>réponses des chapitres · notes flash"]
  A["② L'architecte propose<br/>blocs · variables par bloc · passage à l'agrégé ·<br/>liste des cellules à remplir et qui les remplit"]
  C1{"③ Contrôles de structure<br/>raccords aux comptes"}
  S1["✍ Signature de l'architecture<br/>(interrupteur, cible : une seule signature)"]
  R["④ Relances ciblées, cellule par cellule<br/>une demande précise : variable · bloc · période · unité<br/>même là où on était déjà passé"]
  N{"⑤ Appris quelque chose<br/>qui change la structure ?"}
  V["⑥ Inventaire des variables de scénario<br/>→ scénarios construits → valorisation"]
  S2["✍ Signature du classeur"]
  M --> A --> C1 --> S1 --> R --> N
  C1 -- "refusé, motif" --> A
  N -- "oui : nouvelle version proposée" --> A
  N -- non --> V --> S2
  S2 -. "fait nouveau, revue" .-> N
```

1. **La matière** : l'architecte ne part jamais de zéro. Il reçoit ce que les autres agents ont déjà
   établi — comptes reconstitués, ventilation publiée par segment, marché et géographie (lot B2), réponses
   des chapitres qui tiennent, notes flash. *Ce que ferait un fonds : l'analyste lit le dossier avant de
   dessiner le classeur.*
2. **L'architecte propose** : les blocs (statut : métier actuel, extension annoncée, en développement), les
   variables retenues par bloc, la règle de passage du détail à l'agrégé, et **la liste des cellules à
   remplir**, chacune attribuée à une question existante ou à une demande ciblée.
3. **Contrôles de structure, puis signature** (§6).
4. **Relances ciblées** : chaque cellule vide devient une demande précise (« taille du marché des
   centres de données, estimation interne, exercice 2027, en M$ ») confiée au collecteur et à l'analyste,
   **même si la question avait déjà répondu** en prose. C'est ce qui rend la collecte robuste : on cherche
   une valeur définie, pas un sujet.
5. **Le modèle apprend** : une information qui change la structure (un nouveau produit, un découpage plus
   fin rendu possible par une pièce) fait proposer à l'architecte une nouvelle version ; seules les cellules
   touchées se rouvrent. Le classeur signé reste affiché tant que la nouvelle version n'est pas signée.
6. **Scénarios et valorisation** (§5), puis signature du classeur.

## 4. Deux mailles : le détail et l'agrégé

| Maille | Contenu | Règle |
|---|---|---|
| **Détail** | les blocs de l'architecte, éventuellement plus fins que la publication | un bloc plus fin s'appuie sur des recherches ad hoc et des hypothèses, il est marqué **découpage estimé**, et la somme de ses frères retombe sur la ligne publiée qui les contient |
| **Agrégé** | le business plan au format des comptes reconstitués | mêmes lignes, mêmes définitions ; **historique (comptes reconstitués) et projection côte à côte** ; la somme du détail donne l'agrégé ; la première année projetée part du dernier exercice publié |

Exemple NVDA (mesuré, M0) : la publication donne centres de données = calcul 162 361 + réseau 31 376 =
193 737 M$. Un bloc « grands hébergeurs » à l'intérieur du calcul serait un découpage estimé ; la somme
« grands hébergeurs + autres clients du calcul » doit redonner 162 361. RVMD ne publie rien par programme :
tous ses blocs sont estimés, et l'agrégé se raccorde à la recherche et à la trésorerie totales publiées.

## 5. Les scénarios : un inventaire, puis quelques récits

```mermaid
flowchart LR
  J["Les chapitres de jugement<br/>barrière · dépendances · ruptures ·<br/>concurrents · gouvernance"] --> I
  H["Les hypothèses du classeur"] --> I
  I["Inventaire des variables de scénario<br/>chaque variable : ce qui peut la faire bouger,<br/>de combien, la pièce ou la réponse"]
  I --> SV["Sensibilité de chaque variable<br/>(calculée, sert de contrôle)"]
  I --> CS["Le constructeur de scénarios<br/>quelques récits de risques réels,<br/>chacun combinant les variables qu'il touche"]
  SV --> G{"Une variable matérielle<br/>absente de tout scénario ?"}
  CS --> G
  G -- "oui : signalé au comité" --> CS
  G -- non --> F["Fourchette"]
```

- **L'inventaire** : chaque chapitre de jugement inscrit, pour ce qu'il juge, *quelle variable du classeur
  ce risque ou cette option ferait bouger, dans quel sens, de combien, et sur quelle pièce*. Ex. NVDA me_6
  (concentration des clients) → croissance du bloc calcul, à la baisse ; une extension annoncée (processeurs
  centraux) → un bloc en option, à la hausse, jamais dans le central.
- **La sensibilité de chaque variable** est calculée par le système (sans appel de modèle) : elle n'est pas
  montrée comme résultat, elle sert à **mesurer la matérialité**.
- **Le constructeur de scénarios** (un agent) bâtit quelques récits — scénarios nommés pour une incertitude
  continue (NVDA), arbre d'événements pour une incertitude binaire (RVMD : chaque programme réussit ou
  échoue) — chacun nommant les risques réels qu'il porte et les pièces qui les fondent.
- **Le contrôle** : toute variable dont la sensibilité dépasse le **seuil de matérialité du fonds** doit
  apparaître dans au moins un scénario, ou être déclarée non pertinente avec un motif ; sinon le comité le voit.
- **Repli** (principe n° 3) : si le constructeur échoue, le classeur présente la sensibilité des variables
  matérielles seulement, triée — moins parlante, jamais fausse.
- La synthèse affiche aussi la sensibilité à ±1 point du taux exigé (décision du 2026-10-17).

## 6. Les contrôles, étape par étape

Le système vérifie que les chiffres tiennent ensemble ; le sens se juge à la lecture (#68).

| Étape | Ce que le système vérifie | Le cas qu'il arrête |
|---|---|---|
| Architecture | chaque bloc publié se raccorde à sa ligne publiée (écart nommé) ; les blocs estimés se raccordent à leur ligne parente ; l'agrégé reprend les lignes des comptes reconstitués ; chaque variable est au catalogue ou porte sa fiche complète ; chaque cellule a un auteur et un seul | un découpage plausible qui ne se raccorde pas aux comptes |
| Cellules | origine admise par la variable (pièce, réponse reprise, jugement ancré) ; la part prise est calculée, jamais sur des revenus futurs ; unité et période de la variable | NVDA me_5 #1370 : un marché d'extension pris pour plafond, 10 % sur des revenus futurs |
| Agrégé | somme du détail = agrégé ; première année projetée cohérente avec le dernier exercice publié (écart nommé) ; marges des blocs moins coûts communs = résultat d'exploitation | une projection qui part d'un autre point que les comptes |
| Scénarios | chaque variable matérielle est dans un scénario ou écartée avec motif ; chaque scénario modifie bien les variables qu'il dit toucher | un risque cité qui ne bouge rien ; un risque matériel oublié |
| Valorisation | contrôles existants de l'atelier ; chaque segment est un bloc signé | un segment inventé au moment de valoriser |
| Synthèse | aucune cellule orpheline (écrite sans être lue, lue sans être écrite) | une ligne signée que le calcul ignore |

## 7. Les signatures

- **L'architecture** : signée au procès-verbal (proposer / signer / écarter, motif), comme le classement du
  titre (#139). **Interrupteur** : éteint, l'architecte enchaîne sur les relances et seule la signature du
  classeur subsiste (cible annoncée).
- **Les réponses** : toujours acquittées question par question.
- **Le classeur entier** : la signature du modèle de valorisation (#98) s'étend au classeur ; la version
  signée reste affichée ; l'écart entre versions se lit cellule par cellule.

## 8. Ce que le comité voit

Le classeur (écran E1) : l'architecture et sa version ; un onglet par bloc ; l'agrégé, historique et
projection côte à côte au format des comptes ; l'inventaire des variables de scénario et leur matérialité ;
les scénarios et la fourchette ; la marge de sécurité au dernier cours coté daté (#81). Chaque cellule montre
sa valeur, son origine, sa pièce, son auteur et son état (tient / à revoir). La note d'initiation (E3) cite
les cellules.

## 9. Notes d'implémentation (pour les lots)

- **Référentiel** (`frameworks.yaml`) : `catalogue_de_variables` (fiche : définition, unité, période, origines
  admises, contrôle déterministe nommé) ; `patrons_de_modele` (par archétype : blocs et variables
  suggérés) ; `format_agrege` = renvoi aux lignes du gabarit du socle (#115), pas une copie. Paramètre du fonds
  neuf : `seuil_de_materialite` (§11).
- **Contrats** : `Architecture` (version, blocs : id, libellé, statut, publié/estimé, ligne publiée de
  rattachement ou bloc parent ; variables par bloc ; passage à l'agrégé ; cellules attendues → auteur), sortie
  de l'agent architecte ; `Cellule` (adresse bloc × variable × période, valeur, origine, auteur, pièce) ;
  `InventaireScenario` (variable, cause, sens, amplitude, pièce/réponse) ; `ModeleValorisation` → `modele-1.3.0`
  (segments = blocs signés ou regroupements nommés ; scénarios issus du constructeur).
- **Auteur d'une cellule** : une question existante (son encadré, #100, devient l'écriture d'une cellule ; les
  9 encadrés existants s'y projettent) ou une **demande ciblée** (nouvelle : variable + bloc + période + unité,
  instruite par le collecteur et l'analyste comme une question à une seule cellule). Un seul auteur par
  cellule (#99 généralisé).
- **Ventilation publiée (B2)** — mesurée (M0) : `submissions.json` → `FilingSummary.xml` → rapports `R#.htm`,
  axes et membres XBRL en clair ; repérer par les axes, jamais par le numéro `R#`. NVDA : segments, marchés,
  calcul/réseau, géographie, raccord à 0. RVMD : rien par programme. JPM : 4 métiers avec produit net, coût du
  risque, charges, résultat, fonds propres moyens. Extension du socle (#115) : le code relève.
- **Persistance** : registres append-only — architectures et leur PV ; demandes ciblées ; cellules = vue sur
  les écritures des réponses qui tiennent, recalculée à la lecture (#77). Migration 061 et suivantes.
- **Ordre** : l'architecture signée (ou l'interrupteur éteint) ouvre les relances ciblées ; la valorisation
  attend que les cellules qu'elle lit tiennent ; relance bornée (#137 point 17) au niveau de la cellule.
- **Sensibilité et matérialité** : rejeux de `evaluer_modele` (déterministe) variable par variable sur
  l'amplitude inscrite à l'inventaire.
- **Réplicabilité** : un check greppe le code livré contre tickers et noms de blocs ; fixtures copiées du
  réel sur trois titres (NVDA, RVMD, JPM) ; acceptation de l'architecte sur au moins deux types.

## 10. Les lots

| Lot | Contenu | Qui |
|---|---|---|
| M0 | ✅ Mesure de la ventilation publiée (NVDA, RVMD, JPM) | Sonnet |
| M1 | Catalogue de variables, patrons, format agrégé ; contrats `Architecture` / `Cellule` ; gardes | Opus spec → Sonnet |
| M2 | Ventilation publiée au socle (B2) | Sonnet sur spec |
| M3 | L'agent architecte (contexte = matière du dossier) ; contrôles de structure ; signature au PV avec interrupteur (migration) | Opus spec → Sonnet ; acceptation à blanc NVDA + RVMD |
| M4 | Demandes ciblées par cellule ; projection des encadrés existants en cellules ; relances | Opus spec → Sonnet |
| M5 | Agrégé au format du socle, historique + projection ; contrôles de raccord | Sonnet sur spec |
| M6 | Inventaire des variables de scénario (écrit par les chapitres de jugement) ; matérialité ; constructeur de scénarios + repli | Opus spec → Sonnet |
| M7 | L'agent de valorisation sur le classeur (B3) ; va_4-6 au cours du jour (B4) ; Greenwald (B5) ; ±1 pt ; alerte d'échéance (B7) | Opus → Sonnet |
| M8 | Acceptation NVDA et RVMD (B8) | Sonnet lance, Opus lit |

**Pour NVDA** : les relances D1 (16 questions ouvertes) passent AVANT l'architecte — elles forment sa matière ;
les relances ciblées (M4) viennent après la signature de l'architecture.

## 11. Points résiduels (soumis le 2026-10-21)

1. **Le seuil de matérialité** : à partir de quel effet sur la valeur centrale une variable doit-elle
   figurer dans un scénario ? Proposition : **10 % de la valeur centrale**, décision du fonds au référentiel,
   comme le taux exigé, revue une fois l'an. *Un fonds fixe ce seuil dans sa politique de recherche, commun au
   portefeuille ; titre par titre, il serait arbitraire.*
2. **Quand l'architecte passe-t-il sur NVDA ?** Proposition : après les relances D1, pour qu'il dispose des
   réponses à jour (management, barrière, secteur) ; l'alternative est de le faire passer tout de suite sur
   la matière actuelle, plus vite mais sur des réponses en partie périmées.
