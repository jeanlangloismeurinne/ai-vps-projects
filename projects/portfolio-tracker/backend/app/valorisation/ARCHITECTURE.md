# `valorisation/` — l'atelier de valorisation

> **Cible** (spec : `roadmap/V3/03-spec-frameworks.md` §4.6, roadmap `05-frameworks-complets.md`
> capacité 4 bis, convention #96 du `CLAUDE.md` projet).
> **Réalisé** : prouvé par les `check_*.py` cités ci-dessous — les exécuter.

## Rôle

Le framework « Valorisation » (`va_1`…`va_6`) pose les questions ; ce module fait les CALCULS, hors
du modèle de langage (arbitrage du 2026-09-28 : un calcul fait par le modèle varie d'un passage à
l'autre). Deux étages, comme dans un vrai fonds :

- **`calculs.py` — les gabarits maison** : valeur sans croissance, actualisation, Gordon, DCF,
  croissance implicite dans le prix, valeur pondérée par probabilité de succès, passage à la valeur
  par action diluée, marge de sécurité, fourchette ordonnée. Fonctions pures, fermées, qui REFUSENT
  leur hors-domaine (`ErreurCalcul`) au lieu de rendre un nombre plausible et faux. `CATALOGUE` est
  le détenteur unique de ce qu'une mécanique d'entreprise peut appeler.
- **`bac_a_calcul.py` — le bac à calcul** : exécute la MÉCANIQUE propre à une entreprise (somme des
  programmes pour une biotech, segments pour NVDA…) écrite par l'agent, sur le TABLEAU D'HYPOTHÈSES
  que le comité a signé. Interpréteur d'un sous-ensemble de Python : rien n'est confié à `eval`, liste
  blanche de constructions, pas d'attribut, budget d'opérations, tailles bornées. **C'est une
  frontière de sécurité** : la mécanique vient d'un agent qui a lu du web.

- **`modele.py` — le modèle d'une entreprise** (#97) : le contrat `contracts/modele_valorisation_schema.py`
  porte ce que l'agent PROPOSE et que le comité SIGNE — méthodologie décrite, segments, tableau
  d'hypothèses (trois origines : pièce, réponse reprise, jugement ancré sur un taux de base sourcé),
  forme de la fourchette (scénarios nommés pour une incertitude continue, arbre d'événements
  probabilisé pour une incertitude binaire), mécanique. Le pont `valider_pont_modele` le confronte au
  dossier et à l'exécution ([A] réponse reprise acquittée, [B] pièces au dossier, [C] exécution et
  `valeur_action`, [D] chaque ligne du tableau est lue, [E] fourchette ordonnée) ; `evaluer_modele`
  rend bas/central/haut (et, pour un arbre, chaque événement en échec et en succès), sans modèle.

## Ajouter un gabarit maison — le contrat

Une fonction publique dans `calculs.py`, ajoutée à `CATALOGUE`, qui refuse son hors-domaine avec un
motif lisible par le comité ; ses valeurs de référence **calculées à la main** dans le check (jamais
en rappelant la fonction) et une mutation « formule fausse mais plausible » dans le test négatif.
Un gabarit itératif déclare son coût dans `_COUT_APPEL` du bac.

- **`signature.py` — la signature et les registres** (#98, migration 051) : l'analyste (ou un membre du
  comité) PROPOSE une version ; le comité la SIGNE ou l'ÉCARTE, motif écrit, et le procès-verbal garde
  la fourchette qu'il avait sous les yeux. Deux registres append-only (`modeles_valorisation`,
  `modeles_valorisation_decisions`, une décision par version). `servir_atelier` (pur) rejoue tout contre
  le dossier du jour : la dernière proposition non décidée est en attente (une plus récente remplace
  celle qui attendait), la signée reste affichée tant qu'une autre n'est pas signée, un modèle signé qui
  ne tient plus est « à revoir » avec son motif. Le dossier du jour = les réponses REPRENABLES
  (`reponses_reprenables` : qui tiennent aujourd'hui selon `parcours.reponse_tient` et portent un
  chiffre) et les pièces courantes. Endpoints : `api/valorisation_v2.py`.

## Pas encore construit (capacité 4 bis, suite)

L'agent qui écrit le modèle (et donc le geste « proposer » exposé), l'écran de l'atelier, la reprise
AUTOMATIQUE d'une réponse remplacée (aujourd'hui un modèle qui cite une réponse remplacée passe « à
revoir »), la réponse à plusieurs nombres, le recalcul de `va_4`-`va_6` au cours du jour.

## Cible → garde (réalisé)

| Invariant cible | Garant |
|---|---|
| Les gabarits rendent les valeurs calculées à la main et refusent leur hors-domaine | `check_bac_a_calcul.py` §1-§2 + `negatif_bac_a_calcul.sh` |
| Deux mécaniques d'entreprise différentes s'exécutent ; changer une hypothèse recalcule sans modèle ; au cours du jour, la marge change et la fourchette non | `check_bac_a_calcul.py` §3 |
| Le tableau signé est intouchable (nom, alias, variable de boucle) | `check_bac_a_calcul.py` §4 + `negatif_bac_a_calcul.sh` |
| Toute mécanique hostile sort en `ErreurCalcul` nommée, en temps borné, jamais en succès ni en autre exception | `check_bac_a_calcul.py` §5 + `negatif_bac_a_calcul.sh` |
| Pas d'`eval`/`exec`/`__import__`, imports déclarés, catalogue = gabarits publics | `check_bac_a_calcul.py` §6 + `negatif_bac_a_calcul.sh` |
| Contrat du modèle : cohérence interne (segments chiffrés, scénarios bien formés, probabilités, jugement ancré) | `check_modele_valorisation.py` §1 + `negatif_modele_valorisation.sh` |
| Pont du modèle [A]-[E] et évaluation (arbre : bas = tous échouent, haut = tous réussissent, détail par événement ; scénarios : le central est le tableau) | `check_modele_valorisation.py` §2-§3 + `negatif_modele_valorisation.sh` |
| Signature : signer ⟺ fourchette au PV ; en attente = dernière proposée non décidée ; la signée reste affichée ; « à revoir » nommé ; écart ligne à ligne ; réponses reprenables = qui tiennent ET chiffrées | `check_signature_modele.py` + `negatif_signature_modele.sh` |
| Les registres s'écrivent et se relisent à l'identique ; refus nommés (version décidée, remplacée, inconnue, dossier qui ne tient plus) ; aucune réponse reprise sur une question que l'alerte dit manquante ; append-only | `check_signature_modele_persist.py` (vraie base, ROLLBACK) + `negatif_051.sh` |
