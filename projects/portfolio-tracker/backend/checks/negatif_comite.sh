#!/usr/bin/env bash
# TEST NÉGATIF de `check_comite.py` — une mutation par DÉCISION du registre du comité (lot 6 maillon
# 3), chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_comite.sh
#
# Non mutés, et c'est voulu : les refus de FORME du contrat qui lèveraient Pydantic au premier objet
# construit (« script mort », autre canal que « rouge sur l'assert ») — §1 les éprouve directement.
# Sont mutées les décisions RÉELLES : la règle de chute (réponse refaite, EDGAR injoignable, fait
# postérieur, jour du dépôt, fuseau), la position, le branchement dans l'alerte et les décomptes, le
# canal unique du renvoi, l'ancre qui pèse au POST, et le point de lecture.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_comite.py"
WITH_FRONT=1
C="app/agents/v2/comite.py"
P="app/agents/v2/parcours.py"
S="app/contracts/comite_schema.py"
M="app/agents/v2/projection_memo.py"
N="app/contracts/memo_projete_schema.py"
A="app/api/parcours_v2.py"
D="FRONT:components/v2/DossierComite.js"
REG="FRONT:components/v2/RegistreComite.js"
N3="FRONT:pages/v2/tickers/[ticker_id]/frameworks/[framework_id]/q/[question_id].js"
mutations=(
# ── la règle de chute (arbitrage n°2) ─────────────────────────────────────────────────────────
"$C¦    if decision.answer_id not in reponses_courantes:¦    if False:  # mutation: réponse refaite ignorée¦l'analyse a été REFAITE"
"$C¦    if ancre.status not in (\"found\", \"none\"):¦    if False:  # mutation: panne EDGAR lue comme « rien de neuf »¦EDGAR injoignable"
"$C¦    if nouveau is not None:¦    if False:  # mutation: un fait nouveau ne fait rien tomber¦(accord important) publié après → TOMBE"
"$C¦        if e.filing_date > jour or (e.filing_date == jour and e.accession != connu):¦        if e.filing_date > jour:  # mutation: le jour même ne compte pas¦déposé le JOUR de la décision fait tomber"
"$C¦        if e.filing_date > jour or (e.filing_date == jour and e.accession != connu):¦        if e.accession != connu:  # mutation: tout fait non cité est « nouveau »¦déposé AVANT le jour de la décision était public"
"$C¦    for e in ancre.recents or ((ancre.event,) if ancre.event else ()):¦    for e in ((ancre.event,) if ancre.event else ()):  # mutation: le dernier seul¦déposé le JOUR de la décision fait tomber"
"$C¦    jour = decision.decide_le.astimezone(_FUSEAU_EDGAR).date()¦    jour = decision.decide_le.date()  # mutation: jour UTC¦se lit à NEW YORK"
# ── la position ───────────────────────────────────────────────────────────────────────────────
"$C¦    derniere = registre[0]¦    derniere = registre[-1]  # mutation: la plus ancienne prime¦un renvoi APRÈS une acceptation la remplace"
# ── le canal unique du renvoi (#46) ───────────────────────────────────────────────────────────
"$C¦        mandat_id = await persist_mandate(conn, mandat, framework_version=version)¦        mandat_id = await conn.fetchval(\"SELECT 1\")  # mutation: second chemin¦emprunte \`persist_mandate\`"
# ── le contrat ────────────────────────────────────────────────────────────────────────────────
"$S¦    if not v:¦    if False:  # mutation: un blanc est un texte¦une justification BLANCHE est refusée"
"$S¦            if self.ancre_etat == \"unavailable\":¦            if False:  # mutation¦sur des faits ILLISIBLES"
# ── le branchement dans l'alerte et les décomptes ─────────────────────────────────────────────
"$P¦    if acceptation is not None and acceptation.etat == \"en_vigueur\":¦    if acceptation is not None:  # mutation: tombée protège aussi¦une acceptation TOMBÉE remet la question"
"$P¦                acceptation=position.acceptation if position else None)¦                acceptation=None)  # mutation: l'alerte ignore le comité¦la seule question applicable est acceptée"
"$P¦                  acceptation_tombee=acceptation)¦                  acceptation_tombee=None)  # mutation: la chute est tue¦ET dit pourquoi"
"$P¦        n_acceptees_comite=sum(1 for lq in lignes if lq.applicable and _acceptee(lq)),¦        n_acceptees_comite=sum(1 for lq in lignes if lq.comite is not None),¦une acceptation tombée n'est pas comptée"
"$P¦        acceptees += sum(1 for lq in lignes if lq.applicable and _acceptee(lq))¦        acceptees += 0  # mutation¦repose sur le comité"
"$P¦        comite=ligne.comite, registre=etat.registre.get((f.id, q.id), []))¦        comite=None, registre=[])  # mutation: le PV n'atteint pas l'écran¦le PV COMPLET"
# ── l'ancre du POST ───────────────────────────────────────────────────────────────────────────
"app/api/parcours_v2.py¦        ancre = ancre_substantielle(await material_anchor_for_ticker(conn, ticker_id))¦        ancre = await material_anchor_for_ticker(conn, ticker_id)  # mutation¦l'ancre qui PÈSE"
# ── la note de comité reprend ce que le comité a retenu (arbitrage A, 2026-09-26) ───────────────
"$M¦            retenue = _retenue(comite.get((f.id, lue.answer.question_id)), lue)¦            retenue = None  # mutation: le comité ignoré par la note¦fait entrer la réponse dans la note"
"$M¦                comite=etat.comite, fichier=etat.fichier,¦                comite={}, fichier=etat.fichier,  # mutation: assembleur sans comité¦fait entrer la réponse dans la note"
"$M¦    if acc.etat != \"en_vigueur\" or acc.decision.answer_id != lue.answer_id:¦    if acc.decision.answer_id != lue.answer_id:  # mutation: acceptation tombée publiée¦acceptation TOMBÉE (fait nouveau) sort"
"$M¦    if acc.etat != \"en_vigueur\" or acc.decision.answer_id != lue.answer_id:¦    if acc.etat != \"en_vigueur\":  # mutation: une autre version couverte¦AUTRE version de la réponse"
"$M¦    if position is None or position.acceptation is None:¦    if position is None:  # mutation: un renvoi lu comme une acceptation¦renvoi POSTÉRIEUR"
"$M¦    lues = [AnswerLue(answer_id=r.answer_id, answer=r.servie, motif_revue=r.motif_revue)¦    lues = [AnswerLue(answer_id=r.answer_id, answer=r.servie)  # mutation: faiblesse perdue¦marquée : la faiblesse"
"$M¦                                       retenues),¦                                       0),  # mutation: motif muet sur le comité¦la rubrique DIT combien"
"$M¦        non_acquittees = len(du_framework) - len(publiees)¦        non_acquittees = len(du_framework) - len([p for p in publiees if p[1] is None])  # mutation: la retenue comptée non acquittée¦la rubrique DIT combien"
"$M¦            if lue.answer.manager is not None and lue.answer.manager.verdict == \"acquitte\":¦            if False:  # mutation: le comité passe avant le contrôle¦pas de faiblesse inventée"
"$N¦        if self.acceptation.etat != \"en_vigueur\":¦        if False:  # mutation¦une acceptation tombée ne se porte pas"
"$N¦            if (d.answer_id, d.question_id) != (self.answer_id, self.question_id):¦            if False:  # mutation¦la décision ne se prête pas"
"$N¦            if acquitte:¦            if False:  # mutation¦un point acquitté ne peut pas"
"$A¦    return dresser_niveau1(etat, memo_de_l_etat(etat))¦    return dresser_niveau1(etat, projeter_memo(ticker_id=ticker_id, lues=[], archetype=None, comite={}))¦SEUL \`memo_de_l_etat\` assemble"
"$D¦                {pt.retenue_par_comite && <RetenueComite r={pt.retenue_par_comite} />}¦                {null}¦l'écran de la note LIT la mention"
# ── le point de lecture ───────────────────────────────────────────────────────────────────────
"$REG¦<span data-pv=\"mandat_remplace_id\">¦<span>¦tout champ du PV a son pixel"
"$REG¦<span data-pv=\"auteur\">{dcs.auteur}</span>¦<span data-pv=\"auteur\">{dcs.auteur}</span><span data-pv=\"signature\" />¦tout pixel rend un champ RÉEL"
"$N3¦      {d.manque && <ManqueBloc m={d.manque} tickerId={d.ticker_id} lien={false} />}¦      <RegistreComite d={d} onRecalcule={setD} />\n      {d.manque && <ManqueBloc m={d.manque} tickerId={d.ticker_id} lien={false} />}¦APRÈS avoir lu la preuve"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
