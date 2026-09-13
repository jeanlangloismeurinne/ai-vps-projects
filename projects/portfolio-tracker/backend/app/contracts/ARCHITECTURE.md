# `contracts/` — copies runtime des contrats figés

> **Cible** (spec : `roadmap/V3/03-spec-frameworks.md` §2.4, convention #19/#39).
> **Réalisé** : prouvé par les `check_*.py` cités — les exécuter.

## Rôle

Les contrats Pydantic **matérialisent la garantie G1** (le JSON encode la méthodologie). Ils sont des
**copies runtime FIDÈLES** des cartes figées de `roadmap/V3/provenance-cards/*_schema.py`.

**Pourquoi une copie et non un import** : le contexte de build du backend est `./backend` seul →
`roadmap/` est **hors image**. Les contrats doivent donc vivre dans `app/contracts/`, à l'identique de
la carte figée (seuls les imports diffèrent). La carte figée reste le **détenteur de conception** ;
la copie runtime est ce que le code exécute.

## Faire évoluer un contrat — les 3 points de synchronisation (#19/#39)

Tout changement de structure se répercute **simultanément** sur :
1. la **carte figée** `roadmap/V3/provenance-cards/<x>_schema.py` (conception) ;
2. la **copie runtime** `app/contracts/<x>_schema.py` (exécution) ;
3. l'**exemple JSON du prompt** en DB (`agent_prompts`) — un exemple périmé fait recopier au modèle
   un format obsolète, panne muette invisible hors ligne (#39).

En omettre un crée une désynchronisation silencieuse. `extra="forbid"` sur les contrats d'émission :
un champ périmé fait **rejeter l'entry entière**.

## Cible → garde (réalisé)

| Invariant cible | Garant |
|---|---|
| Copie runtime ≡ carte figée (montée en `/contract_frozen`) | `check_analysis_contract.py`, `check_decision_validate.py`, `check_exit_debate.py`, `check_monitoring_v2.py` |
| Bijection contrat ↔ pixels de la maquette | `check_framework_contract.py` §9 |
| Exemple JSON du prompt synchrone au contrat | `check_fstring_sql.py`, `check_framework_persist.py` (#64) |

⚠️ Le montage `/contract_frozen = roadmap/V3/provenance-cards` est **obligatoire** dans
`checks/run_all.sh` : sans lui, 4 scripts sous-comptent en sortant quand même à 0.
