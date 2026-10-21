# M0 — Mesure : ce que les dépôts EDGAR portent comme ventilation par segment/marché

Lecture seule. Aucune écriture en base, aucun appel de modèle payant, aucune modification du dépôt.
User-Agent utilisé (repris de `backend/app/knowledge/edgar_facts.py:_UA`) :
`portfolio-tracker/2.0 (research contact plm@lm-associes.com)`. Débit : une requête à la fois,
`sleep 0.25`-`0.3` s entre appels (< 4/s).

Émetteurs et CIK confirmés via `https://www.sec.gov/files/company_tickers.json` (HTTP 200) :
- NVIDIA : CIK **1045810**
- Revolution Medicines : CIK **1628171** (trouvé dans le registre — titre `Revolution Medicines, Inc.`,
  pas le CIK 19617 donné pour mémoire dans l'énoncé qui est en fait celui de JPM)
- JPMorgan Chase & Co : CIK **19617**

Dernier 10-K / 10-Q de chacun, via `https://data.sec.gov/submissions/CIK{cik:010d}.json` (HTTP 200×3) :

| Émetteur | 10-K (accession, clôture, dépôt) | 10-Q (accession, clôture, dépôt) |
|---|---|---|
| NVDA | 0001045810-26-000021 — exercice clos 2026-01-25, déposé 2026-02-25 | 0001045810-26-000075 — période close 2026-07-26, déposé 2026-08-26 |
| RVMD | 0001193125-26-071563 — exercice clos 2025-12-31, déposé 2026-02-25 | 0001193125-26-335104 — période close 2026-06-30, déposé 2026-08-05 |
| JPM | 0001628280-26-008131 — exercice clos 2025-12-31, déposé 2026-02-13 | 0001628280-26-054343 — période close 2026-06-30, déposé 2026-08-06 |

Je n'ai exploité que le **10-K** de chacun (c'est lui qui porte les notes de segment annuelles complètes ;
le 10-Q n'a pas été ouvert, hors budget de la mesure — à noter si M2 en a besoin pour le trimestre).

---

## 1. `companyfacts`/`companyconcept` ne porte AUCUNE dimension — confirmé

Requête : `GET https://data.sec.gov/api/xbrl/companyconcept/CIK0001045810/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax.json`
→ HTTP 200.

Chaque point de la série `units.USD` n'a que ces clés :
`{'start', 'end', 'val', 'accn', 'fy', 'fp', 'form', 'filed', 'frame'}`

Exemple réel (dernier exercice avant FY2026) :
```
{'start': '2021-02-01', 'end': '2022-01-30', 'val': 26914000000, 'accn': '0001045810-22-000036',
 'fy': 2022, 'fp': 'FY', 'form': '10-K', 'filed': '2022-03-18', 'frame': 'CY2021'}
```
Aucun champ `segment`, `axis`, `member` ou `dim`. C'est une propriété de l'**API** elle-même
(`companyconcept` et `companyfacts` ne rendent QUE les faits sans qualificateur dimensionnel — les
mêmes faits qu'expose l'API `frames`), pas un trou côté NVDA ni côté `backend/app/knowledge/socle_comptes.py`
qui lit cette même API. §7 du roadmap est donc confirmé : le socle ne peut structurellement pas porter
de ventilation par segment, quel que soit l'émetteur.

---

## 2. Faits XBRL dimensionnés — relevés dans le dépôt lui-même

Méthode : `FilingSummary.xml` du 10-K → liste des rapports R#.htm du « Financial Report » → repérage des
rapports dont le nom contient Segment/Disaggregation/Geographic/Revenue by → fetch du R#.htm → table lue
+ grep des tags `*Axis`/`*Member` dans le même fichier (SEC les imprime en clair dans le HTML rendu, sous
forme `gaap_StatementBusinessSegmentsAxis`, `nvda_ComputeMember`, etc.).

URLs effectivement appelées (toutes HTTP 200) :
```
https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/FilingSummary.xml
https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/R82.htm   (Reportable Segments)
https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/R84.htm   (Revenue/Long-lived assets by Region)
https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/R85.htm   (Schedule of Revenue by Market)
https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/R81.htm   (Segment Information — Narrative)
https://www.sec.gov/Archives/edgar/data/1628171/000119312526071563/FilingSummary.xml
https://www.sec.gov/Archives/edgar/data/1628171/000119312526071563/R44.htm   (Significant Segment Expenses)
https://www.sec.gov/Archives/edgar/data/1628171/000119312526071563/R62.htm   (Sanofi Collaboration — Additional Info)
https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/FilingSummary.xml
https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/R222.htm   (Business Segments & Corporate — Narrative)
https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/R223.htm   (Business Segments & Corporate — Summary)
```

### NVIDIA (FY2026, exercice clos 2026-01-25, M$)

**Axe us-gaap:StatementBusinessSegmentsAxis** (R82 — les 2 segments ASC 280 officiels) :

| Membre | Revenue | Somme vs CA consolidé (215 938) |
|---|---|---|
| nvda:ComputeAndNetworkingSegmentMember | 193 479 | |
| nvda:GraphicsSegmentMember | 22 459 | |
| **Somme** | **215 938** | **écart = 0** |

**Axe srt:ProductOrServiceAxis** (R85 — « Revenue by Market », la maille commentée dans le rapport de
gestion) :

| Membre | Revenue | Somme vs CA consolidé |
|---|---|---|
| nvda:DataCenterMember | 193 737 | dont nvda:ComputeMember 162 361 + nvda:NetworkingMember 31 376 (= 193 737, écart 0) |
| nvda:GamingMember | 16 042 | |
| nvda:ProfessionalVisualizationMember | 3 191 | |
| nvda:AutomotiveMember | 2 349 | |
| nvda:OEMAndOtherMember | 619 | |
| **Somme des 5 marchés** | **215 938** | **écart = 0** |

⚠️ Les deux ventilations (segments vs marchés) ne sont PAS la même maille : Graphics (segment, 22 459)
≠ Gaming+ProViz+Auto+OEM&Other (marchés, 22 201) — écart de 258 M$ (poste de réallocation interne non
détaillé dans les rapports consultés).

**Axe srt:StatementGeographicalAxis** (R84 — CA par région) :

| Membre | Revenue | Somme vs CA consolidé |
|---|---|---|
| United States | 149 617 | |
| Taiwan | 42 345 | |
| China (including Hong Kong) | 19 677 | |
| Other | 4 299 | |
| **Somme** | **215 938** | **écart = 0** |

**Axe srt:MajorCustomersAxis** (R81, narratif) : pas de CA par client, mais un **pourcentage de
concentration** par client anonymisé (`nvda:CustomerOneMember`, `nvda:CustomerTwoMember`) sur le CA du
segment Compute & Networking — ex. Customer one 22 % en FY2026, 12 % en FY2025, 13 % en FY2024. C'est
le fait qui fonde me_6 (« une poignée de clients directs pèse une large part des ventes ») — un fait
XBRL dimensionné, pas une impression de lecture.

### Revolution Medicines (FY2025, exercice clos 2025-12-31, M$)

**Pas d'axe de segment produit/géographique** pour le CA : `us-gaap:StatementBusinessSegmentsAxis`
n'apparaît dans aucun rapport autre que le générique `OperatingSegmentsMember` sur les dépenses R&D
(aucun membre nommé type segment — compatible avec un émetteur à un seul segment opérationnel, mais je
n'ai pas lu de phrase narrative l'affirmant explicitement, donc je ne l'affirme pas comme fait établi).

**CA** (R62, détail de l'accord Sanofi) : `us-gaap:RevenueFromCollaborativeArrangementExcludingRevenueFromContractWithCustomer`
= 0,0 M$ (FY2025), 0,0 M$ (FY2024), 11,6 M$ (FY2023). Aucune dimension produit (pas de membre
« daraxonrasib » / « RASONQUE » / « zoldonrasib »). Non trouvé : CA par produit.

**R&D par catégorie de coût** (R44 — « Significant Segment Expenses », exigé par ASU 2023-07 même pour
un émetteur à un seul segment), axe `us-gaap:StatementBusinessSegmentsAxis` avec le seul membre
`OperatingSegmentsMember` :

| Poste | FY2025 (k$) |
|---|---|
| Third-party research and development expenses (rvmd:ThirdPartyResearchAndDevelopmentExpenses) | 631 291 |
| Salaries and other employee-related expenses | 189 064 |
| Stock-based compensation expense | 78 356 |
| Amortization of intangible assets | 870 |
| Other research and development costs | 87 751 |
| **Total R&D** | **987 332** |

Non trouvé : ventilation par programme/indication (daraxonrasib pancréas 2ᵉ ligne, 1ʳᵉ ligne, poumon ;
zoldonrasib). Le découpage disponible est par **nature de coût**, company-wide, pas par **programme**.

### JPMorgan Chase (FY2025, exercice clos 2025-12-31, M$)

**Axe us-gaap:StatementBusinessSegmentsAxis**, membres : `jpm:ConsumerCommunityBankingMember` (CCB),
`jpm:CommercialAndInvestmentBankMember` (CIB), `jpm:AssetandWealthManagementSegmentMember` (AWM),
`us-gaap:CorporateNonSegmentMember` (Corporate), + une ligne `us-gaap:MaterialReconcilingItemsMember`
(« Reconciling Items », ajustement FTE).

Postes disponibles **par segment** (R223) : noninterest revenue, net interest income, total net
revenue, provision for credit losses, compensation expense, noncompensation expense, total noninterest
expense, income before tax, income tax, **net income**, **average equity**, total assets, **return on
equity**, **overhead ratio**.

| Segment | Total net revenue | Net income | Average equity | ROE | Overhead ratio |
|---|---|---|---|---|---|
| CCB | 76 029 | 18 245 | 56 000 | 32 % | 53 % |
| CIB | 78 454 | 27 761 | 149 500 | 18 % | 49 % |
| AWM | 24 073 | 6 522 | 16 000 | 40 % | 64 % |
| Corporate | 7 025 | 4 520 | 111 254 | — | — |
| Reconciling Items | −3 134 | 0 | — | — | — |
| **Somme** | **182 447** | **57 048** | — | — | — |
| **Consolidé publié** | **182 447** | **57 048** | — | — | — |

Écart = 0 sur le net revenue ET sur le net income (l'ajustement FTE de −3 134 M$ est intégralement
absorbé par la ligne impôt du segment « Reconciling Items », donc n'affecte jamais le résultat net
sommé). Pas de « coût du risque » agrégé nommé ainsi : c'est `Provision for credit losses`, disponible
par segment (ex. CCB 11 493 M$, dont `jpm:AppleCreditCardPortfolioMember` 2 200 M$ isolé en narratif).
Pas de ligne « fonds propres allouées » nommée ainsi non plus : c'est `Average equity`, bien présente
par segment (c'est le proxy réel du capital alloué, utilisé pour calculer le ROE affiché).

---

## 3. NVDA — maille calcul/réseau : fait XBRL dimensionné, PAS seulement du texte

Confirmé au §2 : `nvda:ComputeMember` (162 361 M$) et `nvda:NetworkingMember` (31 376 M$) sont deux
membres de `srt:ProductOrServiceAxis`, additionnés dans R85 pour retomber exactement sur
`nvda:DataCenterMember` (193 737 M$, écart 0). Ce n'est pas une estimation d'analyste ni du texte de
MD&A : c'est une valeur XBRL taguée, extraite du même rapport rendu que les autres membres.

## 4. RVMD — CA par produit / charges par programme

Non trouvé : aucun CA par produit (RASONQUE/daraxonrasib), aucune dimension produit/programme sur le
CA (qui est de toute façon nul en FY2025/FY2024). Non trouvé non plus : R&D par programme — la seule
ventilation disponible est par nature de coût (tiers, salaires, SBC, amortissement, autre), company-
wide, voir tableau §2.

## 5. Banque (JPM) — segments et postes

Voir tableau §2 : 4 segments (CCB, CIB, AWM, Corporate) + 1 ligne de réconciliation. Postes par
segment disponibles comme fait XBRL : noninterest revenue, net interest income, total net revenue,
provision for credit losses (= coût du risque), compensation/noncompensation expense, total
noninterest expense, income before/after tax, net income, **average equity** (= fonds propres
alloués), total assets, return on equity, overhead ratio.

## 6. Méthode la plus simple et robuste, et ses limites

**Méthode retenue** : pour un CIK donné et un formulaire (10-K/10-Q), suivre la chaîne
`submissions → accession → FilingSummary.xml → R#.htm`, toutes sous
`https://www.sec.gov/Archives/edgar/data/{cik}/{accession_sans_tirets}/…` :

1. `GET https://data.sec.gov/submissions/CIK{cik:010d}.json` → dernière accession par formulaire.
2. `GET …/{accession_nodash}/FilingSummary.xml` → liste des rapports (`ShortName`/`LongName`/
   `HtmlFileName`) ; filtrer sur des mots-clés (Segment, Disaggregat*, Geographic, Major Customer,
   Revenue by/Schedule of Revenue).
3. `GET …/{accession_nodash}/R{n}.htm` → table HTML déjà rendue (valeurs + libellés de ligne) **et**,
   dans le MÊME fichier, les noms de tags XBRL bruts (`*Axis`/`*Member`) apparaissent en clair dans la
   section de documentation sous la table — pas besoin de parser l'instance XBRL complète ni les
   contextes `xbrli:context`/`xbrldi:explicitMember`.

C'est le format **le plus simple** trouvé : pas de parsing XML/inline-XBRL lourd, une seule requête par
rapport ciblé, des libellés déjà en anglais lisible, un chiffre déjà résolu dans l'unité annoncée en
en-tête de table.

**Limites mesurées** :
- `FilingSummary.xml` ne donne NI l'espace de noms de l'axe (`us-gaap:` vs `srt:`) ni le concept us-gaap
  précis associé (ex. `Revenue` vs `RevenueFromContractWithCustomerExcludingAssessedTax`) directement
  dans sa liste de rapports — il faut ouvrir le R#.htm et grep les tags, étape supplémentaire mais peu
  coûteuse (un seul fichier de plus, déjà dans le même répertoire).
- Le nommage des rapports (`ShortName`) n'est PAS standardisé entre émetteurs : « Segment Information »
  (NVDA), « Business Segments & Corporate » (JPM), « Significant Segment Expenses » (RVMD, sous un nom
  qui ne contient même pas le mot « Segment Information » mais « Accounting Policies »). Un
  repérage par mots-clés doit rester une LISTE large (Segment, Disaggregat*, Geographic, Major
  Customer, Revenue by, Significant…Expenses), pas un nom de rapport unique attendu.
- Le numéro `R{n}` n'est pas stable entre émetteurs ni entre exercices du même émetteur (il dépend de
  l'ordre des notes dans CE dépôt) : il faut toujours repasser par `FilingSummary.xml` de l'exercice
  visé, jamais réutiliser un numéro observé une fois.
- Pas de contrat formel garantissant qu'un rapport « Segment » existe : un émetteur à un seul segment
  (cas potentiel RVMD) peut n'avoir qu'un tableau de charges, sans ventilation de CA du tout — à
  détecter par un rapport ABSENT, pas par une valeur vide.
- Cette méthode lit la mise en forme humaine du renderer SEC (texte, pas la structure dimensionnelle
  machine). Pour un appariement automatique fiable à l'axe/membre exacts (plutôt qu'au libellé affiché),
  il faudrait remonter à l'instance XBRL brute (`{accn}_htm.xml` ou le document inline lui-même) et
  lire les éléments `xbrli:context`/`xbrldi:explicitMember` — non fait ici (hors budget de la mesure),
  mais les tags `*Axis`/`*Member` relevés dans le R#.htm donnent déjà le nom exact du couple
  axe/membre à chercher dans cette instance, donc cette méthode simple sert aussi de REPÉRAGE pour la
  méthode plus robuste si M2 en a besoin.
- `companyfacts`/`companyconcept` (le socle actuel) reste hors sujet pour cette ventilation — confirmé
  au §1 — donc toute lecture par segment doit obligatoirement passer par cette chaîne FilingSummary/R,
  jamais par le socle existant.

---

## Commandes exécutées (résumé)

```
curl -A "$UA" https://www.sec.gov/files/company_tickers.json                         → 200
curl -A "$UA" https://data.sec.gov/submissions/CIK0001045810.json                    → 200
curl -A "$UA" https://data.sec.gov/submissions/CIK0001628171.json                    → 200
curl -A "$UA" https://data.sec.gov/submissions/CIK0000019617.json                    → 200
curl -A "$UA" …/1045810/000104581026000021/FilingSummary.xml                         → 200
curl -A "$UA" …/1045810/000104581026000021/R82.htm                                   → 200
curl -A "$UA" …/1045810/000104581026000021/R84.htm                                   → 200
curl -A "$UA" …/1045810/000104581026000021/R85.htm                                   → 200
curl -A "$UA" …/1045810/000104581026000021/R81.htm                                   → 200
curl -A "$UA" …/1628171/000119312526071563/FilingSummary.xml                         → 200
curl -A "$UA" …/1628171/000119312526071563/R44.htm                                   → 200
curl -A "$UA" …/1628171/000119312526071563/R62.htm                                   → 200
curl -A "$UA" …/19617/000162828026008131/FilingSummary.xml                           → 200
curl -A "$UA" …/19617/000162828026008131/R222.htm                                    → 200
curl -A "$UA" …/19617/000162828026008131/R223.htm                                    → 200
curl -A "$UA" https://data.sec.gov/api/xbrl/companyconcept/CIK0001045810/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax.json → 200
```
Aucun échec HTTP rencontré (tous codes 200). Aucune écriture, aucun commit, aucun appel de modèle payant.
Script jetable de parsing (texte de table + grep des tags Axis/Member) : fichiers Python inline dans ce
répertoire, aucun persistant hors de ce scratchpad.
