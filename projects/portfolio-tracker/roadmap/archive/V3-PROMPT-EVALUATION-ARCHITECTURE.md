---
id: prompt-evaluation-architecture
status: v1 prêt à lancer (phases 1-2 seulement)
created: 2026-11-13
project: portfolio-tracker
role: >
  Prompt à donner à un modèle (Fable 5.2) pour évaluer l'architecture du système de pilotage
  d'investissement et proposer des améliorations. Phases 1-2 : audit et propositions. Phase 3 :
  réalisation, seulement après arbitrage explicite de l'utilisateur.
---

# Prompt — évaluation de l'architecture

```
Reprends le projet portfolio-tracker à partir du fichier de reprise, en mode
ÉVALUATION D'ARCHITECTURE.

# Mission

Évaluer, puis améliorer si c'est justifié, l'architecture du système de pilotage
d'investissement. Tu as la liberté de remettre en cause la proposition en cours, de
l'adopter, ou d'en proposer une troisième : juge sur pièces.

Objectif final : un système qui réplique le fonctionnement d'un fonds d'investissement
FONDAMENTAL, à HORIZON LONG TERME (+5 ans), CONCENTRÉ, sur les actions cotées
d'abord, le non coté ensuite. Quatre exigences, par ordre d'importance :

1. QUALITÉ de l'analyse : chaque chiffre renvoie à une pièce, les erreurs sont détectées
   et mesurées, un dossier se rejoue à l'identique.
2. AUTONOMIE maximale jusqu'à la DÉCISION AU COMITÉ INCLUSE : sourcing, instruction,
   modèle, valorisation, mémo, suivi tournent sans l'utilisateur. L'humain n'intervient
   qu'aux actes qu'un vrai fonds ne délègue jamais (admettre une nouvelle source de
   référence, trancher une interprétation contestée, décider d'investir) — et tu
   justifies chaque point d'intervention humaine.
3. MODULARITÉ PAR BLOC : chaque bloc (collecte de sources, base de connaissance, comptes
   et segments, filtres, carte des sources de profit, modèle, recherche ciblée,
   jugements, valorisation, mémo/comité, suivi) évolue presque indépendamment des
   autres, derrière un contrat d'interface explicite et versionné. Prévoir dès
   maintenant, sans les construire : un module de CONSTRUCTION DE PORTEFEUILLE
   (taille des positions, concentration, règles de vente) branché après le comité,
   et un module NON COTÉ. Pour le non coté, la cible est de le garder en tête dans
   les contrats : on ne le construit pas dans ce chantier.
4. SOURCES OUVERTES dans le cœur (dépôts SEC, sites d'émetteurs, web) ; les sources
   semi-ouvertes futures (non coté : documents fournis, data rooms) entrent par un
   point d'extension, jamais en dur dans le cœur.

# À lire d'abord, dans cet ordre

1. projects/portfolio-tracker/roadmap/V3/PRINCIPES-FONDATEURS.md : TES règles de conduite
   (questions en termes métier, « ce que ferait un vrai fonds », un raffinement se
   débraye vers la règle simple, on corrige la CAUSE jamais l'exemple).
2. roadmap/V3/00-REPRISE.md.
3. La proposition à évaluer : roadmap/V3/PROPOSITION-PROCESSUS-INSTRUCTION-2026-10-24.md
   (copie du doc « Processus d'instruction — proposition » ; état de réflexion du 24/10,
   issu des difficultés rencontrées avec le système conçu initialement ; PAS un
   arbitrage). Les schémas du doc d'origine n'y figurent pas.
4. roadmap/V3/principe-directeur.md (constitution, prime sur toute spec),
   03-spec-frameworks.md (§0 : les faits qui ont motivé la V3), doctrine-trois-axes.md,
   ARCHITECTURE-CIBLE.md, 09-modele-entreprise.md, 07-avant-comite.md (plan et journal).
5. Les ARCHITECTURE.md de module ; CONVENTIONS.md par grep ciblé (#1 à #143) AVANT de
   toucher ou critiquer un module.
Une brique n'existe que si un backend/checks/check_*.py la garde et qu'un negatif_*.sh
prouve que ce check rougit quand on la casse. Exécute les checks gratuits (depuis backend/),
ne présume pas ; si ton environnement ne permet pas de les lancer (base, Docker absents),
dis-le et classe le constat « non vérifié » plutôt que de le déduire du texte.

# Ce qui est fermé (ne pas rouvrir sans le dire explicitement)

Voir « Ce qui est fermé » de 00-REPRISE.md (grille MVDD, hybridation RRF, leviers du
modèle sur l'exigence, etc.). Si tu veux rouvrir un point, nomme-le, argumente, et
attends mon arbitrage ; ne le contourne jamais en silence.

# Phase 1 : AUDIT (lecture seule, aucune dépense de modèle)

Évalue l'architecture existante ET la proposition sur ces axes, chacun avec preuve
(fichier, check, mesure, journal) :

a) Fidélité à un fonds fondamental long terme : sourcing, filtres, modèle, thèse, comité,
   suivi des dossiers ; ce qui manque ; ce qui est sur-construit pour la valeur apportée.
b) Autonomie : cartographie de chaque intervention humaine requise aujourd'hui, avec
   verdict (légitime / à automatiser / à supprimer) et condition de sortie.
c) Qualité : comment une erreur est détectée (garde de STRUCTURE vs de SENS, conv. #68),
   comment elle est mesurée, rejouée ; dettes de mesure ; faux verts possibles.
d) Modularité : contrats entre blocs, couplages cachés (hypothèses « société cotée US /
   dépôts SEC » codées en dur, constantes globales, vocabulaires partagés), coût réel
   d'ajouter le non coté, un nouveau module en aval du comité, une autre juridiction.
   Le module `nasdaq/` est le contre-exemple d'un bloc autonome : mesure ce qu'il
   enseigne.
e) Sources : cartographie par étape, ouvertes / semi-ouvertes, risque de rupture,
   provenance (#28), dépendance à un fournisseur (DeepInfra, Exa, Serper).
f) Coût et robustesse : dépense par dossier, instabilités observées et leur CAUSE
   (principe 4), ce qui n'a pas été éprouvé hors NVDA et RVMD (cas fictifs d'abord).

Rends un diagnostic classé par gravité. Distingue clairement : prouvé / déduit / non
vérifié. Ne fais aucune recherche web ni appel payant dans cette phase.

# Phase 2 : PROPOSITIONS (je tranche)

Pour chaque amélioration retenue : le problème et sa cause, la preuve, « ce que ferait un
vrai fonds », option recommandée + alternatives, coût et risque, test d'acceptation écrit
AVANT, impact sur le plan 07-avant-comite.md, et ce qui devient réversible par
interrupteur. Réponds aussi, avec une recommandation argumentée, aux questions ouvertes
du doc de proposition. Pose-moi tes questions en termes MÉTIER (principe 1), avec un cas
réel du portefeuille. Termine par l'architecture cible en blocs : un schéma, et pour
chaque bloc son contrat d'entrée/sortie, son propriétaire, et sa dépendance aux autres.

# Phase 3 : RÉALISATION (uniquement après mon arbitrage explicite, dans une autre séance)

Par lots annoncés en une ligne. Une brique = un check + un test négatif. Suite complète
(bash backend/checks/run_all.sh) rejouée après tout changement de contrat partagé ;
règle #19/#39 (prompt en base + exemple JSON + frontend + import).
Documentation commitée même sans déploiement.

# Garde-fous

- Production : aucun déploiement, aucune migration appliquée, aucun outil qui écrit ou
  dépense (tools/executer_chaine.sh, mesureurs) sans mon accord. Instance neuve de
  l'image, jamais dans portfolio-backend ; ps aux / docker ps avant toute relance.
- Dépense de modèle (crédits API DeepInfra/Exa des mesures du projet) : ZÉRO dans cette
  séance. Si une mesure payante te paraît indispensable, décris-la (objet, coût estimé)
  et attends mon accord. Phase 3 : plafond à fixer par moi avant toute mesure.
- Secrets : jamais dans le repo ni dans une sortie ; .env hors git.
- Pas de correctif qui reconnaît un exemple (nom, libellé, seuil calé sur NVDA ou RVMD).

# Livrable

Un doc à commenter (ou un fichier Markdown dans roadmap/V3/ si tu n'as pas d'outil Docs),
en français, comme le précédent : verdict en tête (adopter / adapter /
remplacer la proposition, en une phrase), tableau des constats par gravité, architecture
cible en blocs, recommandations ordonnées, questions pour moi. Puis mise à jour de
00-REPRISE.md SANS l'empiler (CONTROL_SYSTEM.md §5), et commit de la doc.
```
