---
id: seance-arbitrages-groupes
status: tranche-2026-10-17
created: 2026-10-17
project: portfolio-tracker
role: >
  Dossier de la séance d'arbitrages groupés (étape 2 de l'ordre validé dans `07-avant-comite.md` :
  points 9, 10, 11, 12, 15, 17, 20, 21). Une question métier par point, un cas réel relevé en base le
  2026-10-17, ce que ferait un fonds, une recommandation. Les réponses de l'utilisateur sont consignées
  dans la section « Décisions » en bas, puis reportées dans 00-REPRISE.md / CONVENTIONS.md.
---

# Séance d'arbitrages — 2026-10-17

> Cas relevés en base le 2026-10-17 (réponses en vigueur). Deux écarts avec l'inventaire du 16/10 :
> RVMD mo_4 a été refaite (#1420 : 5 ans d'exclusivité réglementaire, prudent — le « 19 ans » est
> réglé) ; NVDA qf_6 #1289 conclut « part faible » sans plus aucun chiffre. Aucune décision du comité
> n'a jamais été enregistrée : le point 17 fixe une règle avant son premier usage.

## 9. Le marché adressable — NVDA me_5

**Cas.** La réponse en vigueur (#1370) dit : marché adressable 200 Md$, part déjà prise 10 %. Mais les
200 Md$ sont le marché des processeurs centraux (Vera CPU), une **extension annoncée**, pas le marché des
accélérateurs qui fait aujourd'hui 92 % du chiffre d'affaires ; et les 10 % rapportent des revenus
**futurs** (~20 Md$ de « visibilité ») à ce marché. La valorisation reprendrait ce chiffre comme plafond
de croissance.

**Ce que ferait un fonds.** L'analyste chiffre le marché du métier actuel ; une extension annoncée est
une option, traitée en scénario à part ; une part de marché se calcule sur du chiffre d'affaires réalisé.

**Question.** Le dossier doit-il séparer « marché du métier actuel » (avec une part calculée sur les
ventes constatées) et « marchés d'extension » (listés comme options, sans part de marché) ?

- (a) **Oui, séparer** — la valorisation ne prend pour plafond que le marché actuel ; les extensions
  nourrissent un scénario haut. *Recommandé.*
- (b) Garder une seule réponse, mais signaler au comité quand elle porte sur une extension.

## 10. Le coût du capital — qui le fixe ?

**Cas.** NVDA qf_1 (#1209) conclut « crée de la valeur » avec un rendement du capital de 112 % en
moyenne, mais le coût du capital est vide : le dossier n'a que des estimations de tiers (sites
d'agrégation, rang faible). Sur NVDA l'écart est tel que la conclusion tient ; sur MSFT ou une banque,
elle dépendra du chiffre. La valorisation (actualisation) ne peut pas partir sans lui.

**Ce que ferait un fonds.** Le taux exigé est une **décision maison**, fixée par le directeur des
investissements ou le comité, commune au portefeuille, révisée rarement (une à deux fois l'an). Deux
pratiques courantes : un taux unique par profil de risque (ex. « 9 % pour une entreprise établie, 12 %
pour une biotech ») ; ou une formule maison (taux sans risque du jour + prime de risque fixée par le
comité, modulée par titre). Les estimations de tiers servent au plus de point de comparaison.

**Question.** Comment le fonds fixe-t-il son taux exigé ?

- (a) **Un taux par profil** (entreprise établie / sans revenus / financière), fixé et daté par le
  comité, revu une fois l'an. *Recommandé : simple, stable, cohérent avec un fonds concentré long terme.*
- (b) Formule maison : taux sans risque du jour + prime fixée par le comité × risque propre du titre.
- (c) Estimation de tiers, citée comme toute pièce.

Si (a) : quels taux ? (à défaut, proposition à valider : 9 % établie, 12 % sans revenus, 10 % financière).

## 11. Les réponses à relire — qui les corrige ?

**Cas (état du 2026-10-17).**
- NVDA qf_6 (#1289) : conclut « part des retraitements faible » sans aucun chiffre (tous non établis).
- NVDA qf_1 (#1209) : le « résultat normalisé » est le résultat d'exploitation déposé, non retraité.
- NVDA me_6 (#1597) : parts des clients 22/14/13/11/10 % justes, mais citées sur un document qui parle
  d'autre chose.
- RVMD qf_8 (#1379) : « aucune contrainte » des prêteurs — à vérifier contre son propre texte.
- MSFT note flash : nouveaux segments lus comme une publication de routine.
- ~~RVMD mo_4 « 19 ans »~~ : réglé par la réponse #1420 (5 ans).

**Ce que ferait un fonds.** Le directeur de la recherche annote la note et la **renvoie à l'analyste** ;
le comité ne réécrit pas la note lui-même, et l'analyste reprend sa copie avec les remarques.

**Question.** Quand le comité relève un défaut dans une réponse, que se passe-t-il ?

- (a) **Il annote ; l'annotation est remise à l'analyste au prochain passage** (la reconstruction du
  test) ; d'ici là la réponse reste affichée avec la remarque. *Recommandé : pas de dépense hors test.*
- (b) Il annote et la question est refaite tout de suite avec la remarque.
- (c) Il corrige lui-même ; sa version remplace celle de l'analyste.

## 12. Les acquisitions passées — NVDA ma_2

**Cas.** ma_2 (#1500, sans fondement) demande « ce que chaque acquisition a rapporté ». Personne ne le
publie : le dossier n'a que Groq (licence, 13 Md$) et Hugging Face (11,9 Md$, non conclue). Pour un
fonds, l'exemple parlant serait Mellanox (2020, ~7 Md$), devenu le réseau du Data Center — mais aucun
document ne chiffre « ce qu'elle a rapporté ».

**Ce que ferait un fonds.** L'analyste juge sur des **indices observables** : prix payé rapporté au chiffre
d'affaires acquis, évolution ensuite du segment qui l'a absorbée, dépréciations d'écart d'acquisition,
cessions ou abandons. Il ne cherche pas un rendement que personne ne publie.

**Question.** La question doit-elle se juger sur ces indices ?

- (a) **Oui, reformuler** : prix payé, évolution du segment d'accueil, dépréciations et cessions.
  *Recommandé.*
- (b) La garder telle quelle et accepter qu'elle reste le plus souvent sans fondement.

## 15. Une pièce ancienne qui périme une réponse à jour — NVDA ma_1

**Cas.** ma_1 (#1475) citait le communiqué de rachat d'actions du 18/05 **et** celui du 28/09. Une
émission obligataire du 15/06 tombe entre les deux : à cause du document du 18/05, toute la réponse a
été déclarée périmée, alors que le document du 28/09 la tenait à jour.

**Ce que ferait un fonds.** Une note est à jour si son information la plus récente **sur chaque sujet**
l'est ; un document remplacé par un plus récent sur le même sujet est du contexte, il ne date pas la note.

**Question.** Pour juger qu'une réponse est périmée, retient-on, sujet par sujet, la pièce la plus
récente ?

- (a) **Oui** : sur un même sujet, seule la pièce la plus récente compte pour la fraîcheur.
  *Recommandé.*
- (b) Non, rester strict : l'analyste ne doit pas citer une pièce remplacée ; s'il le fait, la réponse
  est périmée et renvoyée.

## 17. Relancer l'analyse après une décision du comité

**Cas.** Aujourd'hui, relancer l'analyse d'un chapitre refait toutes ses questions : une réponse que le
comité aurait acceptée serait remplacée, et une recherche qu'il aurait arrêtée, rouverte. Aucune décision
n'a encore été enregistrée : c'est la règle à poser avant la première.

**Ce que ferait un fonds.** Une décision du comité fait foi jusqu'à ce qu'un **fait nouveau** la remette
en cause ; l'analyste ne la défait pas en refaisant son travail, il la **soumet de nouveau**.

**Question.** Une relance peut-elle défaire une décision du comité ?

- (a) **Non, sauf fait nouveau** : la relance saute les réponses acceptées et les recherches arrêtées ;
  si un fait nouveau les touche, elle produit une proposition que le comité tranche. *Recommandé.*
- (b) Oui : la relance remplace, le comité ré-accepte.

## 20. Le 4ᵉ titre du test

**Cas.** Le test porte sur NVDA (établie), RVMD (biotech), MSFT (établie, diversifiée). Le modèle des
comptes n'a jamais vu le bilan d'une banque ou d'un assureur (pas de « stocks », pas de « marge brute »,
la dette est la matière première). Un émetteur étranger (rapport annuel au format 20-F) ajouterait une
deuxième difficulté.

**Ce que ferait un fonds.** Le test couvre les profils qu'il compte détenir, une difficulté à la fois.

**Question.** Quel 4ᵉ titre ?

- (a) **Une financière américaine** (banque ou assureur, rapport 10-K) ; l'émetteur étranger après le
  jalon. *Recommandé.* Préciser le titre (ex. JPMorgan pour une banque, Progressive pour un assureur).
- (b) Un émetteur étranger non financier (20-F).
- (c) Les deux (5 titres).
- (d) Rester à 3 titres.

## 21. RVMD : quand la reclasser « commerciale » ?

**Cas.** RVMD est classée « sans revenus » ; son médicament est approuvé depuis le 26/08/2026. Cinq
questions restent « sans objet », dont le pouvoir de prix (« aucun prix n'est encore pratiqué » — c'est
faux depuis le lancement) et le rendement du capital. Le premier trimestre de ventes paraîtra dans le
rapport trimestriel du T3 (début novembre).

**Ce que ferait un fonds.** Le lancement change la thèse : l'analyste propose au comité de changer de
grille. Mais des ratios sur quelques semaines de ventes ne disent rien : on attend en général le premier
trimestre publié pour les chiffres, tout en rouvrant tout de suite ce qui est observable (le prix).

**Question.** Quand reclasser RVMD ?

- (a) **Au premier trimestre de ventes publié** (T3, début novembre), proposé au comité ; d'ici là, rouvrir
  seulement le pouvoir de prix. *Recommandé.*
- (b) Tout de suite, dès l'approbation.
- (c) Après un exercice complet de ventes.

## Décisions

- **9 — séparer (2026-10-17)**, élargi par l'utilisateur : « estimer la taille de CHAQUE marché visé par
  une entreprise » (comme le potentiel de chaque molécule de RVMD), modélisation simple, structurée et
  repérable dans le bac à calcul (#96).
  **9-bis confirmé** : la question devient la LISTE des marchés visés (statut : métier actuel / extension
  annoncée / en développement ; taille ; part prise sur ventes CONSTATÉES seulement), et un seul tableau
  signé sert l'analyse et la valorisation. **Priorité de l'utilisateur : l'estimation INTERNE d'abord**
  (construite dans le bac à calcul, hypothèses sourcées) — une taille publiée ne sert que de point de
  comparaison, « on ne sait jamais de façon fiable ce qu'elle recouvre ».
- **10 — taux exigé UNIQUE pour le fonds (10-bis a)**, révisé une fois l'an, sensibilité ±1 point affichée ;
  le risque propre d'un titre va dans ses scénarios et probabilités (biotech : pondération des
  programmes, pas de prime de taux — sinon le risque est compté deux fois). Valeur proposée : 10 %
  (taux sans risque ~4 % + prime actions 4-6 points) — **10 % confirmé**.
- **11 — annoter, remis à l'analyste au premier passage du test (la reconstruction)** : accord.
  Souhait : que l'erreur se produise le moins possible → piste de contrôle (conclusion « répondue » alors
  que le chiffre sur lequel elle porte n'est pas établi, cas qf_6).
- **12 — reformuler** sur indices observables (prix payé / ventes acquises, segment d'accueil,
  dépréciations, cessions).
- **15 — la pièce la plus récente, sujet par sujet**, juge de la fraîcheur ; l'ancienne reste du contexte.
- **17 — modèle de l'utilisateur** : l'ajout d'un titre lance l'analyse complète jusqu'au bout ; une
  relance ne porte QUE sur les questions restées ouvertes ou rouvertes par un fait nouveau. Relevé du code
  (2026-10-17) : aucun lancement automatique (passages lancés à la main, chapitre par chapitre) ; deux
  outils — le passage de chapitre refait TOUTES les questions (sauf liste donnée à la main), le bouclage
  ne rejoue que les renvois ouverts (conforme au modèle) ; règle du registre du comité : « analyse refaite
  ⟹ acceptation tombe ». Écart à combler : une relance ne doit jamais refaire une question close.
  Exception nommée : la reconstruction du test (#127), refonte complète délibérée. **17-bis confirmé**,
  complété par l'utilisateur : **réinitialisation** d'une question ou d'un chapitre de son choix, même
  accepté par le comité (acte humain tracé au procès-verbal), à prévoir dès maintenant.
- **20 — les deux à terme** (financière US + émetteur étranger) ; moment non tranché par l'utilisateur ;
  **MSFT mis de côté** pendant la conception, gardé pour tester la reproduction sur une tech voisine de NVDA.
  **Découpage confirmé** : jalon 1 = NVDA + RVMD jusqu'au comité ; puis financière US ; puis étranger ;
  MSFT en contrôle de reproduction. Consigne : tout développement reste GÉNÉRIQUE (aucune règle par titre).
- **21 — au premier trimestre de ventes publié** (T3, début novembre), proposé au comité ; d'ici là,
  rouvrir le seul pouvoir de prix.
  **21 ROUVERT le 2026-10-17** (après la relance bornée) : « rouvrir le seul pouvoir de prix » est impossible
  sans un geste du gérant hors grille (mo_6 hors sujet pour « sans revenus »). L'utilisateur : « reposer le
  moins possible sur la relecture du gérant et le plus possible sur la fiabilité du système » — préfère ouvrir
  toute la grille plus tôt SI l'agent sait dire « pas de réponse à date ». À MESURER avant de trancher
  (acceptation de l'analyste sur RVMD en grille « rentable », sans écriture).


**Séance close le 2026-10-17** — règle durable : `CONVENTIONS.md` #137.
