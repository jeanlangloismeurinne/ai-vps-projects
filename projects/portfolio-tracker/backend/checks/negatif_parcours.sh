#!/usr/bin/env bash
# TEST NÉGATIF de `check_parcours.py` — une mutation par DÉCISION du parcours (lot 6 maillon 2),
# chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_parcours.sh
#
# Non mutés, et c'est voulu : les refus du CONTRAT (`parcours_schema`) — une cause de collecte sans
# preuve, un incomplet sans manque, un état de revue qui ment. Toute mutation de l'assembleur qui les
# violerait fait LEVER Pydantic (« script mort »), un autre canal que « rouge sur l'assert » ; §3 les
# éprouve directement sur le contrat (même doctrine que `negatif_qualite_info.sh`).
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_parcours.py"
WITH_FRONT=1
N3="FRONT:pages/v2/tickers/[ticker_id]/frameworks/[framework_id]/q/[question_id].js"
P="app/agents/v2/parcours.py"
mutations=(
"$P¦        and a.fondation.actualite == \"courante\"¦        and True  # mutation: une réponse périmée tient¦fondée mais PÉRIMÉE"
"$P¦    if not applicable or dispensee:¦    if not applicable:  # mutation: dispense ignorée¦DISPENSÉE"
"$P¦    if r.verdict != \"acquitte\":¦    if False:  # mutation: l'avis ne compte pas¦personne n'a pu relire"
"$P¦    \"source_indisponible\", \"recherche_epuisee\", \"sans_source_possible\")¦    \"recherche_epuisee\", \"source_indisponible\", \"sans_source_possible\")  # mutation¦la cause en tête est la PANNE"
"$P¦    if collecte is None or collecte.plan_id is None:¦    if collecte is None:  # mutation: plan absent lu comme recherche menée¦une collecte sans plan"
"$P¦    if renvoyees:¦    if renvoyees and False:  # mutation: renvoi ignoré¦renvoyée → nature"
"$P¦                  question_id=question_id, enonce=enonce, mandat_ouvert_id=mandat_ouvert_id,¦                  question_id=question_id, enonce=enonce, mandat_ouvert_id=None,¦DÉJÀ repartie en recherche"
"$P¦                      explication=f\"{_EXPLICATION['controle_ko']} : {r.motif_revue}\", **commun)¦                      explication=_EXPLICATION['controle_ko'], **commun)¦nomme le contrôle qui a refusé"
"$P¦                                      f\"{r.servie.fondation.motif_actualite}\", **commun)¦                                      \"\", **commun)¦porte le motif d'actualité"
"$P¦    if etat.archetype is None:¦    if False:  # mutation: non classé lu comme complet¦NON CLASSÉE"
"$P¦            pieces.append(PieceCitee(entry_id=i, role=role, present_au_corpus=False, au_standard=None))¦            pass  # mutation: pièce absente omise¦ABSENTE du corpus"
"$P¦            remplacee=p[\"superseded_by\"] is not None,¦            remplacee=False,¦REMPLACÉE"
"$P¦            rang_plus_faible_cite=_plus_faible(tiers) if tiers else None))¦            rang_plus_faible_cite=tiers[0] if tiers else None))¦rang le plus faible CITÉ"
"$P¦            answer_id=i, servie=servir_answer(a, ancre=ancre_de(a.question_id), entries=entries),¦            answer_id=i, servie=FrameworkAnswerServie(**a.model_dump()),¦APPELLE \`servir_answer\`"
"$P¦    syntheses, manques, acceptees = [], [], 0¦    syntheses, manques, acceptees = [], [], 0\n    etat.fichier.frameworks.sort(key=lambda f: f.id)  # mutation: ordre alphabétique¦l'ordre du RÉFÉRENTIEL"
"$P¦    ancre = ancre_substantielle(await material_anchor_for_ticker(conn, ticker_id))¦    ancre = await material_anchor_for_ticker(conn, ticker_id)  # mutation: ancre brute¦l'ancre qui PÈSE"
# §7 — le point de lecture : un champ perdu, un pixel inventé, l'alerte descendue sous l'identité.
"$N3¦<span data-champ=\"approximation.sensibilite\">{a.approximation.sensibilite}</span>¦<span>{a.approximation.sensibilite}</span>¦tout champ du contrat a son pixel"
"$N3¦<span data-champ=\"analyste\">{a.analyste}</span>¦<span data-champ=\"analyste\">{a.analyste}</span><span data-champ=\"score_global\" />¦tout pixel rend un champ RÉEL"
"$N3¦            <Ligne label=\"motif\"><span data-champ=\"manager.motif\"><Val v={a.manager?.motif} /></span></Ligne>¦            {/* <span data-champ=\"manager.motif\"> */}¦tout champ du contrat a son pixel"
"FRONT:pages/v2/tickers/[ticker_id]/index.js¦      <DossierComite tickerId={t.ticker_id} />¦¦D'ABORD à « peut-on décider"
"FRONT:components/v2/DossierComite.js¦      <Alerte d={d} />¦      <Conclusions d={d} />\n      <Alerte d={d} />¦l'ordre du niveau 1"
"$P¦    return any(p.au_standard is False for p in _pieces(etat, a))¦    return False¦§5bis niveau 2 : seule la réponse"
"$P¦        n_standard_anterieur=sum(1 for lq in lignes for r in lq.reponses if r.standard_anterieur),¦        n_standard_anterieur=0,¦§5bis niveau 2 : la synthèse compte"
"app/knowledge/standard_collecte.py¦    if metric:¦    if False:¦§5bis pièce produite par le code"
"app/knowledge/standard_collecte.py¦    if \"lecture_du_depot\" in (tags or ()):¦    if False:¦§5bis lecture de dépôt"
"app/knowledge/standard_collecte.py¦    if source_type in _SANS_DOCUMENT:¦    if False:¦§5bis lecture du collecteur"
"app/knowledge/standard_collecte.py¦    return (debut_contenu or \"\").startswith(PREFIXE_FICHE)¦    return True¦§5bis une fiche du collecteur sans extraits"
"app/agents/v2/worker.py¦    return (f\"{PREFIXE_FICHE} {url} (vérifiés¦    return (f\"Extraits du document {url} (vérifiés¦§5bis détenteur unique"
"FRONT:pages/v2/tickers/[ticker_id]/frameworks/[framework_id]/index.js¦          {r.standard_anterieur && (¦          {false && (¦§7 #127 le niveau 2 (la réponse)"
"$N3¦          {p.au_standard === false && (¦          {false && (¦§7 #127 le niveau 3"
"FRONT:components/v2/DossierComite.js¦                {s.n_standard_anterieur > 0 && (¦                {false && (¦§7 #127 le niveau 1"
"FRONT:pages/v2/tickers/[ticker_id]/frameworks/[framework_id]/index.js¦>{s.n_standard_anterieur}</p></div>¦>—</p></div>¦§7 #127 le niveau 2 (la synthèse)"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
