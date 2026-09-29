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

## Ajouter un gabarit maison — le contrat

Une fonction publique dans `calculs.py`, ajoutée à `CATALOGUE`, qui refuse son hors-domaine avec un
motif lisible par le comité ; ses valeurs de référence **calculées à la main** dans le check (jamais
en rappelant la fonction) et une mutation « formule fausse mais plausible » dans le test négatif.
Un gabarit itératif déclare son coût dans `_COUT_APPEL` du bac.

## Pas encore construit (capacité 4 bis, suite)

Le CONTRAT du modèle d'entreprise (mécanique décrite en prose + tableau d'hypothèses sourcées + code
+ version + signature du comité), sa persistance, l'agent qui l'écrit, la reprise des réponses
acquittées (`qf_1` → `va_1`), la réponse à plusieurs nombres, le recalcul de `va_4`-`va_6` au cours
du jour. Rien n'appelle encore ce module en production.

## Cible → garde (réalisé)

| Invariant cible | Garant |
|---|---|
| Les gabarits rendent les valeurs calculées à la main et refusent leur hors-domaine | `check_bac_a_calcul.py` §1-§2 + `negatif_bac_a_calcul.sh` |
| Deux mécaniques d'entreprise différentes s'exécutent ; changer une hypothèse recalcule sans modèle ; au cours du jour, la marge change et la fourchette non | `check_bac_a_calcul.py` §3 |
| Le tableau signé est intouchable (nom, alias, variable de boucle) | `check_bac_a_calcul.py` §4 + `negatif_bac_a_calcul.sh` |
| Toute mécanique hostile sort en `ErreurCalcul` nommée, en temps borné, jamais en succès ni en autre exception | `check_bac_a_calcul.py` §5 + `negatif_bac_a_calcul.sh` |
| Pas d'`eval`/`exec`/`__import__`, imports déclarés, catalogue = gabarits publics | `check_bac_a_calcul.py` §6 + `negatif_bac_a_calcul.sh` |
