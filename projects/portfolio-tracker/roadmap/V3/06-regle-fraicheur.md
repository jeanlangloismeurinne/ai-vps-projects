---
id: regle-fraicheur
status: arbitrages 1-3 rendus le 2026-10-16 ; recommandation 4 proposée
created: 2026-10-16
project: portfolio-tracker
role: >
  Refonte de la règle de fraîcheur d'une réponse, ouverte par le jalon A4 (management et allocation du
  capital) à la demande de l'utilisateur : « réfléchir à la règle de fraîcheur — uniforme ou par
  question ; toutes les questions répondues à chaque trimestre ou des réponses passées qui restent
  valables ; un mode initiation et un mode suivi ». Les questions sont posées en termes de fonds.
---

# La fraîcheur d'une réponse — proposition

## 1. Ce qui a déclenché la question (mesuré le 2026-10-16)

- **RVMD, management** (réponses #1451-#1456) : ma_1, ma_2, ma_3 sont **nées périmées** le jour même
  où elles ont été écrites.
- **NVDA, management** : le plan de collecte a été **refusé** (garde #123) — 7 lignes demandaient le
  rapport annuel de janvier pour reconstituer cinq ans de rachats, d'acquisitions et de promesses ;
  après renvoi, le modèle les a redemandées. Rien n'a été écrit.

La cause est la même dans les deux cas. Aujourd'hui :

1. **Ce qui rouvre une question est propre à la question** (`rouverte_par`, arbitrage du 26/09) :
   les résultats rouvrent ma_1, un changement de dirigeant rouvre ma_4 — c'est juste.
2. **Une réponse prend la date de sa pièce LA PLUS ANCIENNE** (règle anti-blanchiment : on ne
   rajeunit pas une analyse en y ajoutant une pièce récente).
3. Elle est **périmée** si un fait qui la rouvre est postérieur à cette date (pour les résultats :
   postérieur à la clôture qu'ils publient, #102).

Conséquence : toute question rouverte par les résultats trimestriels doit être **entièrement
refondée sur des pièces du dernier trimestre**, chaque trimestre. Pour un solde de trésorerie, c'est
juste. Pour un **historique** (« les rachats des cinq dernières années ont-ils été faits au bon
prix ? », « les acquisitions passées ont-elles rapporté ? »), c'est faux : le 10-Q de juillet ne
reprend pas l'histoire de Mellanox, et la citer depuis le rapport annuel suffit à périmer la note.
Même défaut, déjà rencontré et contourné au cas par cas : la série pluriannuelle du modèle économique
(#123, résolue en la lisant dans le modèle des comptes), les descriptions juridiques (arbitrage du
13/10, non construit).

> **Analogie** : aujourd'hui, le dossier traite un **livre d'histoire** comme un **journal du jour** —
> dès qu'un nouveau journal paraît, tout ce qui cite un ancien journal est jeté, y compris le chapitre
> d'histoire qui, lui, n'a pas changé.

## 2. Ce que fait un vrai fonds

- **À l'initiation**, l'analyste lit tout : cinq à dix rapports annuels, le dernier proxy, les
  derniers trimestriels, l'historique des acquisitions. La note d'initiation cite des documents de
  tous âges ; elle est « à jour » parce qu'elle **intègre la dernière publication**, pas parce que
  toutes ses sources sont récentes.
- **Chaque trimestre** (revue trimestrielle, arbitrage du 22/09), l'analyste met à jour le **modèle
  des comptes**, ajoute **une ligne** à l'historique (rachats du trimestre, objectifs tenus ou non),
  et **relit chaque section rouverte** : soit il la **réécrit**, soit il écrit « **inchangé** — la
  publication du … ne modifie pas ce point parce que … ». Il ne réécrit pas la gouvernance après
  des résultats.
- **Une fois par an**, il relit ce qui se publie une fois par an : rapport annuel (description des
  brevets, des contrats de dette, des risques), proxy (rémunération, conseil, contrôle). C'est la
  **revue annuelle** (le mode 6 de la spec V2 en fait « la colonne vertébrale » du suivi long terme).
- **Entre deux**, un fait important (approbation, acquisition, départ du directeur général) donne une
  **note flash** qui rouvre seulement ce qu'il touche (déjà construit, #89/#90).
- À chaque section, il sait **quand il devra la revoir** : « prochaine revue : résultats du T3
  (novembre) », « prochain proxy (avril 2027) ». C'est son calendrier de suivi.

## 3. La proposition, en trois règles

### Règle 1 — La durée de vie se déclare par INGRÉDIENT, pas par question (ni uniforme)

Une même question mélange des matières qui vieillissent différemment : ma_1 demande la répartition
**actuelle** des usages de la trésorerie (vieillit chaque trimestre) **et** leur rendement sur
plusieurs années (un historique qui ne vieillit pas, il s'allonge). Le référentiel déclarerait donc,
pour chaque ingrédient, l'une de quatre durées de vie :

| Durée de vie | Ce que c'est | Remplacée par… | Exemples |
|---|---|---|---|
| **Chiffre courant** | un solde, un flux de la dernière période | les comptes suivants | trésorerie, rachats du dernier semestre, marge des douze derniers mois |
| **Historique** | des faits passés, datés, qui ne changent pas | rien — on y **ajoute** la période nouvelle | rachats des 5 derniers exercices, acquisitions passées et leur prix, objectifs annoncés en 2024 et tenus ou non |
| **Description annuelle** | ce qui ne se publie qu'une fois par an | le document annuel suivant, ou un fait qui la **touche** | brevets, clauses des contrats de dette, rémunération des dirigeants, composition du conseil, contrôle des droits de vote |
| **Jugement** | la conclusion de l'analyste | un fait qui rouvre la question (inchangé : `rouverte_par`) | « la barrière s'élargit », « la direction tient parole » |

Une pièce reste **valable tant qu'elle est dans sa durée de vie**. La règle anti-blanchiment est
gardée, mais elle porte sur la bonne chose : on ne peut pas citer un **chiffre courant** périmé (le
solde de trésorerie de décembre après les comptes de juin) ; on peut citer un **historique** de tout
âge. Une description annuelle cède devant le document annuel suivant (ou devant un fait qui la touche :
la nomination d'un administrateur périme la composition du conseil, pas la rémunération).

### Règle 2 — Une question rouverte n'exige pas une réécriture : elle exige une REVUE

Quand un fait rouvre une question, la réponse passe « **à revoir** » (et non « fausse »). L'analyste a
trois gestes, tous datés et tracés :

- **réécrire** (la publication change la réponse) ;
- **compléter** (ajouter la période nouvelle à l'historique, la conclusion tient) ;
- **confirmer** : « inchangé — la publication du 26/08 ne modifie pas ce point parce que … ».

Une réponse est **à jour** si elle a été **écrite ou confirmée après** le dernier fait qui la rouvre,
**et** si chacune de ses pièces est dans sa durée de vie. La confirmation est le prolongement de ce
qui existe déjà pour un fait postérieur aux comptes (« lire et annoter », #117) : elle doit **citer la
publication** qu'elle déclare avoir lue — une confirmation qui ne nomme pas la publication est refusée
(garde de forme, comme #103/#117 ; elle ne garantit pas que l'analyste a bien lu, cf. §5).

### Règle 3 — Deux modes : l'initiation construit, le suivi revoit selon un calendrier

```mermaid
flowchart TD
    I["INITIATION<br/>toutes les questions, sources de tous âges<br/>dans leur durée de vie"] --> N["Note d'initiation<br/>chaque réponse porte son<br/>PROCHAIN RENDEZ-VOUS"]
    N --> CAL["Calendrier de suivi<br/>= union des prochains rendez-vous"]
    CAL -->|"résultats trimestriels"| T["Revue trimestrielle<br/>questions rouvertes par les résultats :<br/>réécrire · compléter · confirmer"]
    CAL -->|"document annuel / proxy"| A["Revue annuelle<br/>descriptions annuelles relues"]
    EV["Fait important publié<br/>(note flash)"] --> F["Seulement les questions<br/>qu'il touche"]
    T --> CAL
    A --> CAL
    F --> CAL
```

- **Initiation** : toutes les questions doivent avoir une réponse ou un « non fondé » nommé. Les
  pièces de tous âges sont admises dans leur durée de vie ; ce qui est exigé, c'est d'avoir **intégré
  la dernière publication** de chaque question (la garde #123 devient : « une ligne de chiffre courant
  ne vise pas un rapport antérieur à la dernière clôture » — elle ne refuse plus un historique).
- **Suivi** : seules les questions rouvertes sont revues, par le geste le moins lourd qui suffit.
- **Le calendrier** : à l'écriture, chaque réponse reçoit son **prochain rendez-vous**, dérivé de ses
  ingrédients (chiffre courant → prochains résultats ; description annuelle → prochain proxy ou
  rapport annuel ; jugement → aucun rendez-vous fixe, seulement les faits qui le rouvrent). C'est ce
  qui alimente le calendrier de suivi « défini à chaque fois qu'on recherche des informations ».

## 4. Exemples concrets

**NVDA, ma_3 « rachats et émissions au bon prix ? »** (initiation en octobre 2026)
- Rachats des exercices 2022-2026 et prix moyens → **historique** → cités du rapport annuel de
  janvier : valables. Rachats du semestre clos le 26/07 → **chiffre courant** → cités du 10-Q.
- Prochain rendez-vous : résultats du T3 (fin novembre). Ce jour-là, la réponse passe « à revoir » ;
  l'analyste **complète** (rachats du T3 au prix du T3) ou **confirme**. Le rapport annuel de janvier
  2027 remplacera alors la ligne « exercice 2026 » de l'historique (un exercice clos n'est pas réécrit,
  il est publié une fois).

**RVMD, ma_6 « le conseil est-il un contre-pouvoir ? »**
- Composition du conseil, droits de vote → **description annuelle** (proxy 2026) ; jugement.
- Rouverte par un changement de gouvernance (8-K 5.02). Prochain rendez-vous : proxy 2027. Les
  résultats d'août ne la touchent pas — c'est déjà le cas aujourd'hui.

**RVMD, qf_7 « autonomie de trésorerie »** — inchangé : tout est **chiffre courant**, les résultats
trimestriels imposent une nouvelle mesure (ou une confirmation si rien n'a bougé, ce qui est rare).

## 5. Le coût d'erreur, nommé

- **Une confirmation de complaisance** (l'analyste — un modèle — écrit « inchangé » sans avoir lu) :
  elle ne se voit qu'à la relecture. Garde de forme : elle cite la publication et dit en une phrase ce
  qu'elle y a vérifié. Repli possible (principe n° 3, ordre 1 débrayable) : un interrupteur qui
  interdit la confirmation et impose la réécriture — c'est la règle d'aujourd'hui.
- **Une durée de vie mal déclarée** (un chiffre courant classé « historique ») laisserait un solde
  périmé passer pour à jour. Remède de données (le référentiel se relit ingrédient par ingrédient,
  comme `rouverte_par`) ; prudence par défaut : un ingrédient **sans** déclaration est « chiffre
  courant » (la règle d'aujourd'hui).
- **Un historique qu'on oublie de compléter** : la confirmation sans complément laisserait le
  trimestre manquer. Pour les ingrédients « historique », la revue trimestrielle exige « compléter »
  ou un motif (« aucun rachat ce trimestre »).

## 6. Questions à trancher

1. **La durée de vie déclarée par ingrédient** (quatre catégories) vous convient-elle, ou préférez-vous
   une règle plus simple (deux catégories : « courant » / « durable ») ?
2. **La confirmation motivée** (« inchangé, parce que … ») vaut-elle mise à jour, ou toute question
   rouverte doit-elle être réécrite ?
3. **Le rythme du suivi** : la spec V2 faisait de la **revue annuelle** la colonne vertébrale (les
   revues trimestrielles n'escaladent que sur franchissement de seuil) ; l'arbitrage du 22/09 dit
   « publication trimestrielle = revue complète de la thèse ». Lequel fait foi pour les questions de
   **jugement** non touchées par les chiffres du trimestre ?
4. **Le prochain rendez-vous par réponse** alimente-t-il le calendrier de suivi (modes trimestriel /
   annuel), ou le calendrier reste-t-il fixé par la thèse validée ?

## 7. Esquisse de mise en œuvre (après arbitrage — ordre données → règle → agents)

1. Données : `duree_de_vie` sur chaque ingrédient de `frameworks.yaml` (requis, sans défaut — une
   absence se lit « chiffre courant » seulement si on le décide explicitement) ; relecture des six
   frameworks ingrédient par ingrédient avec l'utilisateur.
2. Règle de lecture (`servir_answer`) : chaque pièce jugée dans sa durée de vie ; la date de la réponse
   devient « écrite ou confirmée le » ; recalculée à la lecture (#53), rien de stocké.
3. Garde du traducteur (#123) : ne vise plus que les ingrédients « chiffre courant ».
4. Geste de revue (confirmer / compléter / réécrire) : contrat + pont (la confirmation cite la
   publication) + interrupteur de repli.
5. Prochain rendez-vous dérivé, servi par réponse ; branchement au calendrier selon la réponse à Q4.
6. Acceptation : RVMD ma_1-ma_3 à jour sans réécriture ; NVDA plan management admis et à jour ;
   test négatif : un solde de trésorerie de décembre cité après les comptes de juin reste périmé.

## 8. Arbitrages rendus (2026-10-16)

1. **Quatre durées de vie** — retenu (chiffre courant · historique · description annuelle · jugement).
2. **La confirmation vaut mise à jour, mais pas pour tout ni à tout moment.** Un ingrédient dont on SAIT
   qu'une publication le prolonge (le chiffre d'affaires d'un émetteur à reporting trimestriel, à chaque
   trimestre) ne peut pas être « confirmé » : il doit être **complété**. D'où une précision du
   référentiel : chiffres courants et historiques portent leur **cadence** (trimestrielle ou annuelle,
   celle du document qui les publie), et le geste admis dépend du couple durée de vie × moment :

   | Durée de vie | À une publication de SA cadence | À une autre publication | Revue annuelle |
   |---|---|---|---|
   | Chiffre courant | **réécrire** (confirmer interdit) | non touché | réécrire |
   | Historique | **compléter** (zéro est une valeur : « aucun rachat ce trimestre ») | non touché | compléter |
   | Description annuelle | — | non touchée, sauf fait qui la touche | **relire** : confirmer (en citant le nouveau document) ou réécrire |
   | Jugement | revu si un ingrédient qui le fonde a bougé : réécrire ou confirmer | non touché | réécrire ou confirmer |

3. **Ce que le trimestre ne touche pas ne se rouvre qu'annuellement** (ou sur un fait qui le touche,
   `rouverte_par` inchangé pour les faits autres que les résultats). Les résultats trimestriels ne
   rouvrent donc plus une QUESTION entière : ils rouvrent ses ingrédients de cadence trimestrielle, et le
   jugement qui s'appuie dessus. La revue annuelle devient le rendez-vous de tout le reste.

## 9. Recommandation sur le calendrier (question 4)

**Ce que fait un fonds** : le calendrier de l'analyste n'est pas une liste de réponses à revoir, c'est
une liste d'**événements datés**, chacun avec ce qu'il va rouvrir : dates de résultats, assemblée et
proxy, et surtout les **catalyseurs** — jalons annoncés par l'entreprise (lecture d'essai « au
premier semestre 2027 », date de décision FDA, lancement) et rendez-vous du secteur propices aux
annonces (ASCO, ESMO, AACR pour RVMD ; GTC, Computex pour NVDA).

**Recommandation** : chaque réponse alimente le calendrier, mais **par l'intermédiaire d'événements**,
jamais une ligne par réponse. Trois sources :
1. **la cadence des publications** (dérivée des durées de vie) : résultats trimestriels, rapport annuel,
   proxy — l'essentiel du volume, comme vous le prévoyez ;
2. **les jalons annoncés par l'entreprise**, saisis **pendant la recherche** quand une pièce les
   annonce (date ou fenêtre, ce qui est promis, pièce citée, questions qu'il rouvrira) — c'est
   exactement « le calendrier défini à chaque fois qu'on recherche des informations ». Un jalon dont la
   date passe sans annonce est lui-même une information (ma_5, parole tenue ; à la manière d'un 8-K
   attendu qui ne vient pas) ;
3. **les rendez-vous du secteur**, déclarés par secteur (une donnée, comme les domaines d'émetteur),
   qui ouvrent une fenêtre de veille : ce n'est pas une revue, c'est une lecture attentive des
   communiqués de la période (et, à terme, le « veilleur » des événements extérieurs, #93).

La revue annuelle reste le filet : tout ce qui n'a pas été revu dans l'année l'est ce jour-là.

## 10. Essai de classement — management et allocation du capital (à valider)

| Ingrédient | Durée de vie | Cadence |
|---|---|---|
| ma_1 répartition des usages (plusieurs exercices) | historique | trimestrielle |
| ma_1 rendement des usages | historique | annuelle |
| ma_1 politique annoncée | description annuelle | — |
| ma_2 acquisitions réalisées | historique | annuelle (+ fait `perimetre`) |
| ma_2 résultat obtenu | historique | annuelle |
| ma_2 dépréciations | historique | trimestrielle |
| ma_3 opérations sur le capital | historique | trimestrielle |
| ma_3 valeur au moment de l'opération | historique | trimestrielle |
| ma_3 dilution par la rémunération | historique | trimestrielle |
| ma_4 critères de rémunération | description annuelle | — |
| ma_4 détention des dirigeants | description annuelle | — |
| ma_4 achats et cessions des dirigeants | historique | trimestrielle |
| ma_5 objectifs annoncés | historique | trimestrielle |
| ma_5 réalisation | historique | trimestrielle |
| ma_5 communication des échecs | jugement | — |
| ma_6 contrôle des droits de vote | description annuelle | — |
| ma_6 indépendance du conseil | description annuelle | — |
| ma_6 désaccords observés | historique | annuelle (+ fait `gouvernance`) |

Conséquence lisible : après les résultats de novembre, ma_1/ma_3/ma_5 de NVDA se **complètent** (rachats
du trimestre, objectifs du trimestre), ma_4/ma_6 ne bougent pas, ma_2 attend le rapport annuel sauf
acquisition annoncée. Aucune réponse ne naît plus périmée parce qu'elle cite l'histoire.

## 11. Conditions de l'arbitrage 3 (validées le 2026-10-16)

1. **Le communiqué de résultats est LU** (note flash), en plus de son classement « résultats » par la
   forme. Mesuré dans le code le 2026-10-16 : un 8-K 2.02 + 9.01 est entièrement décidé par sa forme,
   donc jamais lu — une surprise, une prévision révisée, un programme de rachat ou un nouveau découpage
   annoncés le jour des résultats ne rouvrent aujourd'hui rien de plus que les chiffres. Sans cette
   lecture, l'arbitrage 3 laisserait un jugement « à jour » jusqu'à un an après un fait qui le touche.
   **Prérequis : l'arbitrage 3 n'entre pas en vigueur avant elle.**
2. **Position détenue** : revue trimestrielle légère de chaque jugement (confirmer ou rouvrir, une phrase
   motivée) — prolonge Q5 du 26/09 ; reportée au chantier du suivi (hors note d'initiation).

## 12. Classement des ingrédients (proposé le 2026-10-16, à corriger par exception)

Légende : **CC** chiffre courant · **H** historique · **DA** description annuelle · **J** jugement ;
cadence **T** trimestrielle / **A** annuelle. « +ext » : prolongé aussi par les événements extérieurs
(concurrents, régulation — veilleur à construire). Deux mécanismes déjà arbitrés, qui ne sont pas des
catégories : **repris** (hérite de la réponse reprise, #99) et **lecture** (recalculé au dernier cours
coté daté, option 1 du 28/09). La cadence est celle du document qui publie usuellement l'ingrédient ;
un émetteur qui le publie plus souvent pourra la resserrer (exception par émetteur, plus tard).

**Qualité financière** — qf_1 : résultat d'exploitation après impôt CC-T · capital employé CC-T · taux
d'impôt CC-T · coût du capital J (A5) · historique cinq exercices H-A. qf_2 (« de l'exercice ») :
résultat net, trésorerie d'exploitation, variation du BFR, charges sans décaissement CC-A. qf_3 :
croissance par exercice H-A · investissement de maintien J · de croissance J · variation du capital
employé H-A. qf_4 : endettement, échéancier, lignes non tirées, couverture des intérêts CC-T. qf_8 :
clauses DA (+ fait `financement`) · marge avant déclenchement CC-T · remboursement anticipé et défaut DA.
qf_5 : série longue H-A · marge × rotation H-A · comparaison sectorielle H-A. qf_6 : provisions CC-T ·
politique de capitalisation DA · écart publié/ajusté CC-T · éléments non récurrents H-T. qf_7 : tout
CC-T (trésorerie, consommation, charges fixes, prévision de la direction, échéances, lignes).

**Défendabilité** — mo_1 : mécanisme J · coût de réplication J · tentatives de contournement H-A +ext.
mo_2 : marges relatives aux pairs, parts de marché, rétention, coût d'acquisition H-A. mo_3 : signal
nommé J · série du signal H-T · mouvements concurrents H-A +ext. mo_4 : classe de référence J · durée
observée J · échéances contractuelles ou légales DA. mo_5 : vecteur J · signal précurseur J · état du
signal CC-T. mo_6 : prix pratiqués H-T · réaction des volumes H-T · prime de prix H-A.

**Modèle économique** — me_1 : client payeur, besoin servi, alternatives DA · motif de choix J. me_2 :
répartition du CA CC-T · part engagée ou répétée CC-A · montant engagé non reconnu CC-T. me_3 : prix
par unité CC-A · coûts par unité CC-A · marge brute H-T (socle). me_4 : moteurs J · part maîtrisée J ·
sensibilité passée H-A. me_5 : marché adressable DA (+ faits réglementaires) · part déjà prise CC-A ·
extensions engagées DA. me_6 : premiers clients CC-T · premier produit CC-T · fournisseurs sans
substitut DA · exposition par pays CC-A.

**Secteur et concurrence** — se_1 : rentabilité des acteurs H-A · pouvoir des clients, des
fournisseurs, intermédiaires DA. se_2 : acteurs et parts CC-A · évolution des parts H-A · entrants
H-A +ext. se_3 : pairs directs J · indicateurs comparés CC-A · évolution de l'écart H-A. se_4 :
historique de la demande H-A · moteur du cycle J · position actuelle CC-T. se_5 : substituts H-A +ext
· évolutions réglementaires H-A +ext · nouveaux modèles J. se_6 : mouvements récents H-A +ext ·
conséquence pour l'entreprise J · réaction de l'entreprise H-T.

**Valorisation** — va_1 : résultat normalisé, taux, passage par action **repris** · nombre d'actions
dilué **lecture** · valeur des actifs J. va_2 : hypothèses décisives J · coût de la croissance, durée et
plafond, dilution future **repris**. va_3 : classe, distribution, position J. va_4 : cours coté,
croissance implicite **lecture** · comparaison aux scénarios J. va_5 : multiple pertinent J ·
comparaison pairs et historique **lecture** · explication de l'écart J. va_6 : prix et fourchette
**lecture** · hypothèse portante J.

**Management** — §10.
