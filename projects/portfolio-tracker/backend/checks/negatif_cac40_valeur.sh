#!/usr/bin/env bash
# TEST NÉGATIF de `check_cac40_valeur.py` — une mutation par règle, et c'est l'assert VISÉ qui rougit.
#
#   bash checks/negatif_cac40_valeur.sh
#
# SATISFIABILITÉ mesurée avant toute mutation : 34 ok / 0 FAIL (2026-11-22).
# ⚠️ LES MUTATIONS QUI COMPTENT : n°6 et n°7 (divisions d'actions par date de publication du DÉPÔT : Air Liquide,
# cas réel) et n°19 (filtre par marché : sans lui, le CAC 40 entre dans la page Nasdaq et dans ses badges).
# Non gardé : l'exclusion des faits à dimension dans `esef_eps` — aucun dépôt lu n'en porte sur le BPA.
set -u
cd "$(dirname "$0")/.." || exit 1

EU="app/nasdaq/europe.py"
VA="app/nasdaq/valeur.py"
CHECK="checks/check_cac40_valeur.py"
NET=none

mutations=(
  "$EU¦        end = (pd.Timestamp(b) - pd.Timedelta(days=1)).strftime(\"%Y-%m-%d\")¦        end = (pd.Timestamp(b) - pd.Timedelta(days=0)).strftime(\"%Y-%m-%d\")¦ESEF : la fin xBRL-JSON est exclusive (« 2025-01-01 » clôt 2024)"
  "$EU¦    return next((by[n] for n in EPS_CONCEPTS if n in by), {})¦    return next((by[n] for n in reversed(EPS_CONCEPTS) if n in by), {})¦ESEF : le BPA dilué passe avant le BPA de base (LVMH 2024 : 25,12 et non 25,13)"
  "$EU¦EPS_CONCEPTS = (\"DilutedEarningsLossPerShare\", \"BasicEarningsLossPerShare\",¦EPS_CONCEPTS = (\"DilutedEarningsLossPerShare\", \"BasicEarningsLossPerShare\")\n_HORS = (¦ESEF : Bouygues ne déclare que le BPA des activités poursuivies (2024 : 2,80)"
  "$EU¦    return (pd.Period(end[:7], \"M\") + AVAIL_MONTHS).end_time.strftime(\"%Y-%m-%d\")¦    return (pd.Period(end[:7], \"M\") + 0).end_time.strftime(\"%Y-%m-%d\")¦exercice 2024 connu fin avril 2025"
  "$EU¦        pick = cands[0]¦        pick = cands[-1]¦TotalEnergies 2022 : dépôt 2022 en centièmes (0,0785 \$), repris du dépôt 2023 (7,85 \$)"
  "$EU¦    return V.adjust_splits(points, splits)¦    return points¦Air Liquide 2022 : 5,27 € publiés ÷ 1,1² (attributions de 2024 et 2026) = 4,36 € comme Yahoo"
  "$EU¦                                             \"own\": end[:7] == pe[:7], \"filed\": avail_date(pe)})¦                                             \"own\": end[:7] == pe[:7], \"filed\": avail_date(end)})¦Air Liquide 2023, lu au dépôt 2024 (déjà retraité de juin 2024) : ÷ 1,1 seulement = 4,85 € comme Yahoo"
  "$EU¦        if later and scale_error(pick[\"v\"], later[0][\"v\"]):¦        if False:¦TotalEnergies 2022 : dépôt 2022 en centièmes (0,0785 \$), repris du dépôt 2023 (7,85 \$)"
  "$EU¦SCALE = 10¦SCALE = 1.5¦contrôle croisé : hors tolérance, l'analyse est masquée (STMicro 2025, IFRS 0,33 contre US GAAP 0,18)"
  "$EU¦            by[k] = {**y, \"scale\": e[\"v\"]}¦            pass¦Capgemini 2022 : 8 790 000 € par action au dépôt, sans dépôt suivant : Yahoo (8,79 €) le remplace, et la note le dit"
  "$EU¦        if e is None:¦        if True:¦fusion : l'ESEF passe avant Yahoo sur un exercice commun"
  "$EU¦        elif e[\"cur\"] == y[\"cur\"] and abs(y[\"v\"] - e[\"v\"]) > GAP_WARN * max(abs(e[\"v\"]), 1e-9):¦        elif False:¦fusion : un écart de plus de 5 % se signale (ESEF non ajusté 5,72 contre 5,20)"
  "$EU¦    return {\"year\": e[\"end\"][:4], \"ours\": e[\"v\"], \"yahoo\": y[\"v\"], \"currency\": e[\"cur\"], \"ok\": V.eps_check(e[\"v\"], y[\"v\"])}¦    return {\"year\": e[\"end\"][:4], \"ours\": e[\"v\"], \"yahoo\": y[\"v\"], \"currency\": e[\"cur\"], \"ok\": True}¦contrôle croisé : hors tolérance, l'analyse est masquée (STMicro 2025, IFRS 0,33 contre US GAAP 0,18)"
  "$EU¦        return {\"ok\": None}¦        return {\"ok\": False}¦contrôle croisé : sans exercice commun, impossible mais pas masqué (Puma)"
  "$EU¦              and not scale_error(e[\"v\"], ys[e[\"end\"][:7]][\"v\"])]¦              ]¦Capgemini : l'exercice remplacé pour erreur d'échelle n'est pas « contrôlé » (le titre n'est pas masqué)"
  "$EU¦        r = 1.0 if p[\"cur\"] == \"EUR\" else fx(p[\"cur\"], p[\"end\"][:7])¦        r = 1.0¦BPA en dollars converti au change du mois de clôture"
  "$VA¦    return (payload or {}).get(\"market\", \"nasdaq\")¦    return (payload or {}).get(\"market\", \"cac40\")¦une ligne sans marché déclaré est une ligne Nasdaq"
  "$VA¦    return bool(payload) and \"m\" in payload and (payload.get(\"check\") or {}).get(\"ok\") is not False¦    return bool(payload) and (payload.get(\"check\") or {}).get(\"ok\") is not False¦une ligne CAC 40 en échec (marché seul, sans séries) n'est pas affichable"
  "$VA¦    return {t: p for t, p in series.items() if market_of(p) == market}¦    return dict(series)¦la page Nasdaq (et ses badges) ne lit que le Nasdaq, échecs compris"
  "$VA¦         \"periods\": {k: decompose(d, k) if k in mk[\"periods\"] else {\"ok\": False, \"reason\": mk[\"no_history\"]} for k in PERIODS}}¦         \"periods\": {k: decompose(d, k) for k in PERIODS}}¦CAC 40 : « 10 ans » rend « historique insuffisant », pas un départ décalé"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
