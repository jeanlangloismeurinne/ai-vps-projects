#!/usr/bin/env bash
# TEST NÉGATIF de `check_dossier.py` — BIDIRECTIONNEL, une mutation par SECTION de garde.
#
#   0. SATISFIABILITÉ — le check non muté est vert. Sans ça, rien de ce qui suit ne prouve quoi que
#      ce soit : un check déjà rouge « détecte » toutes les mutations sans en garder aucune
#      (`feedback_acceptation_rouge_bidirectionnelle`).
#   puis une MUTATION PAR GARDE, chacune exigeant : (1) exit ≠ 0, (2) le FAIL sur l'assert NOMMÉ,
#   (3) la ligne de bilan atteinte. La boucle vit dans `_negatif.sh` (détenteur unique, #65).
#
#   bash checks/negatif_dossier.sh
#
# CE QUI SE JOUE. Le défaut que ce module ferme ne se voit à AUCUN décompte : l'assemblage fautif
# rendait un dossier bien formé, de la bonne taille, une pièce par point — et servait la pièce la
# plus ANCIENNE. Les trois mutations d'ordre (§2, §3, §4) sont donc le cœur de ce fichier : elles
# vérifient que la clef de tri est éprouvée sur ses TROIS composantes (le drapeau « non datée », le
# signe de la date, le signe de l'id), et pas seulement sur le fait qu'elle trie.
#
# ⚠️ POURQUOI LA MUTATION §1 « STUBBE » UNE ENTRY plutôt que de retirer le `continue`. Retirer sec
# la garde du lien mort fait lever un `KeyError` dans `_rang(entries[i])` : le script MOURRAIT avant
# son bilan — tout aussi rouge, mais par un autre canal, et la boucle classe ça en échec (2ᵉ faux
# vert). La mutation reproduit donc le vrai défaut redouté : le refactor « défensif » qui TOLÈRE un
# lien mort en lui fabriquant une pièce vide. C'est ce cas-là qui ouvrirait une chemise que rien ne
# fonde, et qui se lirait « point instruit ».
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_dossier.py"
SRC="app/agents/v2/dossier.py"
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')

base=$(docker run --rm --network none -v "$PWD:/app:ro" \
        -w /app -e PYTHONPATH=/app --env-file checks/env.checks "$IMG" python "$CHECK" 2>&1)
base_rc=$?
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation : rien ne peut être prouvé"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5
  exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$base" | grep -E 'vérifications OK')"

# fichier ¦ motif remplacé ¦ remplaçant ¦ fragment de LABEL qui doit rougir
mutations=(
# ── §1 regroupement — un lien mort ne fabrique pas un point instruit ───────────────────────────────
"$SRC¦        if entry_id not in entries:¦        entries = {**entries, entry_id: entries.get(entry_id, {\"id\": entry_id, \"source_date\": None})}\n        if entry_id not in entries:¦n'ouvre PAS de chemise vide"
# ── §2 ordre, 3ᵉ composante — à date égale, le départage par id n'est plus déterministe ────────────
"$SRC¦-int(entry[\"id\"]))¦int(entry[\"id\"]))¦l'id le plus haut d'abord"
# ── §3 ordre, 2ᵉ composante — LE défaut d'origine : la clef trie croissant, la plus vieille élue ───
"$SRC¦-d.toordinal() if d is not None else 0¦d.toordinal() if d is not None else 0¦AUCUNE antérieure n'est plus récente"
# ── §4 ordre, 1ʳᵉ composante — une pièce non datée prétend être la plus fraîche ────────────────────
"$SRC¦(0 if d is not None else 1,¦(1 if d is not None else 0,¦passe devant #999"
# ── §5 le plafond mord sur les pièces en vigueur au lieu du reste ──────────────────────────────────
"$SRC¦    retenues = list(dict.fromkeys([*en_vigueur, *hors_index_retenues]))¦    retenues = list(dict.fromkeys([*en_vigueur, *hors_index_retenues]))[:plafond]¦plafond sous le nombre de pièces en vigueur"
# ── §5bis une pièce qui sert DEUX points consomme deux places du plafond ───────────────────────────
"$SRC¦    en_vigueur: list[int] = list(dict.fromkeys(c.en_vigueur for c in chemises))¦    en_vigueur: list[int] = [c.en_vigueur for c in chemises]¦ne consomme qu'une place du plafond"
# ── §6 les pièces hors index sont écartées au lieu d'être jointes ──────────────────────────────────
"$SRC¦    retenues = list(dict.fromkeys([*en_vigueur, *hors_index_retenues]))¦    retenues = list(dict.fromkeys([*en_vigueur]))¦hors index sont dans le dossier"
# ── §7 le décompte des antérieures compte deux fois une pièce partagée ─────────────────────────────
"$SRC¦        return tuple(sorted({i for ch in self.chemises for i in ch.anterieures}))¦        return tuple(sorted([i for ch in self.chemises for i in ch.anterieures]))¦elle ne compte qu'une fois"
# ── §8 l'indéterminable se lit « rien à signaler » (#25/#44) ───────────────────────────────────────
"$SRC¦        return bool(self.collecte)¦        return True¦un tuple vide ne doit pas se lire"
# ── §9 un plafond nul rend un dossier vide au lieu de lever ────────────────────────────────────────
"$SRC¦    if plafond < 1:¦    if False:¦plafond=0 doit LEVER"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
