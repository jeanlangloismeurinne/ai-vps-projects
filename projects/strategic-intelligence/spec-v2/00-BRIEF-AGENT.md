# Brief de mission — agent de développement

Tu construis et opères un système de veille stratégique hébergé sur le VPS de l'utilisateur
(dépôt `ai-vps-projects`, projet `projects/strategic-intelligence/`). Ce dossier est ton contrat.

## Contexte en une phrase

Un directeur de la stratégie veut une tour de contrôle qui collecte en continu de l'information
**publique**, la transforme en **signaux** qualifiés, suit ses **questions clés** et ses
**scénarios**, et lui livre des briefs et des notes transmissibles — sans jamais envoyer ses
**convictions** à un service externe.

## Les 12 règles d'or

1. **Aucune valeur sectorielle dans le code.** Entreprises, secteurs, segments, technologies,
   mots-clés, sources : tout vit dans le pack sectoriel et la configuration en base. Test :
   `check_agnosticite.py` échoue si un terme du pack apparaît dans le code.
2. **Aucune affirmation sans source.** Toute phrase générée qui énonce un fait porte une
   référence vers une `evidence` (citation exacte). Une affirmation orpheline est un défaut détecté.
3. **Toute sortie externe passe par le routeur de sortie.** LLM, embeddings, recherche web,
   courriel, Slack : un seul point de passage, qui applique les niveaux de sensibilité et
   journalise. Aucun appel direct à un fournisseur ailleurs (contrôle par analyse du code).
4. **Les données `red` ne sortent jamais du serveur.** Énoncés de thèses, confiances,
   annotations, notes terrain : ni LLM, ni embedding, ni courriel, ni Slack. Les données `amber`
   ne sortent que segmentées (`05`).
5. **Le moins cher d'abord.** Toute étape payante est précédée d'un filtre gratuit ; la
   déduplication documentaire précède tout appel LLM.
6. **Le brut est immuable, rien n'est jeté.** Un contenu collecté n'est ni modifié ni supprimé ;
   un contenu écarté est marqué avec son motif ; une correction est une nouvelle version.
7. **Aucun résultat dégradé en silence.** Chaque fonction déclare ses prérequis de données et
   s'auto-désactive en l'expliquant. Un échec est nommé, jamais un résultat vide.
8. **Ajouter une source, c'est du paramétrage.** Objectif mesuré : 80 % des sources ajoutées
   après le lot 0.5 le sont par l'interface, sans commit de code.
9. **Ajouter une fonction, c'est toucher un seul module.** Une fonction métier s'ajoute dans son
   module et s'abonne au bus d'événements ; elle ne modifie ni le noyau ni un autre module. Si
   c'est impossible, réviser d'abord `ARCHITECTURE.md` et le signaler.
10. **L'architecture réalisée se prouve, elle ne se déclare pas.** `ARCHITECTURE.md` décrit la
    cible ; ce qui est réalisé est prouvé par un check exécutable. Un invariant sans check est une
    dette marquée ⚠️. Un check neuf n'est éprouvé qu'après avoir viré au rouge une fois (test négatif).
11. **Tout est reproductible.** Le déploiement se fait par `infrastructure/compose-deploy.sh` ;
    toute action manuelle non documentée est un bug. L'amorçage d'une base vide charge le noyau
    générique et le pack sectoriel actif.
12. **Contexte : documentation d'abord, puis lecture ciblée.** Pour reprendre, lire
    `ARCHITECTURE.md`, `00-REPRISE.md`, puis l'`ARCHITECTURE.md` du module concerné. Avant de
    modifier du code, le lire **de façon ciblée** (recherche, puis extrait). Ne jamais charger un
    dossier entier. Une doc de module fausse se corrige dans le même commit.

## Méthode de travail

- Travailler lot par lot selon `06-ROADMAP.md`. Pas de lot N+1 avant que les critères du lot N
  soient verts **et vérifiés en conditions réelles** (déployé, exécuté, observé), pas seulement
  en test.
- Un commit par ticket, message en français, préfixé par l'identifiant du ticket. Terminer le
  message par la ligne d'attribution demandée par l'environnement.
- Committer et pousser avant de déployer ; après déploiement, vérifier dans le conteneur que le
  code attendu tourne (commité n'est pas déployé).
- Tenir à jour `00-REPRISE.md` (état, prochain jalon, dettes ouvertes, commandes de reprise) en fin
  de session, et `DECISIONS.md` pour toute décision non prévue par la spec.
- Idées hors backlog : les noter dans `PROPOSITIONS.md` et continuer.
- Information manquante : choisir l'option la plus simple, la consigner dans `DECISIONS.md` et la
  signaler en tête du compte rendu.
- Tout choix qui augmente le coût mensuel est soumis à l'utilisateur avant d'être fait.
- Un correctif de prompt ou de mappage n'est acquis qu'après avoir tourné contre l'API réelle.

## Définition du « fini » pour un ticket

- Le code est typé, passe le linter, et ses tests unitaires passent.
- Les invariants qu'il introduit sont gardés par un check cité dans l'`ARCHITECTURE.md` du
  module, et ce check a été vu rouge au moins une fois (mutation dans `negatif_*.sh`).
- La migration est écrite et réversible.
- Le manifeste du module et son `ARCHITECTURE.md` sont à jour dans le même commit.
- `bash checks/run_all.sh` est vert, bilan lu par sa forme (`N vérifications OK, 0 échec`).
- Pour une source ou un prompt : exécuté au moins une fois contre le service réel.

## Ce que tu ne dois jamais faire

- Contourner les conditions d'utilisation d'une plateforme ou ignorer un `robots.txt`.
- Ingérer une donnée personnelle hors qualité professionnelle.
- Envoyer une donnée `red` hors du serveur, ou une donnée `amber` non segmentée.
- Coder en dur une clé, une URL de source, un nom d'acteur ou un terme sectoriel.
- Lancer un traitement de masse payant sans estimation préalable affichée.
- Fusionner deux entités ou créer un acteur sans validation humaine.
