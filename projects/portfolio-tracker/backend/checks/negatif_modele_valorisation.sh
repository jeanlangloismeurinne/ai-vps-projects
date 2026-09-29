#!/usr/bin/env bash
# TEST NÉGATIF de `check_modele_valorisation.py` (#97) — BIDIRECTIONNEL.
#
#   bash checks/negatif_modele_valorisation.sh
#
# SATISFIABILITÉ — le check non muté est VERT : **51 vérifications OK, 0 échec** (mesuré avant toute
# mutation). DISCRIMINATION — une mutation par garde, et c'est l'assert VISÉ qui rougit.
#
# ⚠️ LES MUTATIONS QUI COMPTENT VRAIMENT : [D] (une ligne du tableau que le calcul ignore — le comité
# la croirait décisive) et l'évaluation de l'arbre (un « bas » qui ne serait pas « tous échouent »
# ferait lire au comité un pire cas qui n'en est pas un). Toutes rendent un modèle FAUX et plausible.
#
# Une garde a été FUSIONNÉE à l'écriture parce qu'aucune mutation ne pouvait la faire rougir : « la
# réponse reprise n'est pas acquittée » était subsumée par « elle répond à une autre question »
# (None ≠ qf_1). Une seule comparaison, deux motifs — et les asserts du pont lisent le MOTIF.
set -u
cd "$(dirname "$0")/.." || exit 1

M="app/valorisation/modele.py"
S="app/contracts/modele_valorisation_schema.py"

CHECK="checks/check_modele_valorisation.py"
NET=none

mutations=(
  # ── Le pont ────────────────────────────────────────────────────────────────────────────────
  "$M¦    if modele.ticker_id != ticker_id:¦    if False:¦modèle d'un autre titre"
  "$M¦            if qid != o.question_id:   # une seule comparaison : « absente » est le cas qid = None¦            if qid is not None and qid != o.question_id:¦réponse reprise non acquittée"
  "$M¦            if qid != o.question_id:   # une seule comparaison : « absente » est le cas qid = None¦            if qid is None:¦réponse reprise d'une autre question"
  "$M¦        if hors:¦        if False:¦pièce hors dossier"
  "$M¦        return [r.entry_id for r in o.taux_de_base.source_entry_refs]¦        return []¦taux de base hors dossier"
  "$M¦    if isinstance(v, bool) or not isinstance(v, (int, float)):¦    if v is None:¦sortie non numérique"
  "$M¦                if (h.segment is None and h.nom not in noms)¦                if False¦hypothèse globale ignorée"
  "$M¦                or (h.segment is not None and (h.nom not in textes or NOM_RESERVE_SEGMENTS not in noms))]¦                or False]¦hypothèse de segment ignorée"
  "$M¦    if not ev.bas <= ev.central <= ev.haut:¦    if False:¦scénarios croisés"

  # ── L'évaluation ───────────────────────────────────────────────────────────────────────────
  "$M¦        bas, n = _executer(modele, {e.probabilite: 0.0 for e in f.evenements}, \"bas (tous les événements échouent)\")¦        bas, n = _executer(modele, {f.evenements[0].probabilite: 0.0}, \"bas\")¦arbre : bas = tous les événements échouent"
  "$M¦        haut, n = _executer(modele, {e.probabilite: 1.0 for e in f.evenements}, \"haut (tous les événements réussissent)\")¦        haut, n = _executer(modele, {}, \"haut\")¦arbre : haut = tous réussissent"
  "$M¦            echec, n1 = _executer(modele, {e.probabilite: 0.0}, f\"\`{e.id}\` en échec\")¦            echec, n1 = _executer(modele, {x.probabilite: 0.0 for x in f.evenements}, \"échec\")¦A en échec / en succès, B à sa probabilité"
  "$M¦        valeurs[s.role], n = _executer(modele, s.valeurs, f\"scénario {s.role}\")¦        valeurs[s.role], n = _executer(modele, {}, f\"scénario {s.role}\")¦scénarios : bas = ses deux hypothèses modifiées"
  "$M¦        v = surcharges.get(cle_hypothese(h), h.valeur)¦        v = surcharges.get(h.nom, h.valeur)¦scénarios : bas = ses deux hypothèses modifiées"

  # ── Le contrat ─────────────────────────────────────────────────────────────────────────────
  "$S¦        if roles != [\"bas\", \"central\", \"haut\"]:¦        if False:¦rôle manquant"
  "$S¦            if s.role == \"central\" and s.valeurs:¦            if False:¦central qui modifie le tableau"
  "$S¦            if s.role != \"central\" and not s.valeurs:¦            if False:¦scénario haut sans hypothèse"
  "$S¦        if len(set(ids_segments)) != len(ids_segments):¦        if False:¦segments en double"
  "$S¦        if doublons:¦        if False:¦hypothèse en double"
  "$S¦            if h.segment is None and h.nom == NOM_RESERVE_SEGMENTS:¦            if False:¦nom réservé"
  "$S¦            if h.segment is not None and h.segment not in ids_segments:¦            if False:¦segment non déclaré"
  "$S¦        if orphelins:¦        if False:¦segment de façade"
  "$S¦                if inconnues:¦                if False:¦scénario sur hypothèse inconnue"
  "$S¦            if len(set(ids)) != len(ids):¦            if False:¦deux événements, même identifiant"
  "$S¦            if len(set(portees)) != len(portees):¦            if False:¦deux événements, une probabilité"
  "$S¦                if h is None:¦                if False:¦probabilité inconnue"
  "$S¦                if not 0.0 <= h.valeur <= 1.0:¦                if False:¦probabilité hors [0,1]"
  "$S¦    ecart_justifie: Annotated[str, Field(min_length=30)]¦    ecart_justifie: str¦jugement sans écart justifié"
  "$S¦    methodologie: Annotated[str, Field(min_length=80)]¦    methodologie: str¦méthodologie non décrite"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
