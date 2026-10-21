# Procédure — test d'arbitrage (QC de la mission)

**But** : vérifier que `MISSION.md` suffit à trancher comme l'utilisateur. Ponctuel : à
l'activation, après un changement de principe, et quand la jurisprudence a grossi de 5 entrées.

## 1. Contrôle de forme (par l'orchestrateur, rapide)
- (B) Utilisateur et valeur explicites, valeur en **résultat**.
- (B) Mesure de succès observable.
- (B) Principes ordonnés, chacun avec question-test et exemple.
- (B) Modèle de référence (P0), ou absence justifiée.
- (B) Le jalon actif a un scénario de démonstration.
- (M) Chaque capacité de la roadmap sert un élément de la mission.

## 2. Test d'arbitrage (par un relecteur NEUF)
- **Dilemmes** : 5 à l'activation (rédigés avec l'utilisateur, avec sa réponse tenue à part),
  puis les entrées de `JURISPRUDENCE.md`.
- **Relecteur** : un contexte neuf qui ne reçoit **que** `MISSION.md` et les dilemmes (sans les
  réponses). Aujourd'hui : un sous-agent (`Agent`) ; plus tard un autre compte ou fournisseur
  (`REFLEXION.md`, chantier multi-comptes).
- Il rend, pour chaque dilemme : la décision + le principe invoqué.
- **Lecture** : désaccord avec l'utilisateur, ou bon verdict pour un mauvais principe →
  la mission a un trou. Il devient une **question à l'utilisateur** (nouveau principe ?
  question-test à préciser ? ordre à changer ?), jamais un ajout de l'agent.
