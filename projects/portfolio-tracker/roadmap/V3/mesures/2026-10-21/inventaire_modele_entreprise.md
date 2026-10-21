# Inventaire factuel — avant spec « modèle de l'entreprise » (portfolio-tracker)

Lecture seule. Aucune écriture, aucun appel modèle payant, aucun commit. Toutes les citations sont
`fichier:ligne` au moment de l'inventaire (2026-10-21).

## 1. Le contrat `modele_valorisation_schema` et l'atelier de calcul

Fichier : `backend/app/contracts/modele_valorisation_schema.py`. Version actuelle :
`MODELE_SCHEMA_VERSION = "modele-1.2.0"` (modele_valorisation_schema.py:61).

Champs de `ModeleValorisation` (modele_valorisation_schema.py:184-193) :
- `schema_version` (littéral `"modele-1.2.0"`)
- `ticker_id` (str, ≥1)
- `version` (int ≥1)
- `methodologie` (str, ≥80 car. — la mécanique décrite en prose, #96)
- `motif_de_la_forme` (texte ≥20 car. — pourquoi cette forme de fourchette)
- `segments` (`list[Segment]`, min 1) — `Segment` = `id`, `libelle`, `perimetre` (modele_valorisation_schema.py:107-110)
- `hypotheses` (`list[Hypothese]`, min 1)
- `fourchette` (union discriminée `ScenariosNommes | ArbreEvenements`)
- `mecanique` (str, code Python — exécuté dans le bac, doit définir `valeur_action`, `SORTIE_OBLIGATOIRE` modele_valorisation_schema.py:68)

**Hypothèse** (modele_valorisation_schema.py:113-132) : `nom`, `segment` (optionnel, `None` = hypothèse du dossier entier), `libelle`, `unite`, `valeur` (centrale), `origine`, `reprend` (optionnel, question d'une autre méthodologie dont la ligne tient la place).

**Les 3 origines** (`Origine = OriginePiece | OrigineReprise | OrigineJugement`, modele_valorisation_schema.py:104) :
- `OriginePiece` : `type: "piece"` + `source_entry_refs` (modele_valorisation_schema.py:83-85)
- `OrigineReprise` : `type: "reponse_reprise"` + `question_id` (pattern `^[a-z]{2}_[0-9]+$`), `answer_id`, `chiffre` (id déclaré par l'encadré de la question reprise) (modele_valorisation_schema.py:88-95)
- `OrigineJugement` : `type: "jugement"` + `taux_de_base` (`TauxDeBase` : `classe_de_reference`, `valeur`, `source_entry_refs`) + `ecart_justifie` (≥30 car.) (modele_valorisation_schema.py:98-101, 75-80)

**Forme de la fourchette** (`Fourchette`, modele_valorisation_schema.py:181) :
- `ScenariosNommes` : `forme: "scenarios_nommes"`, exactement 3 `ScenarioNomme` (`role` bas/central/haut, `recit`, `valeurs` : clé d'hypothèse → valeur du scénario) ; le central NE PORTE AUCUNE valeur de substitution, les autres doivent en porter (modele_valorisation_schema.py:147-167)
- `ArbreEvenements` : `forme: "arbre_evenements"`, `evenements` (min 1), chacun `id`, `recit`, `probabilite` (clé d'hypothèse qui porte sa probabilité) (modele_valorisation_schema.py:170-178)

**Contraintes de validation internes** (`_coherence_interne`, modele_valorisation_schema.py:195-240) :
- segments à id uniques ; hypothèses à clé unique (`cle_hypothese` = `nom` ou `segment.nom`, modele_valorisation_schema.py:141-144)
- `segments` réservé comme nom d'hypothèse globale (modele_valorisation_schema.py:205-206)
- une hypothèse par segment doit viser un segment déclaré (modele_valorisation_schema.py:207-208)
- un seul chiffre par dossier : deux lignes qui reprennent la même question au même endroit (dossier ou même segment) sont refusées (modele_valorisation_schema.py:209-214)
- segment déclaré qu'aucune hypothèse ne chiffre = refusé, « découpage de façade » (modele_valorisation_schema.py:215-218)
- scénarios : les clés modifiées doivent exister dans le tableau (modele_valorisation_schema.py:222-226)
- arbre : ids d'événements uniques, probabilités (clés) uniques, chaque probabilité référence une hypothèse existante dont la valeur est dans [0,1] (modele_valorisation_schema.py:227-239)

### `app/valorisation/modele.py` — le pont (ce qui n'est PAS dans le contrat, #37)

Vérifie ce que le contrat seul ne peut pas juger (modele.py:1-32) :
- [A] une `reponse_reprise` cite une réponse ACQUITTÉE du bon titre, à la bonne question, et porte LA MÊME valeur ET unité que l'encadré de cette réponse (modele.py:139-163)
- [B] toute pièce citée (hypothèse `piece`, taux de base d'un `jugement`) est au dossier de ce titre (modele.py:164-166, `_pieces_citees` modele.py:116-122)
- [C] la mécanique s'exécute dans le bac pour chaque scénario/branche et définit un nombre `valeur_action` (modele.py:92-100, `_executer`)
- [D] la mécanique LIT chaque ligne du tableau — vérifié par analyse de l'AST (noms + littéraux de chaîne, `_lectures` modele.py:103-113, 187-192)
- [E] la fourchette est ORDONNÉE : bas ≤ central ≤ haut (modele.py:194-197)
- [F] un seul chiffre par dossier : une ligne qui `reprend` une question doit soit reprendre la réponse qui tient (si elle existe), soit porter son propre chiffre SEULEMENT si la question est déclarée « sans objet » pour ce titre ; sinon le modèle « attend » (`ModeleRefuse("F", ...)`, modele.py:168-185).

`evaluer_modele` (modele.py:201-226) : déterministe, sans appel modèle. Pour un arbre d'événements : central = tableau tel quel, bas = toutes probabilités à 0, haut = toutes à 1, et pour chaque événement : valeur en échec (proba=0) et en succès (proba=1), les autres gardées à leur valeur signée. Pour des scénarios nommés : bas/central/haut = trois exécutions avec les surcharges du scénario.

### `app/valorisation/bac_a_calcul.py` — ce que le sous-ensemble Python autorise

Interpréteur par parcours d'AST (jamais `eval`/`exec`/`compile`, bac_a_calcul.py:26-29). Liste BLANCHE :
- **Instructions admises** : affectation simple et tuple (`a, b = …`), affectation indexée sur un conteneur créé par le programme (`d["clé"] = …`, pas sur une hypothèse signée), `+=` (opérateurs arithmétiques seulement), `for` sur une liste/tuple/str/dict finis, `if/elif/else`, `pass` (bac_a_calcul.py:41-45, 301-335, 337-354)
- **Interdits explicitement** : `def`, `lambda`, `import`, `while`, `try`, `with`, chaînes formatées, attributs (`x.y` — donc aucun chemin vers `__class__`), fonctions comme valeurs (bac_a_calcul.py:30-33, `_refus` générique sur tout node non reconnu)
- **Expressions** : arithmétique (`+ - * / // % **`), comparaisons, `and/or/not`, ternaire `x if c else y`, listes/tuples/dicts littéraux (sans `*args`), indices et tranches, compréhensions de liste/génératrice (une seule clause `for`, pas d'async) (bac_a_calcul.py:357-419, 492-507)
- **Appels** : uniquement vers `FONCTIONS` = primitives numériques réécrites (`abs, min, max, sum, round, len, range, sqrt, log, exp`) + `CATALOGUE` de `calculs.py` (bac_a_calcul.py:145-157)
- **Bornes** : code ≤ 20 000 caractères (`LIMITE_CODE`), conteneurs ≤ 10 000 éléments (`LIMITE_ELEMENTS`), budget d'opérations 200 000 (`BUDGET_PAR_DEFAUT`), entiers > 2^53 convertis en flottant, `croissance_implicite` coûte 5000 opérations par appel (`_COUT_APPEL`) (bac_a_calcul.py:62-65, 164)
- **Hypothèses GELÉES** : dicts transformés en `_Gele` (sous-classe de `dict` qui lève `ErreurCalcul` sur toute mutation, y compris via un alias), listes en tuples — la mécanique ne peut jamais réécrire le tableau signé (bac_a_calcul.py:188-207)
- **Noms d'hypothèse réservés** : ne peuvent pas coïncider avec un nom de `FONCTIONS` ni être un mot-clé Python (bac_a_calcul.py:518-520)
- Toute défaillance rend `ErreurCalcul` nommée — jamais une autre exception (contrat de sortie, bac_a_calcul.py:37-39, 510-546)

### `app/valorisation/calculs.py` — `CATALOGUE` : les calculs fermés et leurs entrées

Détenteur unique de ce qu'une mécanique peut appeler (calculs.py:207-216). 13 gabarits :

| Fonction | Entrées | Refuse si |
|---|---|---|
| `valeur_sans_croissance` | `benefice_normalise`, `cout_du_capital` | coût du capital ≤ 0 (calculs.py:67-74) |
| `actualiser` | `flux` (liste), `taux`, `annee_depart=1` | taux ≤ −100 % (calculs.py:77-82) |
| `valeur_terminale` | `flux_final`, `taux`, `croissance` | taux ≤ croissance (Gordon diverge, calculs.py:85-96) |
| `dcf` | `flux`, `taux`, `croissance_terminale` | hérite des refus ci-dessus (calculs.py:99-104) |
| `flux_en_croissance` | `flux_initial`, `croissance`, `annees` | `annees` non entier ou hors [1,100] (calculs.py:107-114) |
| `croissance_implicite` | `valeur_cible`, `flux_initial`, `taux`, `annees`, `croissance_terminale` | flux initial ≤ 0 ; prix hors [−50 %, +100 %] l'an (bissection, 200 itérations, calculs.py:117-149) |
| `valeur_ponderee` | `probabilite_de_succes`, `valeur_si_succes`, `cout_restant=0` | probabilité hors [0,1] (calculs.py:152-158) |
| `valeur_fonds_propres` | `valeur_entreprise`, `dette_nette` | — (calculs.py:161-164) |
| `actions_diluees` | `actions_en_circulation`, `actions_potentielles` | circulation ≤ 0 ou potentielles < 0 (calculs.py:167-174) |
| `dilution` | `actions_en_circulation`, `actions_nouvelles` | hérite de `actions_diluees` (calculs.py:177-180) |
| `valeur_par_action` | `valeur_fonds_propres`, `nombre_actions` | actions ≤ 0 (calculs.py:183-187) |
| `marge_de_securite` | `prix`, `valeur` | valeur ≤ 0 (calculs.py:190-195) |
| `fourchette` | `bas`, `central`, `haut` | non ordonné (calculs.py:198-204) |

### `app/valorisation/signature.py` — la signature (hors périmètre détaillé de cette tâche, repéré pour mémoire)

Deux registres append-only (`modeles_valorisation`, `modeles_valorisation_decisions`). `servir_atelier` rejoue contre le dossier du jour : proposition non décidée la plus récente = « en attente », la signée reste affichée tant qu'aucune autre n'est signée, un modèle signé qui ne tient plus devient « à revoir » (ARCHITECTURE.md:42-50). API : `backend/app/api/valorisation_v2.py` (détail §6 ci-dessous).

---

## 2. Le framework `valorisation` (va_1…va_6) — `backend/app/frameworks/frameworks.yaml:1783-2007`

Méthodologie déclarée (frameworks.yaml:1786-1791) : « Valorisation multi-lentilles (Greenwald, Damodaran, Mauboussin) … L'analyste établit une fourchette de valeur, jamais un point … Il reprend les chiffres normalisés des autres méthodologies, il ne les recalcule pas. » `nature_dominante: mesure`, `lit_le_socle: true` (frameworks.yaml:1792-1794).

Note transversale (frameworks.yaml:1775-1782) : « UN SEUL MODÈLE, JAMAIS DEUX CHIFFRES » — un ingrédient qui porte `repris_de` EST le chiffre de la réponse qui tient à cette question (#99) : il ne se collecte jamais. Si la question est sans objet pour ce titre, le modèle porte son propre chiffre (pièce ou jugement ancré). « Repris de » dans un libellé de va_4/va_5 décrit un CALCUL qui s'appuie sur une reprise, pas un ingrédient repris tel quel.

**Toutes les questions va_1..va_6 ont `chiffres_cles: []`** (frameworks.yaml:1828, 1870, 1905, 1937, 1969, 1997) — AUCUN encadré n'existe encore pour le framework valorisation lui-même (cohérent avec « valorisation : rien » dans 00-REPRISE.md pour NVDA).

| Question | Énoncé | `repris_de` (ingrédient → question(s)) |
|---|---|---|
| va_1 (frameworks.yaml:1797-1839) | Combien vaut l'entreprise sans croissance ? | `resultat_normalise` ← `[qf_1, qf_6]` ; `taux_d_actualisation` ← `[qf_1]` ; `passage_a_la_valeur_par_action` ← `[qf_4]` ; `nombre_d_actions_dilue` (au_cours_du_jour, pas repris) ; `valeur_des_actifs` (jugement, non essentiel) |
| va_2 (frameworks.yaml:1840-1881) | Fourchette bas/central/haut et hypothèses qui séparent les scénarios | `cout_de_la_croissance` ← `[qf_3, qf_2]` ; `duree_et_plafond_de_la_croissance` ← `[mo_4, me_5]` ; `dilution_future` ← `[qf_4, qf_7]` (non essentiel) ; `hypotheses_decisives` = jugement, non repris |
| va_3 (frameworks.yaml:1882-1916) | Classe de référence historique | aucun ingrédient `repris_de` — tout en jugement |
| va_4 (frameworks.yaml:1917-1948) | Ce que suppose le prix | `croissance_implicite` « au taux exigé par le fonds repris de qf_1 » (texte du libellé, pas un champ `repris_de` structuré sur cet ingrédient) ; `cours_cote_date` au_cours_du_jour ; `comparaison_aux_scenarios` jugement |
| va_5 (frameworks.yaml:1949-1980) | Prix vs pairs et historique | aucun `repris_de` structuré — jugement + au_cours_du_jour |
| va_6 (frameworks.yaml:1981-2007) | Marge de sécurité | aucun `repris_de` structuré — `prix_et_fourchette` (au_cours_du_jour) + `hypothese_portante` (jugement) |

---

## 3. Chiffres clés des 5 autres frameworks (question → encadré)

Mapping des préfixes : `qf_*` = Qualité financière (qualite_financiere, frameworks.yaml:269-773, 8 questions) · `mo_*` = Défendabilité (defendabilite, frameworks.yaml:774-1018, 6 questions) · `me_*` = Modèle économique (modele_economique, frameworks.yaml:1019-1272, 6 questions) · `se_*` = Secteur et concurrence (secteur_concurrence, frameworks.yaml:1273-1512, 6 questions) · `ma_*` = Management et allocation du capital (management_capital, frameworks.yaml:1513-1782, 7 questions).

**Sur les 33 questions des 5 frameworks, SEULES 9 questions déclarent un encadré non vide** : qf_1, qf_2, qf_3, qf_4, qf_5, qf_6, qf_7, mo_4, me_5. Toutes les autres (qf_8, mo_1, mo_2, mo_3, mo_5, mo_6, me_1, me_2, me_3, me_4, me_6, se_1..se_6, ma_1..ma_7 — 24 questions) ont `chiffres_cles: []` (« non trouvé » pour chacune).

| Question | Encadré (id — libellé) | Unité | Période |
|---|---|---|---|
| **qf_1** (frameworks.yaml:318-332) | `rendement_du_capital_employe` — Rendement du capital employé (socle : ratio `rendement_du_capital_employe_moyen`) | % | moyenne 5 ans |
| | `cout_du_capital` — Taux exigé par le fonds (décision du comité, `parametre_du_fonds: taux_exige`) | % | à la date de la décision du comité |
| | `resultat_operationnel_apres_impot_normalise` — Résultat d'exploitation après impôt normalisé | M$ | dernier exercice |
| **qf_2** (frameworks.yaml:378-383) | `part_du_resultat_en_tresorerie` — Part du résultat net retrouvée en trésorerie (socle : ratio `part_du_resultat_en_tresorerie`) | % | moyenne 3 ans |
| **qf_3** (frameworks.yaml:427-432) | `capital_par_point_de_croissance` — Capital supplémentaire par point de croissance (socle : ratio `capital_par_point_de_croissance`) | M$ | derniers exercices observés |
| **qf_4** (frameworks.yaml:484-519) | `dette_brute` (socle : formule) | M$ | dernier bilan |
| | `tresorerie_et_placements` (socle : formule) | M$ | dernier bilan |
| | `dette_nette` (= dette_brute − tresorerie_et_placements, calculé par le code) | M$ | dernier bilan |
| | `resultat_exploitation_douze_mois` (socle : formule, 12 mois) | M$ | douze mois glissants |
| | `charges_interets_douze_mois` (socle : formule, 12 mois) | M$ | douze mois glissants |
| | `couverture_des_interets` (= résultat expl. / charges intérêts, calculé ; « n.s. » si résultat négatif) | fois | douze mois glissants |
| **qf_5** (frameworks.yaml:594-599) | `pente_du_rendement` (socle : ratio `pente_du_rendement`) | points/an | sur 5 ans ou plus |
| **qf_6** (frameworks.yaml:648-676) | `retraitements_exercice_clos` (relevé par l'analyste) | M$ | dernier exercice clos |
| | `retraitements_cumul_en_cours` (relevé) | M$ | cumul de l'exercice en cours |
| | `retraitements_cumul_an_passe` (relevé) | M$ | même cumul, exercice précédent |
| | `retraitements_discretionnaires` (calculé = exercice_clos + cumul_en_cours − cumul_an_passe) | M$ | douze mois glissants |
| | `resultat_net_douze_mois` (socle : formule) | M$ | douze mois glissants |
| | `part_des_retraitements` (calculé = retraitements/resultat_net×100 ; n.c. si dénominateur négatif) | % | douze mois glissants |
| **qf_7** (frameworks.yaml:730-758) | `tresorerie_mobilisable` (socle : formule) | M$ | dernier bilan |
| | `consommation_constatee` (socle : formule `-flux_de_tresorerie_disponible`, 12 mois) | M$ | quatre derniers trimestres publiés |
| | `consommation_prevue` (relevé, facultatif, prévision direction) | M$ | exercice en cours (prévision) |
| | `consommation_retenue` (= le plus élevé des deux ci-dessus) | M$ | la plus prudente des deux |
| | `autonomie` (= tresorerie_mobilisable / consommation_retenue × 12, calculé) | mois | à la date du dernier bilan |
| **qf_8** | — | — | — *(non trouvé : `chiffres_cles: []`, frameworks.yaml:556)* |
| **mo_1..mo_3, mo_5, mo_6** | — | — | — *(non trouvé : encadrés vides)* |
| **mo_4** (frameworks.yaml:922-926) | `duree_retenue` — Durée pendant laquelle la barrière tient si rien ne change | années | à la date de l'analyse |
| **me_1..me_4, me_6** | — | — | — *(non trouvé : encadrés vides)* |
| **me_5** (frameworks.yaml:1205-1213) | `marche_adressable` — Taille du marché adressable par le modèle actuel | M$ | à la date de l'analyse |
| | `part_deja_prise` — Part du marché adressable déjà prise | % | dernier exercice |
| **se_1..se_6** | — | — | — *(non trouvé : encadrés vides sur les 6 questions du secteur/concurrence)* |
| **ma_1..ma_7** | — | — | — *(non trouvé : encadrés vides sur les 7 questions de management/allocation)* |

Point notable pour le « modèle de l'entreprise » : **`me_5.marche_adressable` et `me_5.part_deja_prise` sont, à ce jour, le SEUL encadré qui porte une notion de marché/segment** — et le 00-REPRISE.md (ligne 23) dit explicitement que « me_5 → tableau des marchés (9) » est ABSORBÉ par le chantier du modèle de l'entreprise. Aucun autre framework ne porte de chiffre par segment/bloc de marché.

---

## 4. `parametres_du_fonds` — table et lecture

**Ce n'est PAS une table SQL** : c'est une clé du YAML `frameworks.yaml`, validée par le schéma Pydantic `ParametreDuFonds` (`backend/app/contracts/framework_definition_schema.py:201-216`).

Contenu actuel (`frameworks.yaml:255-264`, un seul paramètre déclaré) :
```yaml
parametres_du_fonds:
  taux_exige:
    valeur: 10
    unite: "%"
    decide_le: 2026-10-17
    revoir_avant: 2027-10-17
    decision: "Comité du 2026-10-17 … taux unique pour tout le fonds, coût d'opportunité …"
```

Schéma `ParametreDuFonds` (framework_definition_schema.py:201-210) : `valeur: float`, `unite: str`, `decide_le: date`, `revoir_avant: date`, `decision: str (≥20 car.)` — avec validateur `revoir_avant > decide_le` (framework_definition_schema.py:212-216).

**Lecture** :
- Un chiffre d'encadré référence un paramètre via `parametre_du_fonds: <nom>` (ex. `qf_1.cout_du_capital`, frameworks.yaml:328).
- Garde de cohérence à la définition (pont `[W]`, `backend/app/agents/v2/frameworks.py:421-434`) : le nom doit exister dans `parametres_du_fonds`, et son `unite` doit coïncider avec celle déclarée au chiffre — sinon refus `FrameworkDefinitionRefused`.
- Lecture effective à la construction de l'encadré, `chiffres_du_fonds(q, fichier.parametres_du_fonds)` (`backend/app/agents/v2/analyste.py:510` et appel ligne 621) — pose le chiffre tel quel, daté par la décision du comité, jamais collecté (`backend/app/agents/v2/frameworks.py:958-965` : fonction similaire pour un autre chemin, lit `load_frameworks().parametres_du_fonds`, construit `ChiffreCle(valeur=p.valeur, date_ou_periode="décision du fonds du <decide_le> (comité), à revoir avant le <revoir_avant>")`, ou `motif_absence` si le nom n'existe pas).
- Un retrait historique existe : `backend/tools/retraits/2026-10-19_taux_exige_qf1.sql` (commentaire ligne 2 : le taux exigé était auparavant collecté/affiché différemment, désormais reçu du code via `parametres_du_fonds.taux_exige`).

---

## 5. Le socle des comptes (`montrer_socle.sh NVDA`)

Commande exacte exécutée :
```
bash backend/tools/montrer_socle.sh NVDA
```
Lanceur (`backend/tools/montrer_socle.sh:1-11`) : conteneur neuf (image de `portfolio-backend` inspectée, PAS le conteneur en prod), réseau `coolify`, dépôt monté `:ro`, réseau public uniquement (data.sec.gov), ni base ni modèle. Gratuit, lecture seule — conforme à l'interdit.

Sortie (30 premières lignes utiles, horodatage dépôt `0001045810-26-000075`, formulaire `10-Q` déposé `2026-08-26`) :

```
══════ NVDA — gabarit 1.1.0 — dernier dépôt lu {'accn': '0001045810-26-000075', 'form': '10-Q', 'filed': '2026-08-26'}
  RECLASSEMENT → participations : EquitySecuritiesWithoutReadilyDeterminableFairValueAmount — …
  RECLASSEMENT → participations_courantes : EquitySecuritiesFvNi — …

  Compte de résultat (M$)   [≈ par différence · Σ par somme · ƒ calculé · 0 compté zéro · · non déposé]
                                                   FY2022-01-30   FY2023-01-29   FY2024-01-28   FY2025-01-26   FY2026-01-25  TTM2026-07-26
  Chiffre d'affaires                                 26 914.0       26 974.0       60 922.0      130 497.0      215 938.0      302 970.0
  Coût des ventes                                     9 439.0       11 618.0       16 621.0       32 639.0       62 475.0       76 729.0
  Marge brute                                        17 475.0       15 356.0       44 301.0       97 858.0      153 463.0      226 241.0
  Recherche et développement                          5 268.0        7 339.0        8 675.0       12 914.0       18 497.0       23 592.0
  Frais commerciaux, généraux et administratifs       2 166.0        2 440.0        2 654.0        3 491.0        4 579.0        5 070.0
  Résultat d'exploitation                            10 041.0        4 224.0       32 972.0       81 453.0      130 387.0      197 579.0
  Produits financiers (intérêts reçus)                   29.0          267.0          866.0        1 786.0        2 300.0        2 229.0
  Charges d'intérêts                                    236.0          262.0          257.0          247.0          259.0          464.0
  Résultat avant impôt                                9 941.0        4 181.0       33 818.0       84 026.0      141 450.0      229 743.0
  Impôt sur les résultats                               189.0         -187.0        4 058.0       11 146.0       21 383.0       36 863.0
  Résultat net part du groupe                         9 752.0        4 368.0       29 760.0       72 880.0      120 067.0      192 880.0

  Bilan (M$)   [...]
                                                    B2021-01-31  …  B2026-07-26
  Trésorerie et équivalents / Placements CT et LT / Créances clients / Stocks /
  Participations cotées / Autres actifs courants / Actif courant / Immobilisations /
  Droits d'utilisation / Écarts d'acquisition / Immobilisations incorporelles /
  Participations non cotées / Total de l'actif / Dettes fournisseurs / Dette financière
  (CT et LT) / Obligations locatives / Total des dettes / Capitaux propres /
  Capital employé dans l'exploitation (ƒ) / Capital employé hors écarts d'acquisition (ƒ)

  Tableau des flux de trésorerie (M$) [...] : Dotations aux amortissements, Rémunération
  en actions, Variation BFR, Flux expl., Investissements corporels, Acquisitions,
  Flux d'investissement, Émissions/rachats d'actions, Dividendes, Flux de financement,
  Variation de trésorerie, Flux de trésorerie disponible (ƒ)

Ratios maison (définitions 1.0.0) — par exercice clos :
  Taux d'impôt retenu (%), Résultat d'exploitation après impôt (M$), Capital employé
  moyen (M$), Rendement du capital employé (%), Rendement hors écarts d'acquisition (%),
  Marge d'exploitation après impôt (%), Rotation du capital employé (fois),
  + agrégats sur 5 ans : rendement moyen, pente, part du résultat en trésorerie (3 ans),
  capital par point de croissance

  Contrôles : 26 dont 0 écart(s)
BILAN socle — NVDA : 13 périodes, 383 cellules (depose 273, par_difference 64, par_somme 0,
calcule 20, compte_zero 26, non_depose 0), 26 contrôles, 0 écart(s), 0 refus
```
(Commande sortie avec code 0.)

**Postes disponibles** : compte de résultat consolidé (CA, coût des ventes, marge brute, R&D, SG&A, résultat d'exploitation, résultat financier, résultat avant impôt, impôt, résultat net), bilan consolidé (trésorerie, placements, créances, stocks, participations cotées/non cotées, immobilisations, écarts d'acquisition, dette CT/LT, obligations locatives, capitaux propres, capital employé calculé), tableau des flux (exploitation, investissement, financement, flux disponible calculé). Ratios maison dérivés (rendement du capital employé, marge d'exploitation après impôt, rotation, pente sur 5 ans, part du résultat en trésorerie, capital par point de croissance).

**Périodes disponibles** : exercices fiscaux annuels (FY2022-01-30 … FY2026-01-25, soit 5 clôtures), un cumul douze mois glissants (TTM2026-07-26), et 7 instants de bilan (B2021-01-31 … B2026-07-26) — total 13 périodes annoncé dans le bilan final.

**SURTOUT — décomposition par segment/marché** : **NON TROUVÉE dans le socle**. `grep -rn "segment"` dans `backend/app/knowledge/` (gabarit, `socle_comptes.py`, `ratios_maison.py`) ne retourne aucune correspondance pertinente (seules des correspondances dans des fichiers V3 sans rapport : `synthesis_feed.py`, `appariement_feed.py`, et le schéma de `modele_valorisation_schema.py`/`signature_modele_schema.py`/`collection_plan_schema.py` qui parlent du découpage de marché PROPOSÉ par l'agent dans le modèle de valorisation — pas d'un fait du socle). Le module `socle_comptes.py` (classes `Gabarit`, `Ligne`, `Cellule`, `Periode`, `Equation`, `Terme` — `backend/app/knowledge/socle_comptes.py:81-310`) est entièrement bâti sur des CONCEPTS consolidés (un gabarit unique de reconstitution comptable), sans dimension segment/marché. Une seule trace textuelle existe ailleurs dans le code : un commentaire d'exemple dans `backend/app/contracts/framework_answer_schema.py:149` (« la note peut dire "le Data Center fait 92,4 % du chiffre d'affaires" ») — qui décrit le mécanisme générique `CalculMontre` (un calcul texte avec termes sourcés par pièce, `framework_answer_schema.py:146-157`), PAS une structure de données par segment : c'est un calcul libre que l'analyste peut écrire dans sa prose, recoupé a posteriori, pas un poste du socle ni une colonne dédiée en base. Aucune table SQL « segment » n'existe (`find … -iname "*.sql" | xargs grep -l segment` ne remonte aucune migration/seed consacrée aux segments d'activité).

---

## 6. `api/valorisation_v2.py` et le frontend

**Endpoints servis** (`backend/app/api/valorisation_v2.py:38-68`) :
- `GET /v2/tickers/{ticker_id}/valorisation` → `AtelierServi` (le modèle signé courant + la version en attente, rejoués contre le dossier du jour via `servir_atelier`)
- `POST /v2/tickers/{ticker_id}/valorisation/v/{version}/signer` → signe une version en attente
- `POST /v2/tickers/{ticker_id}/valorisation/v/{version}/ecarter` → écarte une version, motif requis

Pas de route « proposer » : le geste « proposer un modèle » (l'agent qui écrit la mécanique) n'est pas construit (confirmé par `backend/app/valorisation/ARCHITECTURE.md:54-56`, section « Pas encore construit »).

**Page frontend qui affiche cet atelier** : NON TROUVÉE. `grep -rni "valorisation" frontend/` (hors `node_modules`) ne fait apparaître aucun appel à `/v2/tickers/{ticker_id}/valorisation` ni à `AtelierServi`. Les seules occurrences du mot « Valorisation » dans le frontend sont des titres de section sur d'autres objets (thèse V2 : `valuation_range`/`valuation_range_figee`, analyses V2, memos de recherche, mockups HTML statiques).

**`frontend/pages/v2/tickers/[ticker_id]/decision.js`** : lit l'ANCIENNE THÈSE V2, pas le dossier/atelier V3. Preuve :
- Appels réseau : `fetch(`${API}/v2/theses?ticker_id=…`)` (decision.js:257) puis `fetch(`${API}/v2/theses/${cible.id}`)` (decision.js:265), et éventuellement `fetch(`${API}/analyses/${detail.synthesis_analysis_id}`)` (decision.js:273) — AUCUN appel à `/v2/tickers/{ticker_id}/valorisation`.
- Le composant `BlocFige` (decision.js:25-90) affiche des champs hérités de la thèse V2 : `these.verdict`, `these.position_sizing_pct`, `these.synthesis_analysis_id`, `these.research_memo_id`, `these.schema_version`, `these.status`, et la section « Fourchette de valorisation » lit `these.valuation_range` / `these.valuation_range_figee` (`{low, base, high}`) — ce sont les champs de l'objet thèse V2 (« handoff opportunity→thesis », convention #12), pas les champs du contrat `ModeleValorisation` (`segments`, `hypotheses`, `fourchette.scenarios/evenements`).
- Le commentaire de tête du bloc (decision.js:21-24) confirme : « le verdict, le sizing et les conditions d'entrée sont produits par la synthèse et lus en base … jamais des champs de saisie ».

---

## Chemin du rapport

`/tmp/claude-0/-root/963d5c7b-2efa-4da6-8cd7-bf2cc236041c/scratchpad/inventaire_modele_entreprise.md`

## Commandes exécutées (avec code de sortie)

1. `cat`/`ls` initiaux de contexte (CLAUDE.md, 00-REPRISE.md) via l'outil Read — pas de commande shell.
2. `ls backend/app/contracts/ ; ls backend/app/valorisation/ ; ls backend/app/frameworks/` — exit 0
3. `grep -rn "modele_valorisation_schema" backend/app/contracts/` — exit 0
4. `grep -n "^va_\|^  va_\|repris_de\|^- id: va\|id: va_" backend/app/frameworks/frameworks.yaml` — exit 0
5. `grep -n "^  - id:" backend/app/frameworks/frameworks.yaml` — exit 0
6. `grep -n "^      - id: [a-z]*_[0-9]*$" backend/app/frameworks/frameworks.yaml` — exit 0
7. `awk 'NR>=269 && NR<=1782' … | grep -n "^      - id:\|chiffres_cles:"` — exit 0
8. `grep -rn "parametres_du_fonds" backend/ --include=*.py --include=*.sql | grep -v "/checks/\|test_"` — exit 0
9. `find . -iname "*montrer_socle*"` — exit 0
10. `sed -n '540,570p' backend/app/contracts/framework_definition_schema.py ; grep -n "^parametres_du_fonds:" -A 20 backend/app/frameworks/frameworks.yaml` — exit 0
11. `grep -n "class ParametreDuFonds" -A 15 backend/app/contracts/framework_definition_schema.py ; grep -n "def chiffres_du_fonds" -A 25 backend/app/agents/v2/frameworks.py` — exit 0
12. `docker ps --format '{{.Names}}' | grep portfolio` — exit 0
13. `grep -rn "def chiffres_du_fonds" backend/` — exit 0
14. `sed -n '415,440p' backend/app/agents/v2/frameworks.py ; sed -n '950,965p' backend/app/agents/v2/frameworks.py` — exit 0
15. **`bash backend/tools/montrer_socle.sh NVDA`** (gratuit, lecture seule, réseau public uniquement) — exit 0
16. `grep -rln "valorisation_v2\|/valorisation" frontend/pages 2>/dev/null ; find frontend/pages -path "*v2/tickers*"` — exit 0 (le premier grep n'a rien trouvé, normal : vide)
17. `grep -rni "valorisation" frontend/ 2>/dev/null | grep -v node_modules` — exit 0
18. `grep -n "fetch(\|API}\|useEffect\|endpoint\|/v2/theses\|/theses/" "frontend/pages/v2/tickers/[ticker_id]/decision.js"` — exit 0
19. `grep -rln "segment" backend/app/knowledge/ backend/app/contracts/ 2>/dev/null` — exit 0
20. `grep -rni "data center\|gaming\|par segment\|segment_reporting\|StatementBusinessSegments\|reportable segment" backend/app --include=*.py` — exit 0
21. `find . -iname "*.sql" | xargs grep -ln -i "segment"` — exit 0 (aucune ligne correspondante listée dans les fichiers trouvés, confirmé par lecture)

Plus plusieurs lectures de fichiers via l'outil Read (pas des commandes bash) : `modele_valorisation_schema.py`, `valorisation/ARCHITECTURE.md`, `modele.py`, `calculs.py`, `bac_a_calcul.py`, sections de `frameworks.yaml` (lignes 287-760, 899-940, 1181-1225, 1760-2007), `valorisation_v2.py`, `decision.js` (1-90).

## Résumé en 5 lignes

1. Le contrat `ModeleValorisation` (v1.2.0) est précis et outillé : segments, 3 origines d'hypothèse, 2 formes de fourchette, pont `[A]-[F]` qui vérifie dossier/exécution, bac à calcul Python restreint avec 13 gabarits fermés (`CATALOGUE`) — la mécanique de calcul existe et est solide.
2. Le framework `valorisation` (va_1..va_6) est écrit mais **n'a encore aucun encadré de chiffres clés** (`chiffres_cles: []` partout) ; il reprend des ingrédients déclarés par `repris_de` vers qf_1/qf_2/qf_3/qf_4/qf_6/qf_7, mo_4, me_5.
3. Sur les 33 questions des 5 autres frameworks, **seules 9 ont un encadré rempli** (les 7 de qf sauf qf_8, plus mo_4 et me_5) ; les 24 autres (dont la totalité de secteur/concurrence et de management) n'ont aucun chiffre structuré à relire.
4. Le socle des comptes (`montrer_socle.sh`) ne connaît QUE la consolidation : compte de résultat, bilan, flux, ratios maison sur des exercices/TTM/instants — **aucune décomposition par segment ou marché n'existe en base ni dans le gabarit** ; `me_5.marche_adressable`/`part_deja_prise` est le seul embryon de notion de marché, et le 00-REPRISE.md dit qu'il est absorbé par le futur modèle de l'entreprise.
5. L'atelier de valorisation V3 (API `valorisation_v2.py` : GET/signer/écarter) n'a **aucune page frontend qui l'affiche** ; `decision.js` lit l'ancienne thèse V2 (`/v2/theses`, `valuation_range`/`valuation_range_figee`), pas le dossier V3 — le futur outil à onglets devra créer cet écran de zéro.
