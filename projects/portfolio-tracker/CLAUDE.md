# CLAUDE.md — portfolio-tracker

> **Allégé le 2026-10-16** (338 Ko → ce fichier) : il est chargé à CHAQUE conversation. Rien n'a été
> supprimé — le texte intégral vit dans des fichiers pointés :
>
> | Besoin | Où |
> |---|---|
> | Comment décider et poser un arbitrage — **à lire à chaque session, en premier** | `roadmap/V3/PRINCIPES-FONDATEURS.md` |
> | Où on en est, prochain pas | `roadmap/V3/00-REPRISE.md` |
> | Texte INTÉGRAL d'une convention (#1 → #134) | **`CONVENTIONS.md`** — `grep -n "#NN" CONVENTIONS.md` |
> | V0/V1, schéma, liste des migrations, endpoints, scheduling, DataService, env | **`REFERENCE.md`** |
> | Ce que la V3 DOIT faire | `roadmap/V3/03-spec-frameworks.md` (+ `doctrine-trois-axes.md`) |
> | Ce qui existe RÉELLEMENT, module par module | le `ARCHITECTURE.md` du module (`backend/app/**/ARCHITECTURE.md`) |
> | La PREUVE qu'une brique existe | `backend/checks/` — on l'exécute, on ne la lit pas |
>
> Une brique V3 n'est « faite » que si un `check_*.py` la garde **et** qu'un `negatif_*.sh` prouve que ce
> check vire au rouge quand on la casse. ⚠️ `backend/app/agents/v2/` contient surtout de la **V3** malgré
> son nom (les 5 fichiers de la boucle V2 sont nommés dans son `ARCHITECTURE.md`).
> **Avant de toucher un module, lire en entier les conventions qui le concernent dans `CONVENTIONS.md`.**

## Contexte

Suivi d'investissement long terme. URL `portfolio.jlmvpscode.duckdns.org` — backend `portfolio-backend`
(8050, routé `/api` avec stripprefix), frontend `portfolio-frontend` (8051). Python 3.12 / FastAPI /
asyncpg · PostgreSQL 16 `shared-postgres` base `db_portfolio` · Redis 7 · Next.js 14. Modèle des agents V3 :
DeepSeek via DeepInfra (`DEEPINFRA_API_KEY`) ; embeddings `BAAI/bge-m3` 1024d ; web Exa (+ Serper).

## Pièges qui coûtent cher (le détail est dans `CONVENTIONS.md`)

- **asyncpg** : paramètres `$1, $2`… ; JSONB auto-décodé — jamais `json.dumps()` avant INSERT (#1).
- **Migrations jamais auto-appliquées** : `docker cp f.sql shared-postgres:/tmp/ && docker exec shared-postgres
  psql -U admin -d db_portfolio -f /tmp/f.sql` (un heredoc via `docker exec` échoue en silence) (#17).
  Prochaine migration : voir `00-REPRISE.md`.
- **`get_db_session()` n'ouvre aucune transaction** : `async with conn.transaction():` explicite (#35).
- **Déploiement** : `infrastructure/compose-deploy.sh portfolio-backend -m … -f …` (commit + push + rebuild +
  sonde) ; vérifier ensuite DANS le conteneur (`docker exec portfolio-backend grep …`).
- **Outils qui écrivent/dépensent** (`tools/executer_chaine.sh`, mesureurs) : instance neuve de l'image,
  jamais dans `portfolio-backend` ; vérifier `ps aux`/`docker ps` avant toute relance (deux passages
  concurrents ont déjà écrit en même temps).
- **Suite** : `bash backend/checks/run_all.sh` (rejouer EN ENTIER après tout changement de contrat partagé) ;
  test négatif : `bash backend/checks/negatif_<module>.sh`.
- **Règle #19/#39** : tout changement de contrat = prompt en base + exemple JSON + frontend + import.

## Système de pilotage

Déclencheur : « reprends le projet portfolio-tracker à partir du fichier de reprise » → lire
`roadmap/V3/PRINCIPES-FONDATEURS.md`, puis `roadmap/V3/00-REPRISE.md`, qui pointe le reste. Tout le pilotage
vit dans `roadmap/V3/` ; l'historique V0/V1/V2 sous `roadmap/archive/`. Protocole : `CONTROL_SYSTEM.md`
(racine du repo).

## Index des conventions (une ligne chacune — texte intégral dans `CONVENTIONS.md`)

- #1 asyncpg
- #2 Labels Traefik
- #3 `env_file` requis
- #4 `NEXT_PUBLIC_*` est inliné AU BUILD
- #5 Commit + push AVANT
- #6 Traefik + multi-réseaux
- #7 yfinance `.calendar`
- #8 DataService
- #9 Vérification sync avant appel Dust
- #10 PATCH agent ne change pas synced
- #11 `tickers.id` ≠ symbole yfinance
- #12 Handoff opportunity→thesis
- #13 Validation thèse
- #14 Tables V0 renommées
- #15 Permissions DB
- #16 Next.js routes imbriquées
- #17 Migrations non auto-appliquées
- #18 Architecture PE/VC (sociétés non cotées)
- #19 Cohérence format JSON — règle des 3 points de synchronisation
- #20 `pending_manual` dans monitoring_sessions
- #21 `hypotheses_reviewed[]` vs `hypothesis_reviews[]`
- #22 Recherche knowledge
- #23 pgvector et `atttypmod`
- #24 search-worker — le modèle ne qualifie jamais sa propre source
- #25 Un échec de recherche n'est jamais un résultat vide
- #26 `fetch_url` a deux chemins, et le domaine décide de ce qui vaut la peine d'être lu
- #27 On ne tronque pas un document, on y cherche
- #28 La provenance est vérifiée, pas déclarée
- #29 La couverture se LIT dans un index, elle ne se demande pas au modèle
- #30 Le concept XBRL se choisit par FRAÎCHEUR, jamais par convention
- #31 Ce qui décrit UN émetteur ne vit jamais dans une constante globale
- #32 Un plancher qu'aucun domaine ne peut atteindre est un champ infondable déguisé en lacune
- #33 Le site d'un émetteur se reconnaît PAR ÉMETTEUR, et sur deux niveaux
- #34 Les jugements sont disjoints, les faits du monde sont PARTAGÉS
- #35 `get_db_session()` n'ouvre AUCUNE transaction
- #36 Un contrat de décision ne vaut que par ce que le corps HTTP n'expose PAS
- #37 Un contrat valide un objet, JAMAIS la cohérence entre deux
- #38 Le rattrapage d'une échéance dépend de ce qu'elle commente, pas d'une règle uniforme
- #39 L'EXEMPLE JSON d'un prompt est une pièce du contrat, et la DB est le 3ᵉ point de synchro
- #40 Une pré-condition d'ÉTAT se refuse avant l'appel, pas dans le pont
- #41 Un abandon est facturé comme un succès — il doit être comptabilisé comme tel
- #42 Un poste de bilan se date à un INSTANT, un flux à un EXERCICE — et un ratio se date par les postes qui le composent
- #43 L'identité d'un fait est ce qu'il MESURE, et cette règle vit à un seul endroit
- #44 Un ratio à dénominateur négatif n'est pas un niveau, c'est une perte — et « non calculable » n'est pas « absent »
- #45 Un libellé qualifie la maille RÉELLEMENT mesurée, et un montant choisit son unité
- #46 Une règle de FORMAT recopiée dans trois producteurs n'est corrigée dans aucun
- #47 Un zéro est une VALEUR mesurée, et `if x:` ne sait pas le distinguer d'une absence
- #48 La COLONNE `source_date` est un porteur de la date au même titre que le texte — et c'est le seul sur lequel trient les machines
- #49 La péremption est une SECONDE horloge, et elle produit un rapport — jamais un `superseded_by`
- #50 Un champ a TROIS propriétés indépendantes, et le standing est une propriété du COUPLE (source × nature) — jamais de la source seule
- #51 La nature d'une ENTRY et la nature dominante d'un CHAMP sont deux vocabulaires, et le second ne dérive jamais le premier
- #52 Une source est admise pour un COUPLE (source × nature), et l'ordre `nature` PUIS `registre` est ce qui rend cette phrase vraie
- #53 L'actualité est une propriété de la RELATION entre un fait et l'ancre du moment — donc elle se calcule à la LECTURE, et la stocker serait littérale…
- #54 La complétude a TROIS états, parce qu'elle a deux causes d'échec et donc deux remèdes — et un état calculé que personne ne lit n'est pas un état
- #55 Une règle juste dans le PRODUCTEUR est aveugle pour un LECTEUR tant que son discriminant n'est pas dans la ligne
- #56 Un garde-fou écrit en `grep` de token se trompe DANS LES DEUX SENS, et le sens « faux vert » est le plus coûteux
- #57 Re-vocabulariser une rigidité ne la retire pas : elle se déplace avec son nouveau nom
- #58 Ce qu'on collecte se dérive de ce qu'on demande, jamais l'inverse — et l'ordre du COÛT n'est pas l'ordre de l'AUTORITÉ
- #59 La valeur inégale d'une même source selon l'émetteur est de l'ACTUALITÉ, pas de la fiabilité
- #60 Un exécuteur AVEUGLE route sur du texte libre, et une métrique qui CONTIENT le nom d'un poste peut en être une dérivée
- #61 Un producteur qui collecte « tout » avant la question est un socle data-first ; le rendre plan-dérivé en fait un CATALOGUE de recettes, et ça TUE l…
- #62 Un levier du modèle sur l'exigence est une question posée par le MODÈLE, pas par le framework
- #63 Une exigence que le modèle ne peut NI VOIR NI SATISFAIRE se refuse AVANT la dépense — sinon le pont impute à l'agent un corpus qui ne pouvait pas f…
- #64 Une dispense/réponse non clefée par VERSION survit à la question qu'elle répondait
- #65 Le harnais de test négatif est un DÉTENTEUR UNIQUE, et l'archi est gardée comme le code
- #66 La méthode de test se choisit par DÉCIDABILITÉ, pas par coût — et le décideur reste OUVERT
- #67 L'APPARIEMENT question ↔ donnée est une propriété du COUPLE (question × émetteur), il se calcule PAR TICKER contre les champs réellement déposés, e…
- #68 Une garde de code vérifie la STRUCTURE et la RELATION, jamais le SENS — et quand le sens échappe, c'est la FORME de la réponse qu'on change, pas la…
- #69 Le RENDU d'un inventaire est un PRODUCTEUR : ce qu'il omet se lit comme une propriété de l'émetteur
- #70 Une garde nourrie de SA PROPRE VALEUR ne se voit pas — et son signe est un log qui ne peut jamais être vrai
- #71 Un décideur sans producteur ne décide jamais — et sa garde reste verte parce qu'aucune donnée ne l'atteint
- #72 Une formule d'appariement s'EXÉCUTE sur le dépôt DÉJÀ LU — et le chiffre à suivre est la ligne COLLECTÉE, jamais la ligne ROUTÉE
- #73 Un BLOCAGE réseau est un QUATRIÈME état muet, invisible aux checks ET à l'acceptation ROLLBACK : seule une exécution réelle NON surveillée le révèl…
- #74 Le TEMPOREL d'une formule d'appariement porte sur le NOM (`Concept[-1]`), jamais sur un concept neuf — c'est #57 appliqué à la formule
- #75 Une bévue sur UN ingrédient ne fait plus tomber la carte ENTIÈRE — elle se REPLIE, ingrédient par ingrédient (V3, lot 3 maillon 4bis, geste (b) — 2…
- #76 Un contrôle qui re-vérifie ce que le contrat GARANTIT n'a pas de `ko` atteignable — le manager re-vérifie ce que le contrat ne PEUT PAS juger
- #77 Un avis DÉTERMINISTE ne se stocke pas, il se RECALCULE — on ne persiste que son EFFET durable, le mandat, et son cycle de vie
- #78 Tous les nombres justes, le fait FAUX — un `repondu` peut porter un chiffre CALCULÉ qu'aucune entry citée ne contient, et les quatre contrôles l'ac…
- #79 Une pièce porte DEUX dates nommées, et `source_date` cesse d'être reçue — quand deux dates sont structurellement indiscernables, on change la FORME…
- #81 le cours coté et sa date : une séance vide n'est pas une séance
- #82 `qualite_info` : une mesure a plusieurs AXES, et un axe ne se fond jamais dans un scalaire
- #83 « peut-on décider ? » : un manque se NOMME avec sa cause, et la cause appartient à celui qui a échoué
- #84 le procès-verbal du comité : une acceptation se SIGNE, se MOTIVE, et TOMBE d'elle-même
- #85 la note de comité reprend ce que le comité a RETENU, et le dit
- #86 un sigle n'est pas une identité : tout agent qui cherche pour un émetteur reçoit sa raison sociale et son CIK
- #87 une pièce d'une autre société sort du dossier, et la trace reste
- #88 un jugement fondé sur des faits vérifiés est une réponse directe
- #89 créer un framework, c'est décider ce qui ROUVRE chacune de ses questions
- #90 la note flash : on LIT le communiqué que la forme ne qualifie pas, et on cite ce qu'on a lu
- #91 l'analyste lit ses communiqués à DEUX moments : chaque matin, et avant de rouvrir un dossier
- #92 ajouter un framework : le référentiel, sa table dans la spec, et aucune constante de décompte
- #93 « Secteur et concurrence », et l'origine d'un événement
- #94 « Management et allocation du capital » ; la gouvernance rouvre enfin quelque chose
- #95 « Valorisation » : les questions en données, le calcul hors du modèle
- #96 l'atelier de valorisation : l'agent écrit la mécanique, le comité signe le tableau, le bac calcule
- #97 le modèle d'une entreprise : trois origines pour un chiffre, et une fourchette dont la forme dépend de l'incertitude
- #98 la signature du modèle de valorisation : le comité signe ce qu'il voit, et la signée reste affichée
- #99 un seul chiffre par dossier : la valorisation reprend, porte le sien si c'est sans objet, sinon attend
- #100 l'encadré de chiffres clés : la valorisation relit des chiffres déclarés, jamais la prose
- #101 l'analyste relève, le code calcule ; un chiffre manquant ne fait pas tomber la question ; une réponse refusée est renvoyée UNE fois
- #102 un communiqué de résultats ne périme pas les comptes qu'il publie
- #103 un fait postérieur aux comptes, LU et chiffré par l'analyste, ne périme plus sa réponse
- #104 une seule définition de la dette nette, et une pièce d'héritage cède devant une pièce datée
- #105 l'autonomie se calcule sur la consommation la plus prudente
- #106 l'analyste lit les dépôts postérieurs ; le dossier range tous les documents d'un point
- #107 la recette qui lit moins que la carte s'efface ; les annexes d'une réponse partent avec elle
- #108 chaque framework ne lit que ses sujets
- #109 un solde déposé au 10-K reste un instant ; un renvoi raté n'emporte pas le passage
- #110 le texte d'un fait apparié dit ce que le système tamponne
- #111 chaque affirmation se cite par sa source la plus récente
- #112 les douze mois glissants : une PÉRIODE de la référence, lue au dépôt par les durées
- #113 la demande précise la période ; l'analyste ne voit que ce qu'il peut citer
- #114 distinguer les faits et le jugement : qf_4 scindée (tableau de la dette / revue des clauses)
- #115 le socle des comptes : un modèle des comptes commun, les questions sont la couche de jugement
- #116 les ratios maison : définis une fois, lus dans le socle par le code
- #117 lire et annoter : un texte postérieur aux comptes ne périme pas une mesure, il s'annote
- #118 une mesure rouverte chaque trimestre se lit sur douze mois ; un terme négatif rend un calcul « non significatif »
- #119 `PERIODES` n'a pas de valeur « cumul d'une période intermédiaire », et une collecte deux fois
- #120 le traducteur reçoit l'horloge : la date du jour et la clôture des derniers comptes publiés
- #121 l'exemple de sortie d'une consigne est un point de contrat : il se valide contre le contrat
- #122 l'identité de l'émetteur est une donnée de référence : jamais déduite d'une pièce de son dossier
- #123 le plan de collecte vise l'horloge de CHAQUE question, pas seulement la dernière clôture
- #124 un budget de temps se calibre sur une mesure, et le temps d'une recherche est dans l'écriture du modèle
- #125 le rappel : un raffinement d'ordre 1, débrayable (catalogue 1.4.0, principe fondateur n° 3)
- #126 une fiche du collecteur ne dit que ce que son document écrit : extraits littéraux vérifiés, lecture à part
- #127 le standard de collecte : une note se date par le standard sous lequel elle a été instruite
- #128 une réponse hors contrat ne fait plus tomber le lot : lecture tolérante du premier tour
- #129 la fraîcheur se juge dans la DURÉE DE VIE de ce que chaque pièce fonde ; le communiqué de résultats se LIT
- #130 une révision de prévision sans cause dite rouvre les causes PROBABLES du chiffre révisé
- #131 les faits des dirigeants et le jugement sur leur rémunération se séparent ; un dérapage d'exécution ne rouvre pas la concurrence
- #132 un tableau converti en texte garde ses colonnes : une ligne de tableau doit pouvoir se citer
- #133 la source d'origine d'abord : le site de l'émetteur, à défaut ailleurs
- #134 dans un long document, on cherche par les mots du document : `chercher`
