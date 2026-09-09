# Arbitrages en discussion — capacité 5 « la dégradation déclarée »

> ⚠️ **Fichier temporaire de travail.** Support de discussion, pas une spécification.
> À supprimer une fois les arbitrages tranchés et reportés dans
> `roadmap/02-spec-autorite-vs-actualite.md` + `roadmap/provenance-cards/00-REPRISE.md`.
>
> Ouvert le 2026-09-09, après la 4ᵉ réfutation du barreau 4 par la ligne de base.

---

## 0. Les faits mesurés qui ouvrent ces arbitrages

Mesureur : `backend/tools/mesure_ingredients_capacite5.py` (versionné, rejouable, aucune écriture,
aucun appel de modèle de génération, corpus assemblé par le `query_knowledge` **de production**).

- **23 questions déclarées ouvertes**, dans la prose de 6 synthèses grounded persistées
  (NVDA #53/#55/#56/#59, MSFT #112/#113). RVMD : **0 synthèse persistée**.
- Chiffre brut flatteur et **non discriminant** : 15/23 questions ramènent une entry citable hors du
  corpus de leur champ dans le top-5.
- **L'étalon réfute le critère.** #102 (tier A, `edgar_official`, « >450 M de sièges payants ») est
  l'ingrédient CONNU des 5 questions de MSFT/`produits.unit_economics` :

  | formulation de la requête | rangs de #102 | top-5 |
  |---|---|---|
  | la question **en prose**, telle qu'elle vit | `[6, 10, —, 9, —]` | **0 / 5** |
  | la même, **négation retirée** (contre-épreuve) | `[5, 15, —, 9, 16]` | **1 / 5** |

  → l'hypothèse « c'est la formulation qui pollue l'embedding » est **écartée**. Le défaut est la
  **méthode**.
- **Ce que la recherche ramène à la place** : sur 33 entries remontées en top-5, **16 ne peuvent
  structurellement pas être l'ingrédient d'une approximation chiffrée** (9 gouvernance :
  `skin_in_game_pct` ×5, `incitations` ×4 ; 7 narratif de risque : `risques_cles`). La rémunération
  du CEO arrive **r3** sur « coût par GPU ». Les tables de détention d'Amy Hood arrivent **r3** sur
  « menace de nouveaux entrants ».
- **La classe où ça marche** : NVDA/`moat_preuves`, « l'ampleur des dépenses R&D n'est pas
  documentée » → r1 *Chiffre d'affaires FY2026*, r4 *capital return* ; « investissements R&D
  massifs » → r2 *Flux de trésorerie op.*, r3 *Total actif*. Point commun : `covers=[]`, ce sont les
  **agrégats financiers de base**.

---

## 1. L'échelle, et le barreau qui casse

```mermaid
flowchart TD
    A["Le dossier a besoin d'un chiffre<br/>ex. économie unitaire de Microsoft 365"] --> B{"Le chiffre est-il<br/>dans les sources citées ?"}
    B -- oui --> OK["Fait mesuré, daté, sourcé<br/>✅ fonctionne"]
    B -- non --> C["Le dossier NOMME ce qu'il cherche<br/>✅ fonctionne — 23 questions nommées"]
    C --> D["On tente de l'obtenir<br/>✅ fonctionne"]
    D --> E{"Obtenu ?"}
    E -- non --> F["Reconstituer une ESTIMATION<br/>à partir de pièces déjà au dossier<br/>❌ CASSE ICI"]
    F --> G["Sinon : lacune assumée<br/>✅ fonctionne"]
    style F fill:#ffe0e0,stroke:#c00,stroke-width:2px
    style OK fill:#e0f0e0
    style G fill:#e0f0e0
```

## 2. Ce que la mesure révèle en creux : deux natures de trou

```mermaid
flowchart TD
    T["Un chiffre manque"] --> T1{"De quelle nature<br/>est l'ingrédient manquant ?"}
    T1 --> AGG["<b>Agrégat financier</b><br/>chiffre d'affaires, flux de trésorerie,<br/>total actif, retour au capital"]
    T1 --> OPE["<b>Métrique opérationnelle</b><br/>sièges payants, coût par GPU,<br/>coût par token, part de marché"]
    AGG --> AGG2["Vocabulaire fermé, stable,<br/>identique chez tous les émetteurs<br/>✅ la machine les retrouve"]
    OPE --> OPE2["Vocabulaire propre à l'entreprise,<br/>propre au secteur, changeant<br/>❌ la machine ne les retrouve pas"]
    style AGG2 fill:#e0f0e0
    style OPE2 fill:#ffe0e0
```

**Le paradoxe** : les agrégats financiers sont publiés et comparables, ils n'ont pas besoin d'être
estimés. Les métriques opérationnelles sont ce qui différencie réellement une entreprise et ce qui
n'est pas publié — donc ce qui vaut d'être approché. La machine sait faire ce qui ne sert pas.

---

## Arbitrage 1 — Que le dossier a-t-il le droit de faire face à un trou ?

```mermaid
flowchart TD
    Q["Un chiffre manque"] --> A["<b>A · Le trou reste un trou</b>"]
    Q --> B["<b>B · Estimation, mais jamais dans un verdict</b>"]
    Q --> C["<b>C · Estimation qui compte, à un rang inférieur</b>"]

    A --> A1["Lacune nommée, cause identifiée<br/>« non publié par la source »<br/>vs « pas encore collecté »"]
    A1 --> A2["L'investisseur fait le pont<br/>dans sa tête"]
    A2 --> A3["Aucun chiffre faux ne peut<br/>entrer au dossier"]
    A3 --> A4["Mais : trois dossiers pleins de trous<br/>ne se comparent pas entre eux"]

    B --> B1["Le dossier affiche : ordre de grandeur,<br/>méthode, hypothèses, sens de l'erreur"]
    B1 --> B2["Signalé visuellement comme<br/>une reconstitution, pas un fait"]
    B2 --> B3["Ne fonde jamais une note<br/>ni un tri entre valeurs"]
    B3 --> B4["Aide à penser, n'engage pas"]

    C --> C1["L'estimation vaut un cran<br/>sous sa pièce la plus faible"]
    C1 --> C2["Elle peut fonder un verdict<br/>de champ"]
    C2 --> C3["⚠️ Elle sera re-citée par<br/>les analyses suivantes"]
    C3 --> C4["Un chiffre approché devient<br/>indistinguable d'un chiffre mesuré<br/>trois analyses plus loin"]

    style A4 fill:#fff4d0
    style B4 fill:#e0f0e0
    style C4 fill:#ffe0e0
```

**L'asymétrie propre au long terme** : une estimation fausse qui a l'air fondée survit dans le
dossier et se fait re-citer ; un trou assumé reste inoffensif. Un dossier se relit à cinq ans, le
souvenir de « ce chiffre était une reconstitution » ne dure pas cinq ans.

---

## Arbitrage 2 — Qui nomme les ingrédients d'une estimation ?

```mermaid
flowchart TD
    S["Estimer l'économie unitaire de M365"] --> V1["<b>A · La machine cherche seule</b>"]
    S --> V2["<b>B · Le champ déclare ses ingrédients</b>"]
    S --> V3["<b>C · La machine propose, vous validez</b>"]

    V1 --> V1a["❌ RÉFUTÉ PAR LA MESURE<br/>ingrédient connu jamais dans le top-5<br/>rému du CEO remontée sur « coût par GPU »"]

    V2 --> V2a["Vous écrivez UNE FOIS la recette :<br/>« économie unitaire ≈ revenu de la ligne<br/>÷ nombre d'unités payantes »"]
    V2a --> V2b["La machine ne cherche plus,<br/>elle remplit des cases nommées"]
    V2b --> V2c["Coût : temps de modélisation<br/>Gain : vaut pour tous les émetteurs<br/>et se vérifie en le lisant"]

    V3 --> V3a["La machine propose une méthode<br/>et ses ingrédients, vous tranchez"]
    V3a --> V3b["⚠️ 23 questions ouvertes<br/>sur 3 émetteurs seulement"]
    V3b --> V3c["Passe à l'échelle par votre<br/>disponibilité, pas par le code"]

    style V1a fill:#ffe0e0
    style V2c fill:#e0f0e0
    style V3c fill:#fff4d0
```

**Le pivot** : la machine échoue à **découvrir** un ingrédient, mais n'a aucune difficulté à en
**utiliser** un qu'on lui a nommé.

⚠️ *Objection ouverte par l'utilisateur le 2026-09-09* : une recette écrite une fois pour tous les
émetteurs peut être trop rigide — chaque entreprise appelle des métriques ad hoc dépendantes de son
business. Voir la question du graphe de connaissance par ticker.

---

## Arbitrage 3 — Une estimation peut-elle jamais relever une conviction ?

```mermaid
flowchart TD
    E["Estimation produite avec<br/>un sens d'erreur déclaré"] --> D{"Règle de prudence ?"}
    D --> P1["<b>Symétrique</b><br/>l'estimation vaut dans les deux sens"]
    D --> P2["<b>Asymétrique</b><br/>elle ne peut que dégrader"]

    P1 --> P1a["« marge probablement supérieure à X »<br/>peut soutenir une thèse d'achat"]
    P1a --> P1b["⚠️ Le biais de l'analyste devient<br/>le biais du dossier"]

    P2 --> P2a["Une estimation favorable<br/>s'affiche mais ne compte pas"]
    P2a --> P2b["Une estimation défavorable<br/>compte pleinement"]
    P2b --> P2c["Le dossier ne peut jamais<br/>vous rendre plus confiant<br/>qu'un fait établi"]

    style P1b fill:#ffe0e0
    style P2c fill:#e0f0e0
```

**Coût réel de l'asymétrie** : elle rend le dossier structurellement pessimiste sur les entreprises
qui publient peu — et certaines des meilleures publient peu.

---

## Arbitrage 4 — Le silence doit-il se lire comme une couverture ?

*Non prévu. Apparu dans la mesure.*

```mermaid
flowchart TD
    M["Ce que la mesure a trouvé"] --> M1["RVMD : <b>0</b> analyse produite<br/>donc 0 trou déclaré"]
    M --> M2["NVIDIA / forces concurrentielles :<br/><b>0</b> trou déclaré"]
    M --> M3["Microsoft / forces concurrentielles :<br/><b>4</b> trous déclarés"]
    M1 --> R{"Comment un lecteur<br/>interprète-t-il ce silence ?"}
    M2 --> R
    M3 --> R
    R --> R1["« Ce dossier est complet »<br/>❌ FAUX — il n'a pas été audité"]
    R --> R2["« Ce dossier n'a pas été<br/>passé au crible »<br/>✅ vrai, mais rien ne l'affiche"]
    style R1 fill:#ffe0e0
    style R2 fill:#e0f0e0
```

**Le pire mode de panne pour une comparaison** : NVIDIA paraît mieux documenté que Microsoft sur les
forces concurrentielles alors que c'est l'inverse — Microsoft a été examiné et a déclaré ses trous,
NVIDIA ne l'a pas été. Faut-il un troisième état visible, **« non audité »** ?

---

## Recommandation initiale (2026-09-09, avant la discussion)

1 → **B** · 2 → **B** · 3 → **asymétrique** · 4 → **oui**.

Combinaison la plus cohérente avec la mesure, et la seule où le code à écrire est du code dont on
sait déjà qu'il fonctionnera.

⚠️ Cette recommandation est **antérieure** à la question de fond posée par l'utilisateur (graphe de
connaissance par ticker + reproduction de la logique d'un fonds d'investissement). Elle est
susceptible d'être caduque : l'arbitrage 2 option B présuppose un référentiel de champs commun à
tous les émetteurs, qui est précisément ce qui est remis en question.

---
---

# Arbitrage 5 — Le référentiel : formulaire fermé ou graphe par entreprise ?

*Ouvert le 2026-09-09 par l'utilisateur. **Il subsume les arbitrages 1 à 4** : ceux-ci présupposent
un référentiel de champs commun à tous les émetteurs, qui est précisément ce qui est remis en cause.*

## 5.0 Ce que le code dit, vérifié

- `backend/app/agents/v2/common.py:16` — `MVDD_SPEC` : **8 dimensions, 19 champs**, identiques pour
  tout émetteur.
- `common.py:40` — `MVDD_FIELD_PATHS : frozenset` : **vocabulaire FERMÉ**. Commentaire du code :
  *« Un tag hors vocabulaire ne fonde rien — il est écarté, pas inventé. »*
- `worker.py:141` — `_resolve_covers` : un fait trouvé par la recherche dont le `covers` n'est pas
  dans les 19 chemins est **stocké mais rattaché à rien**.
- `synthesis_feed.py:145` — `SYNTHESIS_TARGETS` : **4 cibles**, chacune avec une **requête française
  en dur** identique pour toutes les entreprises (`{company}` substitué).
- `curator.py:69` — `DECLARED_NONBLOCKING_GAPS` : l'unique échappatoire quand la grille ne va pas à
  une entreprise est une **dispense écrite à la main dans le source Python**, par couple
  (ticker, champ), suivie d'un redéploiement. Une seule dispense existe à ce jour.

## 5.1 Ce que la base dit (2026-09-09, 180 entries)

| émetteur | entries | rattachées à rien | part |
|---|---|---|---|
| MSFT | 54 | 11 | 20 % |
| NVDA | 52 | **26** | **50 %** |
| RVMD | 27 | 7 | 26 % |

**Les 26 orphelines de NVIDIA** : chiffre d'affaires ×3, résultat net ×2, marge brute, flux de
trésorerie, capitaux propres, total actif, trésorerie et dette, capex, retour au capital ×2,
trajectoire de marge brute trimestrielle (#32), **coûts de revient et provisions d'inventaire
(#33)**, marge opérationnelle par segment (#34) — **16 faits tier A, source SEC**. Plus 5 mémoires
LLM tier C et 5 context packs.

**Le champ `produits.unit_economics` compte 2 entries dans toute la base.** Les faits d'économie
unitaire de NVIDIA sont dans #32, #33, #34 — **orphelins**.

## 5.2 Le cas RVMD — la grille appliquée à une biotech clinique

```mermaid
flowchart TD
    R["RVMD · oncologie de précision<br/>phase 3, aucun produit commercialisé,<br/>aucun revenu de ventes"] --> G["La grille universelle<br/>19 champs"]

    G --> F1["financials.roic_pct<br/>plancher tier A · <b>obligatoire</b>"]
    G --> F2["financials.fcf_conversion_pct<br/>plancher tier A · <b>obligatoire</b>"]
    G --> F3["produits.unit_economics"]
    G --> F4["marche.croissance_marche_historique"]
    G --> F5["positionnement.moat_preuves"]

    F1 --> R1["entry #190 fabriquée<br/>ROIC sur une société sans revenu"]
    F2 --> R2["entry #191 : « conversion FCF<br/><b>non définie</b> »"]
    F3 --> R3["<b>0 entry</b> — pas de produit"]
    F4 --> R4["entry #186 : incidence du cancer<br/>du pancréas rangée en<br/>« croissance historique du marché »"]
    F5 --> R5["<b>0 entry</b>"]

    R3 --> Z["⇒ <b>0 synthèse grounded</b> pour RVMD<br/>3 des 4 cibles de synthèse sont vides"]
    R5 --> Z
    style R1 fill:#ffe0e0
    style R2 fill:#ffe0e0
    style R4 fill:#ffe0e0
    style Z fill:#ffe0e0,stroke:#c00,stroke-width:2px
```

**Et ce que le dossier RVMD contient vraiment** — entassé dans `business_model.description` (4) et
`business_model.drivers_revenus` (3), faute de champ propre : la plateforme RAS(ON), le pipeline et
le stade de développement, la NDA acceptée par la FDA, l'accord Royalty Pharma (2 Md$).

**Ce qui n'a aucun champ où exister** : durée de trésorerie (*cash runway*), calendrier des
lectures d'essais, probabilité de succès technique et réglementaire, population de patients
adressable, mécanismes concurrents. Pour une biotech clinique, **c'est toute la thèse
d'investissement**. L'entry #167 « Trésorerie et dette long terme » est orpheline.

## 5.3 Ce que cela fait à la capacité 5

```mermaid
flowchart TD
    A["Diagnostic de ce matin :<br/>« la recherche sémantique ne sait pas<br/>isoler l'ingrédient »"] --> B["Vrai, mais ce n'est pas la cause"]
    B --> C["#33 « coûts de revient et provisions<br/>d'inventaire » est <b>orphelin</b>"]
    C --> D["Il est <b>cité en prose</b> par la synthèse<br/>« provisions pour inventaire :<br/>détail non chiffré (#33) »"]
    D --> E["…mais absent du corpus du champ,<br/>car il ne <i>couvre</i> rien"]
    E --> F["<b>L'ingrédient n'a jamais été rangé.</b><br/>La recherche aveugle était le seul<br/>moyen de l'atteindre — et elle échoue"]
    F --> G["Le barreau 4 ne compense pas<br/>une limite de la recherche :<br/>il compense un <b>défaut de rangement</b>"]
    style F fill:#fff4d0,stroke:#c80,stroke-width:2px
    style G fill:#ffe0e0,stroke:#c00,stroke-width:2px
```

## 5.4 Les trois modèles de référentiel

```mermaid
flowchart TD
    Q["Comment le système sait-il<br/>ce qu'il faut savoir sur une entreprise ?"] --> O1["<b>A · Grille fermée</b><br/>(l'existant)"]
    Q --> O2["<b>B · Graphe libre par ticker</b>"]
    Q --> O3["<b>C · Frameworks stables,<br/>variables par entreprise</b>"]

    O1 --> A1["19 champs pour tous"]
    A1 --> A2["✅ comparabilité parfaite<br/>✅ reproductibilité<br/>✅ la porte de complétude a un sens"]
    A2 --> A3["❌ 50 % du tier A de NVDA orphelin<br/>❌ RVMD insynthétisable<br/>❌ adaptation = dispense en dur"]

    O2 --> B1["Le système construit la carte<br/>des variables propres au business"]
    B1 --> B2["✅ pertinence maximale"]
    B2 --> B3["❌ deux dossiers ne se comparent plus<br/>❌ plus de plancher opposable<br/>❌ le modèle choisit ce qu'il doit savoir<br/>= il peut omettre ce qui gêne"]

    O3 --> C1["Le <b>framework</b> est l'objet stable :<br/>« analyse du marché », « 5 forces »,<br/>« qualité des résultats », « pipeline clinique »"]
    C1 --> C2["Chaque framework pose des<br/><b>questions</b> invariantes"]
    C2 --> C3["Les <b>variables</b> qui y répondent<br/>sont propres à l'entreprise :<br/>sièges payants ici, durée de<br/>trésorerie là"]
    C3 --> C4["✅ reproductible (framework)<br/>✅ flexible (variables)<br/>✅ un framework se choisit par archétype<br/>❌ chantier de fond, touche 028/029/034"]

    style A3 fill:#ffe0e0
    style B3 fill:#ffe0e0
    style C4 fill:#e0f0e0
```

**C est la formulation littérale de l'énoncé utilisateur** : *« chaque framework est à la fois
suffisamment spécifié pour être reproductible et suffisamment flexible pour s'adapter à chaque
entreprise »*. Ce n'est pas un compromis entre A et B, c'est un axe différent : A fige les
*variables*, C fige les *questions*.

## 5.5 Ce qui manque au processus de fonds — écart par écart

```mermaid
flowchart LR
    subgraph fonds["Processus d'un fonds"]
      f1["Analyste collecte"] --> f2["Analyste analyse"]
      f2 --> f3["<b>Manager challenge<br/>les hypothèses</b>"]
      f3 --> f4["Directeur rédige le mémo"]
      f4 --> f5["<b>Comité challenge<br/>et redemande</b>"]
      f5 -.->|"éléments complémentaires"| f1
      f5 --> f6["Décision"]
    end
```

```mermaid
flowchart LR
    subgraph sys["Système actuel"]
      s1["search-worker<br/>✅ collecte, score, date"] --> s2["research-agent<br/>✅ mémo neutre"]
      s2 --> s3["bull / bear isolés<br/>+ réfutation bear→bull<br/>✅ avocat du diable"]
      s3 --> s4["synthèse dialectique<br/>✅ seul verdict"]
      s4 --> s5["thèse + hypothèses<br/>falsifiables ✅"]
      s5 --> s6["monitoring 1-6 ✅"]
    end
    MANQUE1["❌ personne ne challenge<br/>une <b>approximation</b> d'analyste"]
    MANQUE2["❌ aucune boucle de retour :<br/>les manques sont déclarés,<br/>la relance est <b>humaine</b><br/>(worker = endpoint HTTP)"]
    style MANQUE1 fill:#ffe0e0
    style MANQUE2 fill:#ffe0e0
```

**Écart A — le manager qui challenge une hypothèse n'existe pas.** Le curator contrôle la
*suffisance des données* (le champ est-il fondé à son plancher ?) ; le debate-agent challenge la
*conviction au maintien*. Personne ne challenge **l'approximation que fait l'analyste pour bâtir son
modèle** — c'est exactement le barreau 4, et il a échoué 4 fois. Il a peut-être échoué parce qu'il a
été conçu comme une **capacité automatique** au lieu d'un **rôle** qui accepte ou refuse une
hypothèse nommée.

**Écart B — pas de boucle comité → collecte.** `reconcile_gaps` déclare les manques ; rien ne les
transforme en mandat de recherche. Le worker ne se déclenche que par `POST /knowledge/worker`
(`api/knowledge_v2.py:72`). L'humain **est** la boucle.

**Écart C — le framework n'est pas un objet du système.** « Les 5 forces » n'existent que comme un
nom de champ + un sac de mots-clés en dur + un bout de prompt. Rien qui se versionne, s'adapte à un
secteur ou se remplace par « pipeline clinique » quand l'entreprise est une biotech.
