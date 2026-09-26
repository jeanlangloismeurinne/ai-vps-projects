# Premier message à l'agent de développement

À coller tel quel pour démarrer le lot 0.

---

Tu prends en charge le développement du projet `projects/strategic-intelligence/` du dépôt
`ai-vps-projects`. La spécification est dans `projects/strategic-intelligence/spec-v2/`.
Il n'existe pas d'autre spécification : ne cherche pas de v1. Le dossier `prive/` (non versionné)
contient des données sensibles : ne le lis que sur demande explicite.

**Étape 1 — lecture, sans coder.** Lis `CLAUDE.md` et `CONTROL_SYSTEM.md` à la racine du dépôt,
puis dans `spec-v2/` : `README.md`, `00-BRIEF-AGENT.md`, `DECISIONS.md`, `01`, `02`, `05`, `04`,
`03-SCHEMA.sql`, `06`, `07`, puis `config-exemple/` et `modeles/`. Chaque sujet a un seul
fichier détenteur (voir le tableau du `README.md`).

**Étape 2 — état des lieux de la machine.** Décris ce que tu trouves : ressources (`nproc`,
`free`, `df`), conteneurs, présence de `db_strategic`, état de `comms-gateway` et de
newsletter-summary. Ne modifie rien.

**Étape 3 — compte rendu**, et rien d'autre :
- ta compréhension du système en 10 lignes ;
- les points de la spec ambigus, incomplets ou contradictoires, classés par gravité, avec
  l'option que tu retiendrais par défaut ;
- les risques techniques sur ce serveur, avec ta parade ;
- ton plan du lot 0, ticket par ticket, avec une estimation de durée.

**Étape 4 — attends ma validation** avant d'écrire la première ligne de code.

Contraintes permanentes :
- les 12 règles d'or de `00-BRIEF-AGENT.md` priment, en particulier : aucune valeur sectorielle
  dans le code, toute sortie par le routeur de sortie, rien de `red` hors du serveur ;
- un invariant n'est « réalisé » que si un check le garde et qu'il a été vu rouge une fois ;
- lot par lot, sans anticiper ; `ARCHITECTURE.md`, manifestes et `ARCHITECTURE.md` de module mis
  à jour dans le même commit que le code ;
- en fin de session : `00-REPRISE.md` actualisé (sans empiler), et un compte rendu : fait, reste
  sur le lot, coût externe du mois, décisions prises seul ;
- tout choix qui augmente le coût mensuel m'est soumis avant d'être fait.
