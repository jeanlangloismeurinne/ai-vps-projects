# Collecte de sources — `app/modules/recueil/`

Contrat **1.0.0**. Module M2 du plan `roadmap/V3/07-avant-comite.md`. **État : construit et prouvé
hors ligne le 2026-11-16 (société fictive, sans base, sans réseau, sans dépense) ; passage à blanc
réel sur SpaceX, en mémoire, contre le registre de la SEC (gratuit). Le rangement en base (tables
`recueil_*`, migration 064, `app/modules/recueil/depot_base.py`) est construit et prouvé le
2026-11-16 sur une base PostgreSQL 16 locale/jetable (`checks/check_recueil_persist.py`) ; PAS
ENCORE APPLIQUÉE en production. Le moteur réel (Exa), le modèle réel (DeepInfra) et l'évaluateur
réel des sources inconnues sont construits et prouvés hors ligne le 2026-11-18
(`checks/check_recueil_evaluateur.py`), et essayés en réel EN MÉMOIRE (`tools/essai_evaluateur.sh`).
PAS ENCORE ACCEPTÉ** : restent l'écran, le déclencheur, et les lignes « réel » (B3, B6, B10, B12-B14) de `roadmap/V3/M2-collecte-sources.md`,
qui porte aussi le tri de l'ancien code.

*Ce que ferait un vrai fonds* : la documentation reçoit une demande de l'analyste, rend les documents
eux-mêmes avec leur provenance, ou répond « ça n'existe pas » en disant pourquoi ; elle ne lit pas
les documents pour lui.

## Ce qu'il rend

Le **recueil d'un émetteur** (`contrat.Recueil`), lu par une seule fonction : `contrat.lire_recueil`.
Pour chaque demande (un **genre** de document au référentiel, un émetteur, une date de départ ou une
adresse), la dernière **réponse** : des documents bruts — chacun avec sa provenance (adaptateur,
adresse, registre, numéro, partie, date de publication, date des faits, document amendé, mention) et
la qualification que M1 donnait à son adresse au jour de la collecte — ou une **indisponibilité**
nommée (raison au référentiel, chaque source essayée avec ce qu'elle a dit). Le contenu brut se lit
par `contrat.lire_contenu(empreinte)`.

## Comment c'est construit

```
contrat.py        objets, dépôt (interface + mémoire + base), lecture, gestes, pas du chef de dossier
coeur.py          l'ordre des sources, l'identité, le rangement, les deux pas (aucun formulaire)
depot_base.py     le rangement en base (tables recueil_*, migration 064) — seul fichier à les nommer
referentiel.json  genres de document, ordre des familles, raisons d'indisponibilité
adaptateurs/
  __init__.py     l'interface d'un adaptateur (Appel, Trouvaille, Identification), la reprise unique
  registre_sec.*  dépôts de la SEC : le SEUL endroit où s'écrivent formulaires et adresses du registre
  site.*          les pages de l'émetteur, aux lieux de sa fiche (jamais devinés)
  web.*           un moteur de recherche INJECTÉ ; domaines de la fiche d'abord (#133)
  exa.*           le moteur réel : chercher, et le texte des pages qui refusent la lecture directe
  deepinfra.*     le modèle réel : un objet JSON et ce qu'il a coûté ; reprises sur « occupé »
  transport.py    le seul fichier qui touche le réseau (lire, envoyer en JSON ; bibliothèque standard)
evaluateur.py     l'évaluateur réel des sources inconnues (rôle distinct du collecteur)
evaluateur.json   son modèle, sa consigne, ses recherches de publications — jamais dans le code
```

**L'évaluateur réel** (#145) : pour une source (un domaine), il lit autant de publications que la
grille de M1 en exige (`emetteurs.grille_d_evaluation`) — celles rencontrées d'abord, puis les
recherches du référentiel limitées au domaine (pages datées d'abord : une recherche sur un site rend
aussi ses pages de rubrique) ; une page refusée en direct est relue par le moteur (seulement ce qui
manque, plus une). Le modèle répond à chaque question pour chaque publication et choisit un critère
écrit ; **le niveau et les natures sont ceux du critère**, pas ceux du modèle. Hors forme, trop peu de
publications, modèle occupé : `EvaluationImpossible` nommée, avec ce qui a été payé (le cœur le
cumule sur la source ; deux essais manqués = échec nommé). **Un aperçu n'est pas une publication**
(arbitrage du 2026-11-18) : le modèle dit d'abord si chaque texte est complet ; un aperçu d'article
payant ne compte pas, et s'il en manque, `EvaluationImpossible` les désigne. Notre propre coupe
(`caracteres_par_publication`) est annoncée en tête et en fin du texte pour ne pas passer pour un
aperçu. Modèle : DeepSeek-V4.1-Flash (référentiel 1.1.0 ; mesures et raison du choix dans
`evaluateur.json`, `_modele`).

- **Ordre d'autorité** : registre officiel, site de l'émetteur, web. On s'arrête à la première
  famille qui rend un document ; les sources essayées avant restent dans la réponse (`essais`).
- **Identité** (#147) : avant de chercher, chaque registre dit ce qu'il sait de l'émetteur ; trouvé,
  `emetteurs.completer_identite` (signé `systeme:documentation`) révise la fiche — jamais les lieux ;
  un champ que vous avez corrigé n'est plus réécrit ; un homonyme → acte attendu, jamais tranché.
- **Prospectus** (#148) : au référentiel du registre, « derniers comptes annuels » a un repli
  (`a_defaut`) et sa mention.
- **Brut, une fois** : un document est identifié par l'empreinte de son contenu ; rangé, il ne se
  réécrit pas ; une collecte interrompue ne retélécharge pas ce qui est rangé (`deja`).
- **Sources inconnues** (#145) : un document non admis est gardé et marqué ; sa source est notée à
  évaluer ; `evaluer_les_sources_rencontrees` la présente à l'évaluateur (injecté) et range son
  jugement chez M1. Les pages de relations investisseurs d'autres sociétés rencontrées sont admises
  au fil de l'eau (`emetteurs.admettre_pages_investisseurs`).
- **Deux pas au chef de dossier** (#146) : `pas_collecte` (toujours après la fiche) lance les
  demandes et rend « en cours » jusqu'à ce que toutes aient répondu ; `pas_evaluation` suit le
  jugement des sources inconnues sans retenir personne, et déclare ce que l'évaluateur a coûté. Les
  pas n'écrivent rien : ce qu'ils décident part dans un `Envoi` que l'appelant range dans la même
  transaction que l'état du dossier.

## Invariant → assert garant

Contrôle : `checks/check_recueil.py` (société fictive) ; test négatif : `checks/negatif_recueil.sh`
(43 mutations, toutes détectées sur leur assert le 2026-11-16 ; les mutations de la règle « votre
correction tient » visent son détenteur, `emetteurs/regles.py`). Garde des accès : `[C7]` de
`check_charte_modules.py`, étendue le 2026-11-16 aux formulaires, registres et places.

**Le rangement en base** (tables `recueil_*`, migration 064) : contrôle `checks/check_recueil_persist.py`
(59 vérifications le 2026-11-16, prouvé sur une base PostgreSQL 16 locale/jetable — PAS ENCORE
appliqué en production) ; test négatif `checks/negatif_recueil_persist.sh` (7 mutations du code
de `depot_base.py` + 9 de la migration 064, toutes détectées le 2026-11-16).

| Ligne | Invariant | Assert |
|---|---|---|
| R0 | 064 appliquée ici, sinon échec nommé (jamais un saut) | [R0] |
| R1 | les mêmes gestes jouées sur `DepotMemoire` et sur le dépôt base rendent le même `lire_recueil` et la même `vue_ecran`, comparés en entier | [R1] |
| R2 | documents, contenus, réponses : la base refuse UPDATE et DELETE (ajout seul) | [R2] |
| R3 | le même document rangé deux fois : une seule ligne, contenu identique octet pour octet (binaire compris) | [R3] |
| R4 | une collecte interrompue puis reprise ne recollecte pas ce qui est déjà rangé | [R4] |
| R5 | une source rencontrée deux fois : adresses fusionnées (dédupliquées, anciennes d'abord), état gardé ; `marquer_source` fusionne | [R5] |
| R6 | même résultat avec et sans le codec JSON du service | [R6] |

| Ligne | Invariant | Assert |
|---|---|---|
| — | Seul le transport touche le réseau ; aucun modèle importé | [B0] |
| B1 | Le cœur ne nomme aucun formulaire (lus dans les référentiels des adaptateurs) ; un registre de plus = un adaptateur injecté | [B1] |
| B2 | Sans numéro, non cotée, sans fiche : document ou indisponibilité nommée, jamais une exception ; sans fiche, l'acte | [B2] |
| B3 | Prospectus à défaut de rapport annuel, dit dans l'origine ; jamais un trimestre ; le rapport annuel dès qu'il existe | [B3] |
| B4 | Brut, une fois ; un amendement cite ce qu'il amende ; pas de second téléchargement | [B4] |
| B5 | Provenance complète et qualification de M1 ; non admis = marqué ; seules les pièces nommées | [B5] |
| B6 | Source inconnue à l'évaluateur, sans attendre ; admise au seuil, en suspens dessous ; plantage compté, deux fois = échec nommé | [B6] |
| B7 | Pages de relations investisseurs d'une autre société admises ; jamais celles de l'émetteur | [B7] |
| B8 | Travail suivi ; on avance à côté ; une réponse par demande à la reprise ; échec relancé une fois puis arrêt | [B8] |
| B9 | Web et évaluateur déclarés au chef de dossier, une fois ; registre et site à 0 | [B9] |
| B10 | Fiche complétée depuis le registre ; votre correction tient ; lieux intouchés ; homonyme = acte | [B10] |
| B11 | PDF, page vide, registre en erreur deux fois : indisponible nommé ; une seule seconde tentative | [B11] |

**Le moteur, le modèle et l'évaluateur réels** : contrôle `checks/check_recueil_evaluateur.py`
(60 vérifications le 2026-11-18, transport simulé dont les réponses copient la forme réelle relevée
le même jour) ; test négatif `checks/negatif_recueil_evaluateur.sh` (44 mutations, toutes détectées).

| Ligne | Invariant | Assert |
|---|---|---|
| X1-X2 | La demande à Exa porte requête, nombre, domaines, catégorie ; dépense = celle déclarée, sinon repli > 0 | [X1] [X2] |
| X3 | Exa qui refuse ou se tait : `MoteurInjoignable` ; le web en fait « injoignable » nommant le moteur | [X3] |
| X4 | Texte des pages rendu sous l'adresse demandée ; dépense comptée | [X4] |
| M1-M3 | Objet JSON + dépense déclarée (sinon jetons × prix, sinon repli) ; « occupé » repris selon le référentiel ; coupé ou non JSON = échec avec sa dépense | [M1] [M2] [M3] |
| V1-V2 | Publications de la source seule, rencontrées d'abord ; recherche seulement s'il en manque ; relecture par le moteur bornée ; trop peu = échec sans appel au modèle | [V1] [V2] |
| V3-V5 | Grille et critères de M1 tels qu'écrits ; le critère fixe niveau et natures ; réponse hors forme = échec, jamais transmise | [V3] [V4] [V5] |
| V6 | Bout en bout : admise / en suspens ; dépense = recherche + pages + modèle ; essais manqués payés et comptés | [V6] |
| V7 | Modèle et consigne au référentiel, pas dans le code | [V7] |
| V8 | Un aperçu ne compte pas : « texte complet » motivé exigé ; incomplète = échec nommé qui la désigne, avec la dépense ; notre coupe est dite au modèle | [V8] |

## Ce qui n'existe pas encore (dit, pas caché)

- **Une source payante inconnue ne peut pas être évaluée** : ses publications ne sont lisibles qu'en
  aperçu ; elle finit en échec nommé et attend l'arbitrage à l'écran. La lecture des articles payants
  pendant la collecte est une question ouverte (`roadmap/V3/M2-collecte-sources.md` §6).
- Le modèle rend parfois une réponse hors forme (2 sur ~20 appels mesurés) : échec nommé, la
  relance du cœur la rejoue.
- **Le déclencheur** qui appelle le chef de dossier, la tâche de fond (`traiter_les_travaux`,
  `evaluer_les_sources_rencontrees`) et range l'`Envoi` : à construire.
- **L'écran** (B12) : `vue_ecran` est écrite, aucune route ni page.
- **La migration 064 n'est pas appliquée en production** : écrite, prouvée en local/jetable
  uniquement (motif #17 — jamais auto-appliquée) ; l'appliquer est un pas distinct.
- Le registre ne lit que les dépôts « récents » de la SEC (le millier le plus récent) : un dépôt plus
  ancien n'est pas vu. Une page du site ne dit pas sa date : `publie_le` reste vide, jamais devinée,
  et un genre « depuis une date » trouvé sur le site n'est pas filtré par date.
- Une source rencontrée par deux dossiers est évaluée une fois ; sa dépense est déclarée au dossier
  qui l'a rencontrée le premier.
- Les documents fournis à la main et les autres régulateurs : un adaptateur de plus (B1), pas construits.
