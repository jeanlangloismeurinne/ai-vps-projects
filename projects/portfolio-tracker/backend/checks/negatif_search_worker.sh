#!/usr/bin/env bash
# TEST NÉGATIF de `check_search_worker.py`, section 11 — les EXTRAITS LITTÉRAUX d'une fiche (#126) —
# section 12 — la source d'origine d'abord (site de l'émetteur, à défaut ailleurs) — et section 13 —
# la lecture tolérante entry par entry (#128) et la relance sans recherche web (#B).
# Une mutation par DÉCISION, chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint
# (harnais `_negatif.sh`).
#
#   bash checks/negatif_search_worker.sh
#
# La comparaison littérale est DÉLÉGUÉE à `app/knowledge/citation.py` : elle se mute chez son
# détenteur (#72), pas dans le worker — sinon la mutation mesurerait le câblage et croirait mesurer
# la règle. Le câblage, lui, a ses propres mutations (worker, outils). Même principe pour #128 : la
# relecture item par item est DÉLÉGUÉE à `runner.lecture_tolerante_liste` (partagée avec l'analyste) —
# ses deux mutations visent donc `runner.py`, pas `worker.py`.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_search_worker.py"
W="app/agents/v2/worker.py"
T="app/agents/v2/tools.py"
C="app/contracts/worker_delegation_schema.py"
CIT="app/knowledge/citation.py"
NF="app/agents/v2/note_flash.py"
WS="app/knowledge/websearch.py"
R="app/agents/v2/runner.py"
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
"$W¦        \"title\": titre_de_fiche(url),¦        \"title\": (raw.get(\"title\") or \"\").strip() or None,  # mutation: repli sur le titre du modèle¦le titre de la fiche NOMME le document"
# Arbitrage du 2026-10-18 : la « lecture du collecteur » redevient titrée par le modèle (son propre
# titre, une AFFIRMATION) plutôt que par le détenteur unique du nom de document.
"$W¦        \"title\": f\"Lecture du collecteur — {titre_de_fiche(fiche['source_url'])}\",¦        \"title\": f\"Lecture du collecteur — {(raw.get('title') or '').strip() or fiche['source_url']}\",  # mutation: titre du modèle¦titre de la LECTURE DU COLLECTEUR nomme le document"
"$W¦        key = (entry[\"source_url\"], (entry[\"title\"] or \"\").lower(), entry[\"content\"].lower())¦        key = (entry[\"source_url\"], (entry[\"title\"] or \"\").lower())¦deux fiches d'un même document"
# le journal, au point de récupération réel
"$T¦        return list(self.textes.get(key, [])) if key else []¦        return [t for v in self.textes.values() for t in v]¦phrase d'un AUTRE document"
"$T¦            log.record_text(u, result.get(\"text\"))¦            pass¦fetch_url : le texte rapporté est journalisé"
"$T¦            log.record_text(h.url, h.text)¦            log.record_text(h.url, h.text or h.snippet)¦une simple accroche de lien"
# le contrat
"$C¦        n_fiches = sum(1 for e in resp.entries if not est_lecture_du_collecteur(e))¦        n_fiches = len(resp.entries)¦max_entries=1 se compte en FICHES"
"$C¦            if not self.extraits:¦            if False:¦contrat : une fiche de document sans extrait"
"$C¦        if sans_document and self.extraits:¦        if False:¦contrat : une lecture (agent_synthesis)"
"$C¦            courts = [e for e in self.extraits if len(e.strip()) < EXTRAIT_MIN_CARS]¦            courts = []¦contrat : un extrait de moins de 20 caractères"
# #132 — les tableaux, au point de conversion en texte (détenteur : websearch.html_to_text)
"$WS¦            self.parts.append(\"\\t\")¦            pass¦les cellules d'en-tête ne sont plus collées"
"$WS¦            self.parts.append(\" \" if self._cell else \"\\n\")¦            self.parts.append(chr(10))¦tient sur une ligne"
"$WS¦            self._cell = 0  # une cellule non fermée¦            pass  # une cellule non fermée¦ne fait pas déborder une ligne sur la suivante"
"$WS¦            self._cell = 0  # fin de ligne¦            pass  # fin de ligne¦ne déborde pas sur le paragraphe suivant"
# la source d'origine d'abord (2026-10-16), chez son détenteur (websearch.web_search) puis au câblage
"$WS¦    origine = await backend.search(q, n, include_domains=domaines) if domaines else []¦    origine = []¦le site de l'émetteur est interrogé"
"$WS¦    ouvert = await backend.search(q, n)¦    ouvert = []¦et le web ouvert l'est aussi"
"$WS¦    hits = origine + [h for h in ouvert if h.url not in vus]¦    hits = [h for h in ouvert if h.url not in vus] + origine¦passent EN TÊTE"
"$WS¦    hits = origine + [h for h in ouvert if h.url not in vus]¦    hits = origine + ouvert¦n'est pas répétée"
"$WS¦    domaines = issuer_domains_for(ticker_id)¦    domaines = (\"nvidia.com\",)¦aucun domaine deviné"
"$WS¦            \"site_emetteur\": est_site_emetteur(self.url, ticker_id),¦            \"site_emetteur\": True,¦et qu'une reprise n'en vient pas"
"$WS¦    return bool(host) and any(host == d or host.endswith(\".\" + d) for d in issuer_domains_for(ticker_id))¦    return bool(host) and any(host.endswith(d) for d in issuer_domains_for(ticker_id))¦notnvidia.com"
"$T¦        hits = await web_search(query, n, ticker_id=ticker_id)¦        hits = await web_search(query, n)¦le site de l'émetteur est interrogé"
# le détenteur unique, partagé avec la note flash
"$NF¦_normaliser = normaliser¦_normaliser = lambda t: normaliser(t)¦détenteur unique : la note flash"
# #128 — lecture tolérante entry par entry, DÉLÉGUÉE à runner.lecture_tolerante_liste (partagée
# avec l'analyste) : ses deux mutations visent donc runner.py, pas worker.py.
"$R¦            erreurs.append((it, str(v)))¦            valides.append(it)¦la bonne fiche survit, les deux fautives sont écartées"
"$R¦            valides.append(it)¦            pass¦la bonne fiche survit, les deux fautives sont écartées"
# le câblage dans le worker : tolérance de FORME (sortie illisible toujours relevée) et #126
# toujours vérifié même pour une entry tolérée
"$W¦        if not lect.lisible:¦        if True:¦la bonne fiche survit, les deux fautives sont écartées"
"$W¦        if not lect.lisible:¦        if False:¦sortie brute illisible → l'exception d'origine"
"$W¦        manquant = extrait_introuvable(extraits, log.textes_de(url))¦        manquant = None¦entrée tolérée par #128 reste vérifiée par #126"
# #B — la relance unique sans recherche web
"$W¦    if _doit_relancer_sans_web(corrected, retrieval_log, allow_without_web=allow_without_web):¦    if False:¦relance UNIQUE, le rappel est bien dans le message"
"$W¦    if _doit_relancer_sans_web(corrected, retrieval_log, allow_without_web=allow_without_web):¦    while _doit_relancer_sans_web(corrected, retrieval_log, allow_without_web=allow_without_web):¦le second tour est aussi vide"
"$W¦    return log.appels_de(\"web_search\") == 0 and log.appels_de(\"fetch_url\") == 0¦    return True¦MAIS un appel \`web_search\` a eu lieu pendant le tour"
"$W¦            cost_usd=cost1 + cost2, log=retrieval_log,¦            cost_usd=cost2, log=retrieval_log,¦coût (et les tokens) des DEUX tours sont cumulés"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
