#!/usr/bin/env bash
# TEST NÉGATIF de `check_cours_cote.py` (#81) — BIDIRECTIONNEL.
#
#   bash checks/negatif_cours_cote.sh
#
# POURQUOI CE FICHIER EXISTE. Le lot #81 est un lot de correctif : il est donc exactement du genre
# qui s'écrit tout entier sans rien tenir, parce que ses asserts passent sur un code qu'on vient
# d'écrire pour eux. Les deux sens sont donc exigés (`feedback_acceptation_rouge_bidirectionnelle`) :
#   · SATISFIABILITÉ — le check non muté est VERT : **82 vérifications OK, 0 échec** (mesuré avant
#     toute mutation, hors ligne). Sans cette mesure, un check qui rougit toujours passerait pour
#     un check qui discrimine.
#   · DISCRIMINATION — une mutation par critère ci-dessous, et c'est l'assert VISÉ qui rougit.
#
# ⚠️ LES MUTATIONS QUI COMPTENT VRAIMENT sont les n°6 et n°7 : elles REMETTENT le défaut mesuré en
# production le 2026-09-23 (le calcul repart de `hist` au lieu de la série cotée). Si elles
# laissaient le check vert, tout le reste serait du décor — le check ne garderait pas le bug qu'il
# est censé empêcher de revenir.
#
# ⚠️ CE QUE LES MUTATIONS N'ONT PAS LE DROIT DE FAIRE : tuer le script avant son bilan. On ne
# SUPPRIME donc jamais une garde (ce qui ferait lever `fromtimestamp(nan)` ou `iloc[-1]` sur une
# série vide), on lui ajoute un cas d'exception — qui est de toute façon le mode de panne réel.
# C'est pourquoi la mutation 14 rend une date bidon plutôt que de retirer le test `cotee.empty`.
set -u
cd "$(dirname "$0")/.." || exit 1

M1="app/data_collection/m1_quantitative.py"
DS="app/data_collection/data_service.py"
VF="app/knowledge/valuation_feed.py"

CHECK="checks/check_cours_cote.py"
NET=none

mutations=(
  # ── `fini` : le trio d'états ────────────────────────────────────────────────────────────────
  "$M1¦    return f if math.isfinite(f) else None¦    return f¦\`NaN\` → None (le quatrième état muet)"
  "$M1¦    return f if math.isfinite(f) else None¦    return f if math.isfinite(f) and f != 0 else None¦\`0.0\` TRAVERSE"

  # ── `serie_cotee` : le détenteur unique du filtre ───────────────────────────────────────────
  "$M1¦    return hist[hist[\"Close\"].map(lambda c: fini(c) is not None)]¦    return hist¦la séance vide tombe (10 → 9)"
  "$M1¦    return hist[hist[\"Close\"].map(lambda c: fini(c) is not None)]¦    return hist[hist[\"Close\"].map(lambda c: fini(c) is not None)].iloc[::-1]¦les cours restants sont INCHANGÉS et dans l'ORDRE"
  "$M1¦    return hist[hist[\"Close\"].map(lambda c: fini(c) is not None)]¦    return hist[hist[\"Close\"].map(lambda c: c == c)]¦\`±inf\` tombe aussi"

  # ── LE DÉFAUT MESURÉ, REMIS : le calcul repart du cadre au lieu de la série cotée ───────────
  "$M1¦    debut, fin_ = fini(cotee[\"Close\"].iloc[-days]), fini(cotee[\"Close\"].iloc[-1])¦    debut, fin_ = fini(hist[\"Close\"].iloc[-days]), fini(hist[\"Close\"].iloc[-1])¦variation 1m : RENSEIGNÉE malgré la séance manquante"
  "$M1¦    ytd = cotee[cotee.index.year == datetime.now().year]¦    ytd = hist[hist.index.year == datetime.now().year]¦variation ytd : RENSEIGNÉE malgré la séance manquante"

  # ── Le seuil qu'aucune donnée ne pouvait franchir ───────────────────────────────────────────
  "$M1¦    if len(cotee) < minimum:¦    if len(cotee) < 252:¦le calcul sur FENÊTRE, lui, rend un nombre sur la même donnée"
  "$M1¦    if len(cotee) < minimum:¦    if len(cotee) < 0:¦une fenêtre TRONQUÉE (150 séances) reste refusée"
  "$M1¦    debut, fin_ = fini(cotee[\"Close\"].iloc[0]), fini(cotee[\"Close\"].iloc[-1])¦    debut, fin_ = fini(cotee[\"Close\"].iloc[0]) or 1e-9, fini(cotee[\"Close\"].iloc[-1])¦un premier cours à 0 → ABSENT"

  # ── Les deux dates du relevé ────────────────────────────────────────────────────────────────
  "$M1¦        tz = ZoneInfo(info.get(\"exchangeTimezoneName\") or \"UTC\")¦        tz = ZoneInfo(\"UTC\")¦même instant, place de Tokyo → jour suivant"
  "$M1¦        return repli¦        return None¦sans horodatage : repli sur la dernière cotation"
  "$M1¦    if not isinstance(ts, (int, float)) or not math.isfinite(float(ts)):¦    if not isinstance(ts, (int, float)):¦un horodatage non fini retombe sur le repli"
  "$M1¦    return None if cotee.empty else cotee.index[-1].date().isoformat()¦    return \"1970-01-01\" if cotee.empty else cotee.index[-1].date().isoformat()¦série vide → pas de date de marquage"
  # Le motif est volontairement la PREMIÈRE occurrence de `cotee = serie_cotee(hist)` dans le
  # fichier : elle appartient à `_derniere_cotation` (le remplacement ne vise que la 1ʳᵉ).
  "$M1¦    cotee = serie_cotee(hist)¦    cotee = hist¦la date de marquage est celle du dernier cours COTÉ"

  # ── Le filet du DataService ─────────────────────────────────────────────────────────────────
  "$DS¦        if isinstance(obj, float) and not math.isfinite(obj):¦        if False:¦les quatre variations non finies deviennent None"
  "$DS¦        if isinstance(obj, float) and not math.isfinite(obj):¦        if isinstance(obj, float) and not obj:¦\`0.0\` traverse le filet — mesure, pas absence (#44)"
  "$DS¦        if isinstance(obj, dict):¦        if False:¦le filet descend dans les dicts IMBRIQUÉS"
  "$DS¦            return [_net(f\"{prefixe}[{i}]\", v) for i, v in enumerate(obj)]¦            return [_net(f\"{prefixe}[{i}]\", v) for i, v in enumerate(obj)][::-1]¦le filet descend aussi dans les LISTES, sans les réordonner"
  "$DS¦            tombes.append(prefixe)¦            tombes.append(\"un champ\")¦il NOMME le chemin tombé : \`m1.price.ytd_change_pct\`"
  "$DS¦            ticker, len(tombes), \", \".join(sorted(tombes)),¦            ticker, 0, \", \".join(sorted(tombes)),¦l'avertissement DÉNOMBRE les champs tombés (6 ici)"
  "$DS¦    if tombes:¦    if True:¦aucune charge saine ne produit d'avertissement"
  "$DS¦        return _assainir_non_finis(ticker, data)¦        return data¦le filet est POSÉ SUR LA PORTE"

  # ── Le census : découvert, jamais récité ────────────────────────────────────────────────────
  "$M1¦        return fini(df.loc[row_name].iloc[col_idx])¦        return float(df.loc[row_name].iloc[col_idx])¦chacune passe par \`fini\`"
  "$M1¦def _safe_float(df, row_name: str, col_idx: int) -> Optional[float]:¦def _lecteur_clandestin(df):\n    return df[\"Close\"].iloc[-1]\n\n\ndef _safe_float(df, row_name: str, col_idx: int) -> Optional[float]:¦fonctions lisant une cellule de série, découvertes par AST"

  # ── La cascade #79 dans le dossier ──────────────────────────────────────────────────────────
  "$VF¦    for clef in (\"price_as_of\", \"last_close_date\"):¦    for clef in (\"last_close_date\", \"price_as_of\"):¦\`price_as_of\` PRIME"
  "$VF¦            logger.warning(\"valuation_feed : \`%s\` illisible (%r) — ignoré\", clef, brut)¦            return date.today()¦une date illisible est ÉCARTÉE"
  "$VF¦    price = m1.get(\"price\") or {}¦    price = m1.get(\"price\") or {\"price_as_of\": date.today().isoformat()}¦un m1 sans bloc \`price\` rend ABSENT"
  "$VF¦                        datation=constatee(date_du_fait=as_of, date_du_document=date.today()),¦                        datation=constatee(date_du_fait=date.today(), date_du_document=date.today()),¦le FAIT n'est JAMAIS \`date.today()\`"
  "$VF¦    as_of = _date_du_fait(m1) or date.today()¦    as_of = date.today()¦\`as_of\` est PRODUIT par \`_date_du_fait\`"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
