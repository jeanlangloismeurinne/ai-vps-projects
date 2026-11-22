#!/usr/bin/env bash
# TEST NÉGATIF de `check_nasdaq_valeur.py` — une mutation par règle, et c'est l'assert VISÉ qui rougit.
#
#   bash checks/negatif_nasdaq_valeur.sh
#
# SATISFIABILITÉ mesurée avant toute mutation : 26 ok / 0 FAIL (2026-11-22).
# ⚠️ LA MUTATION QUI COMPTE est la n°1 : elle remet le défaut du premier essai (divisions d'actions
# ajustées APRÈS l'addition des quatre trimestres), qui allumait « plancher caduc » chez Apple et Nvidia.
set -u
cd "$(dirname "$0")/.." || exit 1

VA="app/nasdaq/valeur.py"
CHECK="checks/check_nasdaq_valeur.py"
NET=none

mutations=(
  "$VA¦            if d > p[\"filed\"] and r > 0:¦            if d > \"2099\" and r > 0:¦exercice 2025 (4 trimestres de part et d'autre de la division du 2024-06-10) = 2,94 \$"
  "$VA¦        if n and y[\"end\"] not in Q:¦        if False:¦T4 de l'exercice 2025 déduit (2,94 − 2,04)"
  "$VA¦        out.append({\"end\": e4[-1], \"avail\": max(Q[e][0] for e in e4), \"ttm\": sum(Q[e][1] for e in e4)})¦        out.append({\"end\": e4[-1], \"avail\": e4[-1], \"ttm\": sum(Q[e][1] for e in e4)})¦disponible au dépôt du 10-K (2025-02-26), pas à la clôture"
  "$VA¦        while j < len(pts) and pts[j][\"avail\"] <= end:¦        while j < len(pts) and pts[j][\"end\"] <= end:¦janvier 2025 ne voit pas encore l'exercice clos le 26"
  "$VA¦        f[\"mult\"] = (p[n] / e1) / (p[i0] / e0)¦        f[\"mult\"] = (p[n] / e0) / (p[i0] / e1)¦cours₁/cours₀ = inflation × bénéfices réels × multiple"
  "$VA¦        f[\"real\"] = (e1 / e0) / f[\"infl\"]¦        f[\"real\"] = e1 / e0¦cours₁/cours₀ = inflation × bénéfices réels × multiple"
  "$VA¦    f[\"total\"] = f[\"price\"] * f[\"div\"]¦    f[\"total\"] = f[\"price\"]¦rendement total = cours × dividendes"
  "$VA¦            out[\"real\"].append(math.log(e[i] / e0) - li)¦            out[\"real\"].append(math.log(e[i] / e0))¦aire empilée : la somme des couches (logs) retombe sur le cours"
  "$VA¦    while i0 < n - 12 and not (e[i0] is not None and e[i0] > 0):¦    while False:¦perte au départ : départ décalé au premier bénéfice"
  "$VA¦    if e0 is None or e1 is None or e0 <= 0 or e1 <= 0:¦    if e0 is None or e1 is None or e0 <= 0:¦perte aujourd'hui : pas de décomposition, et on dit pourquoi"
  "$VA¦    return (e[i] + e[i - 12] + e[i - 24]) / 3¦    return e[i]¦plancher central = moyenne des états à t, t-12, t-24 × 15"
  "$VA¦        out[\"degraded\"].append(bool(a3[i] is not None and (not ok or (best and real[i] < DEGRADED_BELOW * best))))¦        out[\"degraded\"].append(bool(a3[i] is not None and not ok))¦bénéfices divisés par deux : plancher caduc"
  "$VA¦        out[\"degraded\"].append(bool(a3[i] is not None and (not ok or (best and real[i] < DEGRADED_BELOW * best))))¦        out[\"degraded\"].append(bool(a3[i] is not None and (not ok or (best and real[i] <= best)))) ¦état qui progresse : plancher valide"
  "$VA¦    if i < 24 or e[i] is None or e[i - 12] is None or e[i - 24] is None:¦    if e[i] is None or e[i - 12] is None or e[i - 24] is None:¦avant 24 mois d'historique : pas de plancher"
  "$VA¦                        \"pe_lo\": d[\"p\"][n] / fwd[\"fwd_hi\"] if fwd.get(\"fwd_hi\") and fwd[\"fwd_hi\"] > 0 else None,¦                        \"pe_lo\": d[\"p\"][n] / fwd[\"fwd_lo\"] if fwd.get(\"fwd_lo\") and fwd[\"fwd_lo\"] > 0 else None,¦fourchette : l'analyste le plus optimiste donne le PER le plus bas"
  "$VA¦    return bool(payload) and \"m\" in payload and (payload.get(\"check\") or {}).get(\"ok\") is not False¦    return bool(payload) and \"m\" in payload¦contrôle croisé en défaut : analyse masquée"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
