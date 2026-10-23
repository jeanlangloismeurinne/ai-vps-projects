#!/usr/bin/env bash
# TEST NÉGATIF de `check_architecte.py` (lot M3 / M3 bis, roadmap V3 `12-lot-M3-architecte.md` /
# `13-lot-M3bis-structure.md`) — sur le harnais existant (`_negatif.sh`, détenteur unique, #65).
#
#   bash checks/negatif_architecte.sh
#
# SATISFIABILITÉ — le check non muté est VERT (mesuré avant toute mutation). DISCRIMINATION — une
# mutation par règle ([S1]-[S11], la porte, l'interrupteur, le renvoi, la réplicabilité), et c'est
# l'assert VISÉ qui rougit. Chaque motif de mutation est une SOUS-CHAÎNE D'UNE SEULE LIGNE, unique
# dans le fichier muté (le harnais ne convertit `\n` que dans le REMPLAÇANT, jamais dans le motif
# cherché — un motif multi-ligne sort en MUTATION CADUQUE, cf. l'en-tête de `_negatif.sh`).
#
# ⚠️ Couverture partielle assumée (temps de la session) : les 7 lignes du tableau de la porte §3.1
# sont gardées par LA MÊME boucle `for … in cas_porte` dans le check — une mutation sur UNE branche
# de `_diagnostic` fait rougir TOUTES les lignes de cette branche à la fois, ce qui n'est pas un
# faux vert (la garde est bien PARTAGÉE, #46) ; chaque branche a néanmoins sa propre mutation.
#
# [S12] (maturité ≠ origine, cause ⑤) n'a PAS de mutation ici : c'est un invariant d'UN SEUL objet
# (#37), posé dans le contrat (`BlocPropose`) et gardé par `negatif_modele_entreprise.sh`.
#
# Lot M3 ter (`15-lot-M3ter-architecte.md`) : [S13] (un bloc non plateforme couvre UN SEUL
# programme) est, comme [S12], un invariant d'UN SEUL objet posé dans le CONTRAT
# (`app/contracts/modele_entreprise_schema.py`) — mais son assert de test ne vit que dans
# `check_architecte.py` (§10), jamais dans `check_modele_entreprise.py` : sa mutation vit donc ICI
# (« une garde déléguée se mute chez son détenteur » appliqué à l'ASSERT, pas seulement au code).
# [S14]/[S15] (structure.py) et le refus NOMMÉ à l'assemblage (§3, architecte.py), le rappel de la
# liste des pièces citables dans [S6] (structure.py) et les périodes attendues de [P4]
# (referentiel.py) suivent le même geste.
set -u
cd "$(dirname "$0")/.." || exit 1

S="app/modele_entreprise/structure.py"
P="app/modele_entreprise/porte.py"
PE="app/modele_entreprise/periodes.py"
A="app/modele_entreprise/architecte.py"
F="app/modele_entreprise/faits_publies.py"
D="app/modele_entreprise/dimensions.py"
C="app/contracts/modele_entreprise_schema.py"
R="app/modele_entreprise/referentiel.py"
T="tools/architecte.py"

CHECK="checks/check_architecte.py"
NET=none

mutations=(
  # ── [S1]-[S9] (structure.py) — chaque motif cible la CONDITION, jamais le `if` qui la partage ──
  "$S¦        if manquants:¦        if False:¦[S1] — membre inventé refusé"
  "$F¦    if len(set(parents.values())) > 1:¦    if False:¦regroupement"
  "$S¦    couvrantes_ant = [p for p, ms in par_periode_ant.items() if membres_vises <= ms]¦    couvrantes_ant = [p for p, ms in par_periode_ant.items() if True]¦[S2] — découpage mixte refusé"
  # Lot P1 : suivre le découpage ANTÉRIEUR n'est plus reconnu — l'architecture du 10-K serait refusée
  # au lieu d'être signalée au comité ([S3b]).
  "$S¦    elif couvrantes_ant:¦    elif False:¦[S3b] — signal"
  # Lot P1, garde (iii) : la période de référence n'est plus l'EXERCICE annuel de référence — un
  # cumul ou des douze mois calculés la remplaceraient.
  "$S¦        reference = annuelle if annuelle in couvrantes_ref else max(couvrantes_ref, key=_cle_tri_periode)¦        reference = max(couvrantes_ref, key=_cle_tri_periode)¦[S2] — période de référence = l'EXERCICE"
  "$S¦    if len(axes) > 1:¦    if False:¦[S3] — un seul axe au premier niveau"
  "$S¦b.rattachement.ligne not in famille.lignes_du_business_plan¦False¦[S4] — bloc agrege hors du business plan refusé"
  "$S¦parent.role == \"commun\"¦False¦[S4] — bloc parent rattaché à un bloc commun refusé"
  "$S¦b.role != \"commun\" and b.maille != \"estime\"¦False¦[S5] — un bloc"
  "$S¦p not in matiere.pieces_citables¦False¦[S6] — pièce hors du dossier refusée"
  "$S¦if passage is None:¦if False:¦[S7] — aucune formule ne porte la ligne chiffre_affaires, refusé"
  "$S¦if noms != attendus:¦if False:¦[S7] — bloc oublié dans l'agrégé refusé"
  "$S¦if bloc_id in annonces:¦if False:¦[S8] — extension annoncée comptée"
  "$S¦p not in periodes_classeur¦False¦[S9] — période hors du classeur refusée"
  "$S¦manquantes = set(matiere.periodes_projetees) - couvertes¦manquantes = set()¦[S9] — période projetée non couverte refusée"

  # ── [S10]/[S11] (lot M3 bis, cause ①/④) ───────────────────────────────────────────────────────
  "$S¦    if oublies:¦    if False:¦[S10] — axe \`secteurs\` sans bloc publié"
  "$S¦        if dim != dim_attendue or not math.isclose(echelle, m_attendu.echelle, rel_tol=1e-9):¦        if False:¦[S11] — produit volume × prix_moyen SANS"
  "$D¦            if g.dimension != d.dimension or not _meme_echelle(g.echelle, d.echelle):¦            if False:¦[S11] — somme M\$ + % refusée"
  "$D¦        if resultat.periode != attendu:¦        if False:¦[S11] — une variable \`exercice\` (taille_du_marche) sur une ligne \`instant\`"
  "$D¦    if a == b:¦    if False:¦[S11] — produit volume × prix_moyen AVEC"
  "$D¦    return any(math.isclose(v, c, rel_tol=1e-9) for c in conversions)¦    return True¦[S11] — coefficients \`* 0.9\` et \`/ 2\`"
  "$D¦    return any(math.isclose(v, c, rel_tol=1e-9) for c in conversions)¦    return False¦[S11] — M\$ × % ramené par"

  # ── La porte (porte.py) ───────────────────────────────────────────────────────────────────────
  "$P¦    if applicable is None:¦    if False:¦émetteur non classé"
  "$P¦    if manque.nature == \"sans_reponse\":¦    if False:¦sans_reponse, toute cause"
  "$P¦    if manque.nature == \"rouverte_comite\":¦    if False:¦rouverte_comite"
  "$P¦échec technique : relancer avant de dessiner¦tout va bien, rien a signaler¦non_fondee, source_indisponible"

  # ── L'interrupteur `porte_admet_reponses_refusees` (arbitrage du 2026-10-22) ────────────────────
  "$P¦if ref.porte_admet_reponses_refusees:¦if not ref.porte_admet_reponses_refusees:¦interrupteur"

  # ── Les périodes (periodes.py) ──────────────────────────────────────────────────────────────
  "$PE¦vus[fy] != p[\"fin\"]¦False¦collision de deux exercices"

  # ── Le renvoi (architecte.py) — la PREMIÈRE occurrence de `if not tient:` (4 espaces, avant le
  # renvoi) ; `replace(..., 1)` prend le match le plus à GAUCHE dans le fichier, donc celui-ci,
  # même si la chaîne de 4 espaces est aussi une sous-chaîne de la seconde occurrence (8 espaces,
  # après le renvoi) plus bas dans le fichier. ─────────────────────────────────────────────────
  "$A¦    if not tient:¦    if False:¦renvoi — sortie refusée puis valide"

  # ── Réplicabilité (§9 du check — grep des `app/modele_entreprise/*.py` livrés) ─────────────────
  "$A¦__all__ = [¦_TICKER_DE_TEST = \"NVDA\"\n__all__ = [¦réplicabilité"

  # ── Lot M3 ter (§10 du check) — [S13]-[S15], §3 (jamais de plantage), [S6]/[P4] enrichis ───────
  "$C¦                if len(self.programmes) != 1:¦                if False:¦deux programmes sur un bloc non plateforme devait être refusé"
  "$S¦            absents = sorted({n for n in noms_a_verifier if _forme_comparable(n) not in verbatim})¦            absents = sorted({n for n in noms_a_verifier if False})¦programme absent du verbatim de \`me_7\` refusé"
  "$S¦    if n < int(attendu):¦    if False:¦inventaire (6) < chiffre clé (8) de \`me_7\` refusé"
  "$A¦        except ValidationError as e:¦        except ZeroDivisionError as e:¦PLANTAGE au lieu d'un refus nommé"
  "$S¦                    f\"{sorted(matiere.pieces_citables)}\")¦                    \"\")¦rappelle la liste exacte des pièces citables"
  "$R¦            attendu = (f\" ; périodes attendues : {list(periodes_projetees)}\" if periodes_projetees else \"\")¦            attendu = \"\"¦message de renvoi NOMME les périodes attendues"
  # Ajouts du 2026-10-23 (relecture Opus) — branches de [S14] sans mutation, refus [CONTRAT].
  "$S¦        if attendu is not None and bloc.statut != attendu:¦        if False:¦\`rattache\` vers un bloc qui n'est pas \`metier_actuel\` refusé"
  "$S¦        if b.statut == \"en_developpement\" and not b.plateforme and b.id not in couverts:¦        if False:¦bloc \`en_developpement\` absent de l'inventaire refusé"
  "$S¦                          f\"{_REGLE_DU_TRAITEMENT[item.traitement]}\")¦                          \"\")¦dit la RÈGLE"
  "$S¦    return \" \".join(texte.split()).casefold()¦    return texte¦casse et espaces différents : admis"
  "$S¦                              f\"le verbatim de \`me_7\` — {_CONSIGNE_NOM_LITTERAL}\")¦                              \"le verbatim\")¦passage continu"
  "$T¦membres={b.rattachement.membres})¦membres={b.rattachement.membre})¦rendu de l'outil — exemple du prompt"
  "$S¦        if item.traitement == \"bloc\" and (bloc.plateforme or¦        if False and (bloc.plateforme or¦pas SA ligne propre, refusé"
  "$S¦    non_nommes = sum(b.nombre_de_programmes_non_nommes or 0 for b in arch.blocs if b.plateforme)¦    non_nommes = 0¦la plateforme couvre l'écart"
  "$A¦    except AgentOutputInvalid as e:¦    except ZeroDivisionError as e:¦sortie hors contrat : PLANTAGE"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
