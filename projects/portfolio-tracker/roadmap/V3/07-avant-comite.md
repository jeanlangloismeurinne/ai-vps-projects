---
id: inventaire-avant-comite
status: valide-ordonne-2026-10-16
created: 2026-10-16
project: portfolio-tracker
role: >
  Inventaire de TOUT ce qu'il reste à traiter avant d'avoir un système qui produit une note
  d'initiation présentable au comité d'investissement (six chapitres + fourchette de valeur) sur
  3-4 titres très différents. Demandé par l'utilisateur le 2026-10-16 : « regardons d'abord tous les
  sujets pour faire la liste de ce qu'il faut traiter ». À VALIDER et ORDONNER avec lui ; l'ordre
  retenu deviendra la checklist de la roadmap (05, jalon A).
---

# Avant le comité — inventaire

> **Ordre validé le 2026-10-16** : (1) la matière — 1.1, 1.2, 1.4, 1.6 ; (2) les arbitrages groupés en une
> séance — 9, 10, 11, 12, 15, 17, 20, 21 ; (3) la tenue du dossier — 14, 16, 17, 13 ; (4) la valorisation —
> 18 ; (5) le test — 22, 19, 23.

> Chaque ligne : ce qui ne va pas **en termes de fonds**, un cas réel, et la nature du travail —
> **[A]** arbitrage de l'utilisateur à poser · **[C]** correctif à construire · **[D]** donnée à
> écrire (référentiel) · **[P]** passage à refaire (dépense modèle). Ordre proposé à discuter.

## 1. La matière : ce que la collecte ramène (touche tous les chapitres)

1. **Copies au lieu de l'original** [C] — la prévision de NVIDIA a été prise sur un site brésilien qui
   la reprend (rang faible, rejetée) alors qu'elle est sur le site et dans les dépôts de NVIDIA.
   ✅ **Fait le 2026-10-16 (#133, `9c7152b`)** : le site de l'émetteur d'abord, puis le web ouvert ; rejeu
   NVDA ma_5 → communiqué `investor.nvidia.com` + commentaire CFO `sec.gov`. Reste (non bloquant) : la
   transcription officielle est hébergée chez le prestataire IR (`s201.q4cdn.com/141608511/…`), domaine
   partagé entre émetteurs donc non enregistrable tel quel — le collecteur a lu une copie (`earningscalls.dev`).
2. ~~Sélection des passages selon la langue~~ ✅ **Fait le 2026-10-16 (#134)** — la langue n'était pas la
   cause (traduction anglaise fidèle : même échec) ; c'est un mandat long qui dilue la question et une ligne
   de tableau sans sens propre. Remède : le collecteur dit ce qu'il cherche DANS le document (`chercher`,
   intitulé de section) ; rejeu NVDA ma_4 → la fiche cite le tableau de détention.
3. **Tableaux** ✅ #132 (cellules séparées, une ligne de tableau se cite).
4. ~~Instabilité du collecteur~~ ✅ **Fait le 2026-10-16 (#135)** — mesuré : délais réglés par #124 ;
   hors contrat = un extrait trop court faisait tomber toute la réponse (lecture fiche par fiche) ; « rien
   trouvé » instable = un passage sans recherche web (relancé une fois). Reste un « rien » stable légitime.
5. **Prix au moment des rachats** [A/C] — NVIDIA ne publie plus en données structurées les actions
   rachetées ; le cours historique n'est pris qu'au web (rangs faibles). Un fonds prend l'historique de
   cours dans sa base de marché : faut-il en faire une source du système ? Cas : NVDA ma_3.
6. **Le chiffre sans sa pièce** (D-me6) [A/C] — une réponse cite un chiffre juste tiré d'une pièce
   qu'elle ne cite pas (NVDA me_6, RVMD se_4). Contrôle avant comité : tout chiffre renvoie à une pièce.
7. **Événements extérieurs** [C] — les annonces de concurrents ne rouvrent rien faute de veilleur
   (RVMD : revue FDA d'un concurrent le 07/10, non vue).
8. **Pièces d'héritage** [P] — ~130 pièces sans datation et les réponses « standard antérieur » :
   soldées par la reconstruction (premier passage d'A11), pas avant.

## 2. Le raisonnement : ce que les réponses affirment

9. **D-me5 — marché adressable** [A] — NVDA me_5 chiffre un marché d'extension (processeurs centraux)
   au lieu du marché actuel (accélérateurs), et une « part prise » sur des revenus futurs. Prérequis de
   la valorisation (va_2 reprendrait ce plafond).
10. **Coût du capital** [A] — qui le fixe ? Un fonds le fixe en interne, commun au portefeuille ; le
    système n'a que des estimations de tiers. Prérequis de la valorisation.
11. **Réponses à relire par le comité** [A] — NVDA qf_6 (part des retraitements en solde net 2,6 % vs
    ≈ 14 % poste par poste), qf_1 (résultat « normalisé » = résultat déposé), RVMD mo_4 (« 19 ans » de
    barrière = dernière échéance de brevet, non prudent), qf_8 RVMD (classement vs son propre texte),
    MSFT note flash (nouveaux segments lus comme routine).
12. **Acquisitions passées** [A/D] — « ce qu'elles ont rapporté » n'est publié par personne ; la question
    ma_2 est-elle instruisable telle quelle, ou se juge-t-elle sur l'évolution des segments acquis ?

## 3. La tenue du dossier : quand une réponse est-elle en vigueur

13. **Ré-analyse qui dégrade une réponse** [A] — NVDA ma_1 : fondée (périmée) → « sans fondement » au
    passage suivant ; un refus d'agent ne doit pas devenir une demande de recherche. ⚠️ La règle proposée
    (« la nouvelle n'entre en vigueur que si au moins aussi fondée ») a été **écartée par l'utilisateur
    le 2026-10-16** : sujet laissé en dette, à repenser. Prérequis du test de reproductibilité.
14. **Demandes de recherche jamais closes** [C] — mandats 983-986, 2612/2613, 2975-2977 restent
    ouverts quand la question a trouvé sa réponse.
15. **Une pièce ancienne périme une réponse à jour** [A] — NVDA ma_1 citait le communiqué de rachat du
    18/05 en plus de celui du 28/09 ; le plus ancien la rend périmée (émission obligataire du 15/06).
16. **Calendrier et revue trimestrielle** [C] — non construits (publications, jalons annoncés,
    rendez-vous du secteur ; revue légère des jugements d'une position détenue) ; la position du comité
    tombe encore sur des résultats sans surprise.
17. **Re-run vs acceptation du comité** [A] — une chaîne relancée refait l'analyse et fait tomber une
    acceptation du comité, voire rouvre une recherche qu'il avait arrêtée.

## 4. La valorisation (aucune réponse aujourd'hui)

18. **L'agent qui écrit le modèle de l'entreprise** [C] — méthodologie, segments, tableau d'hypothèses,
    mécanique ; l'ordre d'instruction (après les frameworks repris) ; va_4-6 au cours du jour ; règle de
    Greenwald ; va_6 rouverte avec va_1/va_2. Socle livré (#96-#100) ; prérequis 9 et 10.

## 5. Le périmètre du test

19. **MSFT** [P] — aucune réponse en vigueur, cartes à refaire.
20. **4ᵉ titre « financière »** [A/C] — banque ou assureur : le modèle des comptes n'est pas éprouvé sur
    un bilan financier ; un émetteur étranger (20-F) entre-t-il dans le jalon ?
21. **RVMD reclassée « commerciale »** [A] — proposée au comité après l'approbation : sans elle, des
    questions restent « sans objet » sur un titre qui vend.
22. **L'outil du test** [C] — table de mesure par titre × chapitre, et comparaison de deux passages
    identiques (mêmes statuts, mêmes chiffres de l'encadré, écarts nommés).
23. **Le test lui-même** [P] — note d'initiation complète sur 3-4 titres, deux passages ; le premier est
    la reconstruction au standard figé.

## 6. Hors du chemin du comité (connu, non bloquant)

- Estimations d'analystes (FMP refuse la clé, 403) ; coût web non instrumenté ; lignes web en série
  (~1 h par chapitre) ; résidus #115/#116 du modèle des comptes (MSFT : amortissements, Activision ;
  loyers à un an) ; pistes DeepInfra « modèles de décision » pour remplacer le vote de trois lectures.
