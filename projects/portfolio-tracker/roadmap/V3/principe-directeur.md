---
id: principe-directeur
status: constitution en vigueur
created: 2026-08-11
updated: 2026-11-13 (réécrite après les arbitrages de l'évaluation d'architecture ; version antérieure, intégrale : `roadmap/archive/V3-principe-directeur-avant-2026-11-13.md`)
project: portfolio-tracker
role: >
  La constitution technique du système visé : les règles durables que tout module, toute spec et tout
  changement de code doivent respecter. Elle ne raconte rien et ne planifie rien — le plan est
  `07-avant-comite.md`, le schéma des blocs `ARCHITECTURE-CIBLE.md`, la conduite des arbitrages
  `PRINCIPES-FONDATEURS.md`.
---

# Principe directeur — la constitution

Ce document prime sur toute spec de détail : en cas de contradiction, c'est lui qui tranche. Il ne
cède qu'aux `PRINCIPES-FONDATEURS.md` (comment on décide et comment on demande) et à la liste « Ce
qui est fermé » de `00-REPRISE.md` (ce qu'on ne rouvre pas).

## 1. Comment on construit

- **Module par module, sur une base propre.** Un module marche — seul, sur NVDA et sur RVMD — avant
  qu'on ouvre le suivant. L'ordre et l'acceptation de chacun sont dans `07-avant-comite.md`.
- **Les modules reconstruits vivent dans `backend/app/modules/`.** Tout le reste de `backend/app/`
  est l'ancien code : une **carrière**. À l'ouverture d'un module on y reprend ce qui tient dans son
  contrat, on laisse le reste ; ce qu'un module remplace est **supprimé le jour où ce module est
  accepté**. Tant qu'il n'est pas remplacé, l'ancien code reste en place et ses contrôles restent verts.
- **Un document de cadre ne décrit jamais comme en vigueur un mécanisme supprimé ou une méthode
  abandonnée.** Un plan terminé, un prompt ponctuel, une proposition arbitrée partent dans
  `roadmap/archive/`.

## 2. La charte d'un module

Elle vaut pour tous les modules, sans exception.

1. Il **possède ses tables** ; personne d'autre ne les lit.
2. Il rend **un seul objet de sortie**, versionné, lu par une seule fonction. Un contrôle refuse tout
   autre accès, et vire au rouge quand on le casse.
3. Il se livre **avec son écran** : on voit ce qu'il produit.
4. Il se teste **seul**, sur une société fictive et des modèles simulés, sans dépense.
5. **Rien de propre à une société, à un pays ou à une place de cotation n'est écrit dans son code** :
   c'est une donnée des référentiels (principe fondateur n° 4).
6. Son **acceptation est écrite avant** sa construction, et passée sur NVDA **et** RVMD.
7. Il s'ouvre par un **tri** de l'ancien code et des données déjà en base : repris tel quel / repris
   derrière le contrat / laissé. Une pièce déjà collectée se garde si elle satisfait le contrat ; les
   réponses des anciens chapitres ne sont pas reprises (elles servent de contrôle, gratuitement).
8. Il **déclare son pas au chef de dossier** et **compte ce qu'il dépense** — modèles et recherches web.

**Lecture humaine.** Tant que le taux d'erreur d'un module n'est pas mesuré, sa sortie est lue par un
humain avant que le module suivant s'en serve. C'est un interrupteur par module, levé un à un
(principe fondateur n° 3 : la lecture humaine est la règle simple, l'automatisation son raffinement).

## 3. Les deux règles du schéma des blocs

1. **Un bloc ne lit d'un autre que son contrat de sortie.** Ni ses tables, ni ses fonctions internes.
2. **Le non coté et les émetteurs de l'UE n'ajoutent que des adaptateurs, un kit de spécialité et une
   famille de comptes.** S'il fallait toucher un autre bloc pour les accueillir, le contrat de ce
   bloc serait à revoir maintenant.

Le **chef de dossier** (automate sans modèle de langage) lit tous les contrats et n'en écrit aucun :
il donne le pas suivant ou nomme l'acte humain attendu. Le schéma : `ARCHITECTURE-CIBLE.md`.

## 4. Les trois garde-fous

- **G1 — Le contrat est un objet versionné, source de vérité unique.** La consigne donnée au modèle
  (exemple de sortie compris), l'écran et la validation à l'écriture en dérivent, jamais l'inverse ;
  les trois se modifient dans le même changement.
- **G2 — La décision ne dépend pas de l'écran.** Les règles de décision (§8) sont définies d'abord et
  contraignent l'affichage. Un écran n'encode jamais un comportement séduisant mais faux, et le corps
  d'un acte de décision ne porte que ce que son auteur a le droit de décider.
- **G3 — Toute information entre datée, sourcée et figée avant d'être utilisée.** Aucune pièce n'est
  lue par un module avant d'exister dans la base de connaissance avec son origine et ses dates ; une
  pièce ne se modifie pas, elle se remplace en laissant sa trace ; une recherche faite à la demande
  entre par la même porte qu'un flux régulier. Fiabilité, nature et actualité restent trois
  propriétés distinctes, jamais fondues en une note (`doctrine-trois-axes.md`).

## 5. Les modèles de langage

- **Un seul fournisseur : DeepInfra.** Tout appel passe par l'interface de fournisseur du projet ;
  aucun module n'appelle directement une bibliothèque de modèle.
- **Le modèle de chaque rôle est une donnée**, pas une constante dans le code ni un nom dans un
  document de cadre.
- **Changer le modèle d'un rôle rejoue les dossiers étalons** de ce rôle avant d'être adopté.
- **Ce qui se calcule ne se demande pas à un modèle** : comptes, squelette du classeur, valorisation
  et enchaînement du dossier sont du code, rejouable à l'identique.
- **On mesure le coût, on ne plafonne pas la qualité.** Chaque module compte sa dépense ; le chef de
  dossier fait une pause tous les 1 $ consommés sur un dossier, avec l'estimation du coût restant.

## 6. Le kit de spécialité

Un seul analyste générique, outillé par un **kit de spécialité** tenu en donnée dans les référentiels :
sources du secteur, famille de comptes, moteurs types, questions propres, dossiers étalons. Ajouter un
secteur ajoute un kit, sans toucher aux modules.

**Une entreprise sans kit suit le parcours généraliste**, qui doit rester assez souple pour bien
l'analyser : le kit affine, il n'est jamais une condition d'entrée (arbitrage du 2026-11-13).

## 7. Les sources

- **Le système évalue les sources et les admet lui-même**, sous contrôle a posteriori : chaque
  admission est datée et motivée dans un registre que l'utilisateur suit et corrige (principe
  fondateur n° 2, modifié le 2026-11-13).
- Une source **révoquée** signale les pièces qui s'y appuient.
- Le modèle qui utilise une source n'est jamais celui qui la qualifie.
- La fiabilité d'une source ne se dégrade pas selon l'émetteur étudié.

## 8. Règles de décision (ce que tout écran doit servir)

- **Horizon d'au moins cinq ans.** Une valeur centrale, une fourchette et ce que le prix suppose —
  pas un objectif de cours.
- **On vend sur une dégradation de la thèse**, pas sur un seuil de prix mécanique. À chaque revue on
  se demande si la thèse, restée valide, justifie encore le prix ; la surévaluation seule conduit à
  ne pas renforcer et à revoir.
- **Trois indicateurs distincts, jamais fusionnés** : qualité de l'information · conviction sur la
  thèse · marge de sécurité.
- **Tout se reconstitue** : on peut toujours répondre « pourquoi le système a dit cela » à partir des
  pièces figées qu'il a lues.
- **L'effort de recherche suit le poids dans la valeur et les débats de la thèse** ; on ne cherche pas
  pour accumuler.
- **Restent des actes humains** : arrêter ou poursuivre un dossier, valider la carte et les débats,
  signer le modèle et sa fourchette, décider d'investir. Le comité ne voit que les exceptions.

## 9. Test de conformité

Une contribution est prête si elle répond « oui » à tout :

- [ ] Respecte-t-elle les huit points de la charte (§2) ? Son acceptation était-elle écrite avant ?
- [ ] Ne lit-elle des autres blocs que leur contrat de sortie (§3) ?
- [ ] Son contrat est-il versionné, et consigne, écran et validation changés ensemble (G1) ?
- [ ] La règle de décision est-elle définie avant l'écran et conforme au §8 (G2) ?
- [ ] Toute information utilisée est-elle une pièce datée, sourcée et figée (G3) ?
- [ ] Le modèle de chaque rôle est-il une donnée, appelé par l'interface de fournisseur (§5) ?
- [ ] Rien de propre à une société, un pays ou une place de cotation n'est-il dans le code (§2.5) ?
- [ ] Chaque contrôle neuf a-t-il viré au rouge pour la bonne raison (`METHODE-TEST.md`) ?
