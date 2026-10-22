---
id: spec-lot-m3bis
status: spec-2026-10-22 (Opus) — à exécuter par Sonnet
created: 2026-10-22
project: portfolio-tracker
role: >
  Spec d'EXÉCUTION du lot M3 bis (suite de B4, plan `07-avant-comite.md`) : fermer les trous du contrôle de
  structure révélés par la lecture des 4 architectures à blanc du 2026-10-22 (`mesures/2026-10-22/*.json`),
  AVANT tout `--ecrire`. Lot précédent : `12-lot-M3-architecte.md` (règles [S1]-[S9], contrat 1.1.0).
---

# Lot M3 bis — un membre publié reste publié, une ligne annuelle lit des grandeurs annuelles, un programme a un jalon

> **Ce que ferait un vrai fonds** : le directeur de la recherche qui relit le plan d'un classeur refuse
> trois choses à la première lecture. (1) Un chiffre que l'entreprise publie, recopié comme une
> « estimation » et rangé sous une case d'un AUTRE découpage — les segments et les marchés de l'émetteur
> se croisent, ils ne s'emboîtent pas. (2) Une ligne annuelle du compte de résultat alimentée par un
> montant qui n'a pas de période (« ce qu'il reste à dépenser » n'est pas « ce qu'on dépense cette
> année »). (3) Un programme en développement sans son prochain jalon : la probabilité de succès est
> celle d'UN jalon, elle ne se partage pas entre des molécules à des stades différents. Et quand le
> dossier ne permet pas de découper, l'analyste l'écrit (« il me manque l'inventaire des programmes »)
> au lieu de regrouper en silence.

## 0. Ligne de base mesurée (2026-10-22, Opus) — à RE-MESURER en premier (§7, étape 0)

| Fait | Mesure |
|---|---|
| Production | M3 déployé (`1d5dfbf`), `GET /v2/tickers/NVDA/architecture` → 200 `aucune_proposee` ; `check_architecture_persist` 10/0 contre la vraie base (corrigé : point de sauvegarde autour du doublon refusé), 0 ligne laissée dans `architectures_modele` / `_decisions` |
| NVDA, 2 passages | premier niveau = segments (`secteurs` : Compute & Networking, Graphics) ; puis les marchés de l'axe `activites` (Data Center, Gaming, ProViz, Automotive, OEM ; Hyperscale, AI Clouds, Edge Computing) déclarés **`estime`** et rattachés `parent` sous un segment — **Data Center (193 737 M$) sous Compute & Networking (193 479 M$)**, Automotive sous Graphics. Passage 2 : Networking ET Data Center frères sous Compute & Networking (double compte : Networking est un enfant de Data Center dans la ventilation). Emboîtement fin différent d'un passage à l'autre. Hugging Face (acquisition annoncée le 2026-09-02) en `en_developpement` |
| Pourquoi les contrôles passent | [S1]/[S3] ne regardent que les blocs `publie` : un membre publié déclaré `estime` y échappe |
| RVMD, 2 passages | un bloc produit approuvé ; tout le portefeuille en UN bloc « programmes précliniques » (une probabilité de succès) ; `recherche_developpement = programmes_precliniques__cout_restant_de_developpement` |
| Pourquoi les contrôles passent | [S9] saute les fiches `sans_periode` (`structure.py:323`) : un stock sans période alimente une ligne annuelle |
| Matière RVMD (`architecte.sh RVMD --matiere-seule`, gratuit) | 39 289 caractères, ~9 800 jetons ; **aucune molécule hors daraxonrasib n'y figure** (0 occurrence des autres candidats) : le regroupement n'est pas une faute de l'architecte, c'est un trou du DOSSIER — aucune question source n'inventorie le portefeuille de programmes |
| Porte RVMD | **fermée** : se_3 sans réponse instruite (mo_6 refusée, admise par l'interrupteur de phase de test) |

## 1. Périmètre et interdits

- **Livré** : contrat `architecture-1.2.0` (jalon des programmes, manques du dossier) ; référentiel `1.2.0` (une
  fiche) ; règles [S10]-[S12] ; prompt et exemple mis à jour ; signaux neufs au service ; checks et négatifs.
- **Pas livré** : la question source « inventaire des programmes » (§6, arbitrage de l'utilisateur, après le comité
  NVDA) ; les demandes ciblées (M4) ; tout raccord chiffré (M5).
- **Ne change pas** : `frameworks.yaml` ; la porte ; la migration (aucune : 0 ligne en base, le JSONB porte la
  nouvelle forme) ; `socle_comptes.yaml` (LU, jamais recopié).
- **Réplicabilité** (07) : aucun ticker, nom de segment, de marché, de produit ou de membre dans le code, le
  prompt, l'exemple ni le référentiel. Fixtures copiées du réel (les 4 JSON du 2026-10-22 + la ventilation NVDA)
  et le disent.
- **Ne pas committer, ne pas déployer, ne rien écrire en production** ; acceptation à blanc seulement.

## 2. Le contrat et le référentiel

### 2.1 `architecture-1.2.0` (`modele_entreprise_schema.py`)

- `Bloc.jalon: Optional[Jalon]` avec `Jalon(Strict)` = `franchi: str` (min 10 : le dernier jalon atteint, ex. de
  forme « essai de phase 2 achevé »), `franchi_le: date`, `prochain: str` (min 10 : le jalon que mesure
  `probabilite_de_succes`), `attendu_vers: Optional[str]` (exercice `FYxxxx` ou texte court).
  Validateur : `jalon` **requis** si `statut == "en_developpement"`, **interdit** sinon (un métier actuel n'a pas de
  jalon de développement ; une extension annoncée va aux scénarios, pas au central).
- `ArchitecteSortie` et `Architecture` gagnent `manques_du_dossier: list[ManqueDuDossier]` (défaut `[]`), avec
  `ManqueDuDossier(Strict)` = `sujet: str` (min 20 : ce qu'il faudrait pour dessiner juste), `blocs: list[Identifiant]`
  (les blocs dont la maille en souffre, peut être vide), `consequence: str` (min 20 : ce que l'architecture fait à
  la place, ex. « un seul bloc pour des programmes dont le dossier ne donne ni le nombre ni le stade »).
  Validateur : tout id de `blocs` est un bloc de l'architecture.
- `ARCHITECTURE_SCHEMA_VERSION = "architecture-1.2.0"` (0 ligne en base : aucune reprise).

### 2.2 Référentiel `1.2.0` (`modele_entreprise.yaml`)

- Fiche neuve **`depense_de_developpement_du_bloc`** : « Dépense de recherche et développement engagée sur
  l'exercice pour le programme du bloc — ce que le compte de résultat de l'année supporte, pas le coût restant
  jusqu'au jalon » ; unité M$, période `exercice`, famille `industrielle`, origines `piece`, `jugement`, `calcul` ;
  questions sources `[qf_7]` ; pas de `somme_vers_ligne` (la ligne `recherche_developpement` porte aussi la
  recherche non affectée : sa formule reste à l'architecte, gardée par [S11]). Ajoutée au patron `pre_revenus`.
- `cout_restant_de_developpement` : définition complétée d'une phrase — « montant SANS période : il ne
  s'inscrit jamais tel quel dans une ligne annuelle ; la dépense de l'exercice est
  `depense_de_developpement_du_bloc` ».

## 3. Les règles neuves (`structure.py`, même forme : un code, tous les motifs réunis)

| Code | Règle | Le cas qu'elle arrête (réel, 2026-10-22) |
|---|---|---|
| [S10] | **un membre publié ne se déguise pas en estimé** : aucun bloc non publié dont le libellé OU l'id, normalisé (§3.1), égale le libellé ou le nom local (§3.1) d'un membre de la ventilation, sur N'IMPORTE QUEL axe (cellules et membres nouveaux). Motif : « le bloc `x` est le membre publié (axe=…, membre=…) : cite son adresse ». Sans ventilation : sans objet | Data Center, Gaming, Automotive… en `estime` sous un segment ; Networking frère de Data Center |
| [S11] | **une ligne lit des grandeurs de son cadrage** : dans la formule de passage d'une ligne, tout nom `bloc__variable` (et toute variable propre) a une fiche de période `exercice` si la ligne est de cadrage `flux`, `instant` si elle est de cadrage `instant` ; jamais `sans_periode`. Le cadrage d'une ligne = celui de l'état du gabarit (`socle_comptes.yaml`, `etats[].cadrage`) qui la porte, lu par le chargeur du socle (détenteur unique, #46 — jamais une liste de lignes recopiée) | `recherche_developpement = …__cout_restant_de_developpement` |
| [S12] | **un programme, un jalon** : deux blocs `en_developpement` qui ont le même `jalon.prochain` normalisé ET la même `attendu_vers` sont signalés (pas refusés : deux indications d'une même molécule peuvent partager un essai) ; un bloc `en_developpement` qui porte `probabilite_de_succes` sans `jalon` est déjà refusé par le contrat | un portefeuille entier sous une seule probabilité |

### 3.1 Normalisation de [S10] (pure, une fonction, testée)

`_cle(texte)` : minuscules ; `&` → `and` ; accents retirés ; tout ce qui n'est pas `[a-z0-9]` retiré. Nom local d'un
membre : la partie après `:` du qname, suffixe `Member` (et `SegmentMember`) retiré, puis `_cle`. Un bloc est
refusé si `_cle(libelle)` ou `_cle(id)` ∈ {`_cle(libellé du membre)`, nom local}. Ex. de forme : `data_center` →
`datacenter` = `DataCenterMember` → `datacenter`. Les libellés préfixés (« Extension annoncée — … ») ne sont
pas en cause : la comparaison est une égalité, pas une inclusion — **jamais** une inclusion (« Data Center
Networking » n'est pas « Networking »).

### 3.2 Signaux neufs (ce que le comité lit, servis par `juger`, écrits au PV à la signature)

- chaque `manque_du_dossier` : « manque du dossier : {sujet} — {consequence} (blocs …) » ;
- chaque bloc `en_developpement` : « programme `x` : franchi {franchi} le {date}, prochain {prochain} vers
  {attendu_vers} » — le comité vérifie qu'il s'agit bien d'un produit de l'émetteur (une acquisition non conclue
  est une extension annoncée) : #68, la structure ne juge pas le sens, elle l'expose ;
- [S12].

## 4. Le prompt et l'exemple (`architecte.py`)

Ajouter, en termes d'analyste :
- « Un membre que la ventilation publie est TOUJOURS un bloc publié, avec son adresse recopiée. Deux axes
  différents (secteurs et marchés, par exemple) se croisent : on n'emboîte jamais un membre d'un axe sous un
  membre d'un autre axe. L'emboîtement entre blocs publiés est celui de la ventilation ; tu ne le déclares pas. Si
  tu veux le détail d'un autre axe que celui du premier niveau, il n'a pas sa place dans l'architecture : il servira
  de raccord. »
- « `en_developpement` = un produit de l'émetteur en cours de développement (essais, prototype, homologation) ;
  il porte son jalon. Une acquisition, un partenariat ou un produit seulement annoncés sont `extension_annoncee`. »
- « Un bloc de programme = un prochain jalon. Si le dossier ne te donne pas les programmes un par un, ne les
  regroupe pas en silence : déclare le manque (`manques_du_dossier`) et dis ce que tu fais à la place. »
- « Une ligne annuelle ne lit que des grandeurs de l'exercice : le coût restant d'un programme n'est pas sa
  dépense de l'année. »
- `_EXEMPLE_ARCHITECTURE` (société fictive) : son programme porte un `jalon` et `depense_de_developpement_du_bloc` ;
  `manques_du_dossier` = un manque fictif. Toujours validé par le check (#121) contre sortie, contrat, [P], [S].

## 5. Les gardes

- `check_architecte.py` : pour [S10], [S11], [S12], le contrat 1.2.0 — un cas réel qui passe, et les **4 JSON du
  2026-10-22 copiés en fixtures** (`checks/fixtures/architecte/2026-10-22/`, en-tête posé) : NVDA 1 et 2 refusés par
  [S10] (le motif nomme Data Center et son adresse), NVDA 2 aussi par [S10] sur Networking ; RVMD 1 et 2 refusés par
  [S11] (nomme `cout_restant_de_developpement` et `recherche_developpement`) et par le contrat (`jalon` manquant).
  `_cle` : `DataCenterMember` ↔ « Data Center » égal ; « Data Center Networking » ≠ « Networking ».
  [S11] lit le cadrage depuis le gabarit : un cas `capital_employe` (instant) qui lit une fiche `exercice` est refusé.
- `negatif_architecte.sh` : une mutation par règle neuve et par validateur du contrat ; chaque mutation nomme
  l'assert qui doit rougir (motif de mutation unique dans le fichier muté).
- `check_modele_entreprise.py` / `negatif_modele_entreprise.sh` : la fiche neuve, 1.2.0.
- `run_all.sh` : suite ENTIÈRE (contrat partagé) — bilan par `grep -E`.

## 6. Arbitrage réservé (ne pas exécuter)

Le portefeuille de programmes d'une `rentable` qui en porte (RVMD) n'est instruit par AUCUNE question source ;
après M3 bis, l'architecte de RVMD le déclarera en manque (le comité le verra) au lieu de le regrouper en
silence. **Recommandation d'Opus** (à trancher par l'utilisateur, après le comité NVDA — RVMD a déjà sa porte
fermée par se_3) : une question source « quels programmes l'entreprise développe-t-elle, à quel stade, avec quel
prochain jalon et quelle dépense » (un tableau que publient les 10-K des sociétés de biotechnologie), applicable
aux classements `pre_revenus` et `rentable`, rattachée à `probabilite_de_succes`, `annee_de_lancement`,
`depense_de_developpement_du_bloc`.

## 7. Étapes et ce que Sonnet rend à Opus

0. Re-mesurer §0 (gratuit) : `architecte.sh NVDA --matiere-seule`, `architecte.sh RVMD --matiere-seule` (taille) ;
   rejouer les 4 JSON contre `valider_structure` actuel → « passent » (ligne de base : les trous existent).
1. Contrat et référentiel 1.2.0 ; checks M1/M3 verts.
2. [S10]-[S12], signaux, prompt, exemple ; checks et négatif ; les 4 fixtures refusées par le bon code.
3. Suite entière.
4. **Acceptation à blanc** (quelques centimes ; crédit DeepInfra vérifié par un appel minimal) : `architecte.sh NVDA`
   deux fois, `architecte.sh RVMD --hors-porte` deux fois, `--sortie` dans `mesures/2026-10-22bis/` (ou la date du
   jour). Rapporter les 4 BILAN et, par titre, ce qui diffère entre les deux passages. Critères lus par Opus :
   NVDA — aucun membre publié en `estime`, un seul axe, le découpage choisi dit au motif ; RVMD — la ligne
   `recherche_developpement` lit une grandeur de l'exercice, le portefeuille est soit découpé avec des jalons
   fondés sur des pièces, soit déclaré en manque. Un refus après renvoi est un résultat (le rapporter), pas un
   échec à contourner.
5. Rendre : fichiers ; écarts et pourquoi ; négatifs (rouges / total) ; ce qui n'a PAS été exécuté. Ne pas committer.

Opus vérifie ensuite par exécution, lit les architectures contre la matière, committe, déploie, puis — sur accord
de l'utilisateur — `--ecrire` pour NVDA et la signature au comité.
