# Mode SDD léger — garder le cap

> **Statut : proposé, non implémenté** (rédigé le 2026-10-21, aucun projet activé).
> Ce dossier n'est chargé par **aucune** session par défaut. Il n'est lu que depuis un projet
> dont le `00-REPRISE.md` porte `mode: sdd`. Un projet sans ce champ est en mode simple :
> rien ici ne s'applique à lui.

## Le problème traité, et lui seul

L'orchestrateur perd de vue la mission et le prochain objectif fonctionnel. Symptôme mesuré
(portfolio-tracker) : laissé à « où en est-on dans la spec, quelle est la prochaine étape »,
il s'enlise dans les bugs — **chaque bug est une prochaine étape légitime**, la dérive est
invisible de l'intérieur. Remède observé : « liste les étapes restantes pour arriver à
*{capacité utilisateur}* » — il reprend de la hauteur et reconstruit un sous-plan cohérent.

Trois logiques, et ce qui les porte :

| Logique | Ce qui la porte |
|---|---|
| La mission est une **valeur pour l'utilisateur**, qui guide à court et long terme | `MISSION.md` — valeur + **modèle de référence** |
| Cette valeur se traduit en **principes** qui tranchent les arbitrages | `MISSION.md` — 3 à 5 principes ordonnés ; `JURISPRUDENCE.md` |
| Il faut **rappeler** la mission et le prochain objectif fonctionnel | `CAP.md` + procédure de **recentrage** (replanification à rebours) |

Plus : la gestion d'un changement en cours de route (`procedures/changement.md`).

## Le modèle de référence — la pièce maîtresse

Un principe abstrait (« fiabilité ») ne tranche rien au moment où il faut. Un **modèle de
référence** — « agir comme le ferait un fonds d'investissement » — **génère** la réponse à
une question que personne n'a prévue : *que ferait un comité ?* Il sert deux fois :
- **arbitrer** : il est le principe P0, au-dessus des autres ;
- **trouver seul les axes d'amélioration** : « que fait le modèle de référence que notre
  système ne fait pas encore ? » — source cadrée de capacités futures (et entrée du
  diagnostic 360°, `CONTROL_SYSTEM.md` §4).

S'il n'en existe pas, `MISSION.md` le dit : les arbitrages seront plus fragiles, la
jurisprudence grossira plus vite.

## Les quatre pièces d'un projet SDD

```
projects/<p>/
  00-REPRISE.md      frontmatter ci-dessous + journal de lots en pied (inchangé sinon)
  MISSION.md         une page — lue au recentrage, à l'arbitrage, au changement
  CAP.md             ≤ 15 lignes — lu au DÉMARRAGE de chaque session, réécrit par le recentrage
  JURISPRUDENCE.md   arbitrages tranchés, chacun citant un principe — lu par grep, jamais en entier
```

Les **jalons** ne sont pas un fichier de plus : ce sont les capacités de la roadmap figée
(`roadmap/<nom>.md`, `CONTROL_SYSTEM.md` §1), auxquelles on ajoute pour chacune :
- `Scénario` : la démonstration que tu fais pour valider (ce que l'utilisateur voit/fait) ;
- `Sert` : l'élément de mission ou le principe servi.

### Frontmatter de `00-REPRISE.md`

```yaml
mode: sdd                 # absent = simple
niveau: N1
active_le: 2026-..-..     # date + raison de la dernière décision (prise par l'utilisateur seul)
raison: ...
jalon_actif: roadmap/<nom>.md#<n>
```

**Différence clé avec le mode simple** : en SDD, le `00-REPRISE.md` ne stocke **pas** « la
prochaine étape ». Il stocke le jalon actif ; les étapes sont **recalculées** à rebours à
chaque recentrage (`CAP.md`). C'est le levier principal.

### Journal de lots (pied de `00-REPRISE.md`)

```
## Journal de lots
| date | exécutant | jalon | avancé ? | note (≤ 1 ligne) |
```

Une ligne par lot. Il alimente le coupe-circuit du recentrage. Il remplace la mesure formelle :
c'est sur lui que l'utilisateur se fait un avis sur l'utilité du mode.

### Une ligne dans le `CLAUDE.md` du projet

```
> **Mode SDD (N1)** — au démarrage, lis `CAP.md` puis applique
> `_governance/sdd/procedures/recentrage.md`. Arbitrage : `MISSION.md` puis `grep` dans
> `JURISPRUDENCE.md`. Changement de mission/jalon/spec : `_governance/sdd/procedures/changement.md`.
```

Coût en contexte au démarrage : cette ligne + `CAP.md` ≈ **400 tokens**, sur ce projet seul.

## Activer un projet

1. **Proposition argumentée** par l'agent ; **décision de l'utilisateur** consignée dans le frontmatter.
2. **Adoption** — extraire de la spec / du `CLAUDE.md` / de la pratique ce qui relève de la
   valeur, du modèle de référence et des principes. **Rien qui n'y figure pas** : une lacune
   devient une question posée à l'utilisateur, jamais un complément de l'agent.
3. Brouillon de `MISSION.md` (gabarit `templates/MISSION.md`) + 5 dilemmes → co-écriture.
4. **Test d'arbitrage** (`procedures/test-arbitrage.md`) : la mission est prête quand un
   relecteur neuf tranche les dilemmes comme l'utilisateur.
5. Ajouter `Scénario` / `Sert` aux capacités de la roadmap active, choisir le jalon actif.
6. Premier recentrage → `CAP.md`. Ajouter la ligne au `CLAUDE.md` du projet.

**Désactiver** : retirer `mode: sdd` et la ligne du `CLAUDE.md`. Les fichiers restent comme
documents de référence ; aucun code supprimé.

## Ce qui n'est pas ici, et où le trouver

Idées écartées pour la version légère (hooks, gates, verrou, N2/N3, multi-fournisseurs) :
`REFLEXION.md`. Prompts d'origine et référence N2/N3 : `reference/` (ne lire `n2-n3.md`
qu'à la première activation de N2).
