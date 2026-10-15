#!/usr/bin/env bash
# TEST NÉGATIF de `check_search_worker.py`, section 11 — les EXTRAITS LITTÉRAUX d'une fiche (#126).
# Une mutation par DÉCISION, chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint
# (harnais `_negatif.sh`).
#
#   bash checks/negatif_search_worker.sh
#
# La comparaison littérale est DÉLÉGUÉE à `app/knowledge/citation.py` : elle se mute chez son
# détenteur (#72), pas dans le worker — sinon la mutation mesurerait le câblage et croirait mesurer
# la règle. Le câblage, lui, a ses propres mutations (worker, outils).
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_search_worker.py"
W="app/agents/v2/worker.py"
T="app/agents/v2/tools.py"
C="app/contracts/worker_delegation_schema.py"
CIT="app/knowledge/citation.py"
NF="app/agents/v2/note_flash.py"
mutations=(
# la règle, chez son détenteur
"$CIT¦        if not any(n in c for c in corpus):¦        if False:¦paraphrase inventée"
"$CIT¦    return re.sub(r\"\\s+\", \" \", t).strip().casefold()¦    return t.strip().casefold()¦typographie, espaces et casse normalisés"
# le câblage dans le worker
"$W¦        manquant = extrait_introuvable(extraits, log.textes_de(url))¦        manquant = None¦extrapolation du collecteur"
"$W¦        court = next((e for e in extraits if len(e) < EXTRAIT_MIN_CARS), None)¦        court = None¦extrait de moins de 20 caractères (non discriminant) → refusé"
"$W¦        if not extraits:¦        if False:¦clef \`extraits\` absente"
"$W¦        if not extraits:¦        if False:¦liste d'extraits vide sur un document"
"$W¦        extraits = []¦        pass¦aveu llm_memory"
"$W¦    releve = _contenu_du_releve(url, extraits) if extraits else content¦    releve = content¦le texte de la fiche porte les extraits"
"$W¦        \"content_structured\": None if extraits else (¦        \"content_structured\": raw.get(\"content_structured\") if True else (¦valeurs structurées du collecteur ne sont PAS"
"$W¦        \"source_type\": \"agent_synthesis\",¦        \"source_type\": fiche[\"source_type\"],¦la lecture est une synthèse d'agent"
"$W¦        if lecture is not None and lecture[\"reliability_score\"] >= req.reliability_min:¦        if lecture is not None:¦lecture sous le plancher du mandat"
"$W¦    raw: Any, req: WorkerRequest, log: RetrievalLog¦    raw: Any, req: WorkerRequest, log: RetrievalLog = None¦\`_normalise_entry\` exige le journal"
"$W¦        log=retrieval_log,¦        log=RetrievalLog(),¦en production, le journal du run"
# le journal, au point de récupération réel
"$T¦        return list(self.textes.get(key, [])) if key else []¦        return [t for v in self.textes.values() for t in v]¦phrase d'un AUTRE document"
"$T¦            log.record_text(u, result.get(\"text\"))¦            pass¦fetch_url : le texte rapporté est journalisé"
"$T¦            log.record_text(h.url, h.text)¦            log.record_text(h.url, h.text or h.snippet)¦une simple accroche de lien"
# le contrat
"$C¦        n_fiches = sum(1 for e in resp.entries if not est_lecture_du_collecteur(e))¦        n_fiches = len(resp.entries)¦max_entries=1 se compte en FICHES"
"$C¦            if not self.extraits:¦            if False:¦contrat : une fiche de document sans extrait"
"$C¦        if sans_document and self.extraits:¦        if False:¦contrat : une lecture (agent_synthesis)"
"$C¦            courts = [e for e in self.extraits if len(e.strip()) < EXTRAIT_MIN_CARS]¦            courts = []¦contrat : un extrait de moins de 20 caractères"
# le détenteur unique, partagé avec la note flash
"$NF¦_normaliser = normaliser¦_normaliser = lambda t: normaliser(t)¦détenteur unique : la note flash"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
