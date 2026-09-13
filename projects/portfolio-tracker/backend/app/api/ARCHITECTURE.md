# `api/` — surface backend → frontend

> **Cible** (spec : garde-fous G2/G3 de `roadmap/V3/principe-directeur.md`, convention #36).
> **Réalisé** : prouvé par les `check_*_listing.py` et checks de contrat cités — les exécuter.

## Rôle

La **seule** frontière entre le backend et le frontend. Deux espaces disjoints (2026-08-22) : les
routers V1 existants, et les routers **V2** au suffixe `_v2`. Le frontend **va itérer** ; cette couche
est le **contrat stable** sur lequel il s'appuie — il itère sur la *présentation*, jamais sur le contrat.

Routers montés dans `app/main.py` (`include_router`). V2 : `analysis_v2`, `portfolio_v2`,
`monitoring_v2`, `thesis_v2`, `calendar_v2`, `knowledge_v2`.

## Exposer une information au frontend — le contrat

1. **G3 — la décision est indépendante de l'UX.** Une route n'infléchit jamais un verdict ; elle le
   sert. Le frontend peut changer d'affichage sans toucher au backend.
2. **G2 — le corps HTTP ne vaut que par ce qu'il n'expose PAS (#36).** Un contrat de décision
   n'accepte que les **acquittements** et les **faits d'exécution** ; `verdict`, `sizing`, `conditions`,
   `hypotheses` sont **lus en base**, jamais acceptés du client (sinon les garde-fous deviennent
   décoratifs). Les champs dérivés ne sont jamais redemandés.
3. **Un verdict qui dépend d'un ingrédient non stocké se recalcule à la LECTURE.** Ex. le readiness
   dépend de l'actualité (non persistée, #53) : le GET rejoue la moitié déterministe, sans écriture
   (#54, `feedback_controle_au_point_de_lecture`).
4. **Ajouter une exposition** = un router `_v2` + `include_router` dans `main.py` + un
   `check_*_listing.py` qui verrouille la forme lue par le frontend.

## Cible → garde (réalisé)

| Invariant cible | Garant |
|---|---|
| Listings de lecture stables (tickers, thèses, knowledge) | `check_tickers_v2_listing.py`, `check_theses_v2_listing.py`, `check_knowledge_entries_listing.py` |
| Décision contrainte : le corps n'expose que les acquittements (G2) | `check_decision_validate.py` §8 |
| Monitoring : invariants relationnels vérifiés en code, pas dans le schéma | `check_monitoring_v2.py` |
| Readiness recalculé à la lecture | `check_readiness_recompute.py` |

⚠️ Le listing exhaustif des endpoints V1/V0 vit dans `REFERENCE.md` ; `grep` du code fait foi.
