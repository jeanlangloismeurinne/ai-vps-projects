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
M="app/modele_entreprise/matiere.py"

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
  "$S¦                absents.append(n)¦                pass¦programme absent du verbatim de \`me_7\` refusé"
  "$A¦        except ValidationError as e:¦        except ZeroDivisionError as e:¦PLANTAGE au lieu d'un refus nommé"
  "$S¦                    f\"{sorted(matiere.pieces_citables)}\")¦                    \"\")¦rappelle la liste exacte des pièces citables"
  "$R¦            attendu = (f\" ; périodes attendues : {list(periodes_projetees)}\" if periodes_projetees else \"\")¦            attendu = \"\"¦message de renvoi NOMME les périodes attendues"
  # Ajouts du 2026-10-23 (relecture Opus) — branches de [S14] sans mutation, refus [CONTRAT].
  "$S¦        if attendu is not None and bloc.statut != attendu:¦        if False:¦\`rattache\` vers un bloc qui n'est pas \`metier_actuel\` refusé"
  "$S¦        if b.statut == \"en_developpement\" and not b.plateforme and b.id not in couverts:¦        if False:¦bloc \`en_developpement\` absent de l'inventaire refusé"
  "$S¦                          f\"{_REGLE_DU_TRAITEMENT[item.traitement]}\")¦                          \"\")¦dit la RÈGLE"
  "$S¦    return \" \".join(texte.split()).casefold()¦    return texte¦casse et espaces différents : admis"
  "$S¦                              f\"{_CONSIGNE_NOM_LITTERAL}\")¦                              \"\")¦passage continu"
  "$T¦membres={b.rattachement.membres})¦membres={b.rattachement.membre})¦rendu de l'outil — exemple du prompt"
  "$S¦        if item.traitement == \"bloc\" and (bloc.plateforme or¦        if False and (bloc.plateforme or¦pas SA ligne propre, refusé"
  # Diagnostic du 2026-10-23 (`banc-modeles/`) — [S15] sur les DEUX chiffres de `me_7`, modèle, #143.
  "$S¦        if nommes_dans_me7 != total - d:¦        if False:¦les deux écarts dits"
  "$S¦        if en_plateforme != d:¦        if False:¦aucune plateforme : signalé"
  "$S¦    if declares_non_nommes is not None:¦    if False:¦6 nommés + plateforme de 2 = 8 dont 2"
  "$S¦    if nommes_dans_me7 + en_plateforme != total:¦    if False:¦est SIGNALÉ au comité"
  "$S¦    if en_plateforme:¦    if False:¦signalée, jamais muette"
  "$M¦             if c.id == \"nombre_de_programmes_non_nommes\"), None)¦             if c.id == \"autre\"), None)¦lit les DEUX chiffres clés"
  # Étape 0 du plan « découpage » (2026-10-23) — [S16] double comptage dans des lignes sœurs ; et le
  # signal [S15] qui ne doit pas redevenir muet.
  "$S¦            if len(lignes) > 1:¦            if False:¦double comptage refusé"
  "$S¦        signaux_ecart = ([\"[S15] décompte à lire au comité : \" + \" ; \".join(motifs)] if motifs else [])¦        signaux_ecart = []¦les deux écarts dits"
  "$S¦    m16 = _s16(arch)¦    m16 = None¦double comptage refusé"
  # Plan « découpage » B4g, étape 1 (2026-10-23) — le premier niveau imposé, [S17], [R7], rendu, prompt.
  "$F¦        if raccord is None or raccord.get(\"statut\") != \"boucle\":¦        if raccord is None:¦dont la somme ne boucle pas avec les comptes"
  "$F¦        if len(membres) < 2:¦        if False:¦un seul membre au premier niveau"
  "$F¦    for axe in axes_par_priorite:¦    for axe in reversed(axes_par_priorite):¦les produits et services d'abord"
  "$F¦            ecartes.append((axe, \"l'émetteur ne publie pas de chiffre d'affaires sur cet axe\"))¦            pass¦l'axe écarté est DIT"
  "$S¦            motifs.append(f\"le segment « {mi.libelle} » n'a pas son bloc \`{mi.bloc_id}\`\")¦            pass¦un segment imposé omis"
  "$S¦                  and list(b.rattachement.membres) == [mi.membre]):¦                  ):¦deux segments regroupés"
  "$S¦                and est_premier_niveau_publie(b, par_bloc, matiere.ventilation_structure)):¦                and False):¦un bloc publié d'un autre axe ajouté"
  "$F¦    return PremierNiveau(axe=None, periode=None, membres=(), axes_ecartes=tuple(ecartes))¦    return None¦dont la somme ne boucle pas avec les comptes"
  "$M¦    if not pn.impose:¦    if False:¦un premier niveau non imposé est DIT"
  "$S¦    if pn is None or not pn.impose:¦    if pn is None:¦premier niveau NON imposé (axe inexploitable)"
  "$S¦    m17 = _s17(arch, matiere, par_bloc)¦    m17 = None¦branché dans valider_structure"
  "$M¦        *_premier_niveau_texte(m.premier_niveau),¦¦la matière montre le premier niveau imposé"
  "$A¦PREMIER NIVEAU IMPOSÉ : quand le dossier contient¦PREMIER NIVEAU : si le dossier contient¦la consigne dit de recopier le premier niveau"
  "$R¦    if inconnus:¦    if False:¦un axe inconnu dans"
  "$A¦MODELE_ARCHITECTE = \"deepseek-ai/DeepSeek-V4-Pro-0813\"¦MODELE_ARCHITECTE = \"deepseek-ai/DeepSeek-V4-Flash-0731\"¦tourne sur V4-Pro"
  # Plan « découpage » B4g, étape 2 (2026-10-24) — l'arbre de décision remplace le critère #143.
  "$A¦      3. Est-il DÉJÀ VENDU (un chiffre¦      3. Est-il vendu (un chiffre¦DANS L'ORDRE"
  "$A¦    La PROBABILITÉ DE SUCCÈS n'entre PAS dans ce choix¦    La probabilité de succès compte¦HORS du critère"
  "$A¦(question 5) : sa propre ligne.¦réussite incertaine : sa propre ligne.¦HORS du critère"
  "$A¦autre marché (question 3 ou 5). GRAND GROUPE DIVERSIFIÉ¦autre marché (question 3 ou 5). GRAND GROUPE¦paragraphe sectoriel"
  "$A¦rattaché au même segment, SEULEMENT si¦rattaché au même segment, si¦reste du segment"
  "$A¦    \"« Nom » ;¦    \"« son nom » ;¦le nom SEUL"
  "$A¦Tu es l'analyste d'un fonds d'investissement qui dessine¦Tu es l'architecte du classeur qui dessine¦vocabulaire standard"
  "$S¦que des éléments NON nommés (arbre de décision)¦que des éléments NON nommés¦RÈGLE de l'arbre"
  "$A¦    except AgentOutputInvalid as e:¦    except ZeroDivisionError as e:¦sortie hors contrat : PLANTAGE"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
