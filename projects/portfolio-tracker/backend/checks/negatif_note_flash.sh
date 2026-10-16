#!/usr/bin/env bash
# TEST NÉGATIF de `check_note_flash.py` — une mutation par DÉCISION de la note flash (#90), chacune
# exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_note_flash.sh
#
# Ce que la note flash CHANGE au point de lecture (l'horloge par question) est éprouvé par
# `negatif_evenements.sh`, chez son détenteur `evenements.py` — pas ici (#72).
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_note_flash.py"
NF="app/agents/v2/note_flash.py"
SC="app/contracts/note_flash_schema.py"
mutations=(
# §1/§2 — le contrat, le type dérivé
"$SC¦            if self.cause is None:¦            if False:¦une surprise SANS cause est refusée"
"$SC¦    return \"surprise_\" + (\"concurrence\" if cause == \"non_dite\" else cause)¦    return \"surprise_\" + cause¦cause non dite ⟹ \`surprise_concurrence\`"
# §3 — ce qu'on lit
"$NF¦_TYPES_LUS = re.compile(r\"^(8-K|8-K/A|6-K|6-K/A|EX-99(\\.\\d+)?)\$\")¦_TYPES_LUS = re.compile(r\"^(8-K|8-K/A|6-K|6-K/A|EX-99(\\.\\d+)?|EX-5\\.1)\$\")¦l'avis juridique EX-5.1"
"$NF¦        brut = _EN_TETE_XBRL.sub(\" \", brut)¦        pass¦un 6-K (sans item) : l'en-tête XBRL masqué"
"$NF¦            texte = texte[debut.start():] if debut else texte¦            pass¦la page de garde du formulaire"
# §4 — ce que le modèle voit
"$NF¦    out = [{\"id\": t.id, \"libelle\": t.libelle} for t in fichier.types_evenement¦    out = [{\"id\": t.id, \"libelle\": t.libelle, \"portee\": t.portee} for t in fichier.types_evenement¦le modèle ne voit NI la portée"
"$NF¦           and t.id != A_QUALIFIER and not t.id.startswith(\"surprise_\")]¦           and not t.id.startswith(\"surprise_\")]¦catalogue proposé"
# §5 — le pont
"$NF¦            if cite is not None and _normaliser(cite) not in corpus:¦            if False:¦une PARAPHRASE est refusée"
"app/knowledge/citation.py¦    return re.sub(r\"\\s+\", \" \", t).strip().casefold()¦    return t.strip().casefold()¦une citation littérale (espaces normalisés) passe"
"$NF¦    permis = {t[\"id\"] for t in types_proposables(fichier)}¦    permis = {t.id for t in fichier.types_evenement}¦\`a_qualifier\` n'est pas un type"
"$NF¦    types = tuple(sorted({type_derive_de(d[\"type\"], d.get(\"cause\")) for d in elements¦    types = tuple(sorted({d[\"type\"] for d in elements¦les types retenus sont ceux que le CODE dérive"
# §6 — quels dépôts lire
"$NF¦            and (e.accession not in qualifications or qualifications[e.accession].a_relire)¦            and True¦un dépôt déjà lu"
"$NF¦            if e.event_date >= depuis and e.accession¦            if e.accession¦depuis la date"
"$NF¦            and (e.accession not in qualifications or qualifications[e.accession].a_relire)¦            and e.accession not in qualifications¦une note écrite sous une AUTRE version du catalogue est relue"
"$NF¦    a_relire = version != fichier.types_evenement_version¦    a_relire = False¦une note d'une ancienne version COMPTE encore"
"$NF¦                       catalogue_version=fichier.types_evenement_version, note=note,¦                       catalogue_version=fichier.schema_version, note=note,¦une lecture juste : 1 appel"
# §7 — la relecture
"$NF¦    if not types <= connus:¦    if False:¦un type que le référentiel ne connaît plus"
# §8 — la rédaction
"$NF¦    for essai in (1, 2):¦    for essai in (2,):¦renvoyée UNE fois"
"$NF¦    if not documents:¦    if False:¦AVANT tout appel modèle"
# §9 — le rappel (#125) : l'admission (détenteur `verdict_rappel`), la lecture sous l'interrupteur
"$SC¦        if self.type == SURPRISE and self.rappel_du is not None:¦        if False:¦un écart aux attentes n'est jamais un rappel"
"$NF¦        if n.date_evenement == rappel_du and n.date_evenement < event_date and type_ in n.types_annonces:¦        if n.date_evenement == rappel_du:¦un autre type à la bonne date"
"$NF¦        if n.date_evenement == rappel_du and n.date_evenement < event_date and type_ in n.types_annonces:¦        if type_ in n.types_annonces:¦une date sans note"
"$NF¦    if rappel_du >= event_date:¦    if False:¦une date non antérieure"
"$NF¦           and q.date_evenement < event.event_date and q.types_annonces]¦           and q.types_annonces]¦ni la note du dépôt lu ni une note POSTÉRIEURE"
"$NF¦                              for n in precedentes],¦                              for n in []],¦le modèle VOIT les notes précédentes"
"$NF¦        return ((fichier.rappels_ecartes and bool(el.get(\"rappel_admis\")))¦        return ((bool(el.get(\"rappel_admis\")))¦interrupteur OFF : l'ordre 0 EXACT"
"$NF¦        lus = gardes or frozenset({\"routine\"})¦        lus = gardes¦une note faite que de rappels se lit"
"$NF¦        return ((fichier.rappels_ecartes and bool(el.get(\"rappel_admis\")))¦        return ((fichier.rappels_ecartes and False)¦interrupteur ON : le rappel admis ne rouvre rien"
"$NF¦    types = tuple(sorted({type_derive_de(d[\"type\"], d.get(\"cause\")) for d in elements¦    types = tuple(sorted({type_derive_de(d[\"type\"], d.get(\"cause\")) for d in elements if d.get(\"rappel_du\") is None¦les types PERSISTÉS restent ceux de l'ordre 0"
"$NF¦    vues = precedentes if fichier.rappels_ecartes else []¦    vues = precedentes¦interrupteur OFF : le modèle ne voit PAS l'historique"
# Le communiqué de résultats (diagnostic §13, 2026-10-16) — une mutation par règle
"$NF¦            out.append(ph)¦            pass¦le CODE relève la tranche de mai"
"$NF¦        if manquantes:¦        if False:¦une phrase relevée SANS verdict"
"$NF¦        if doubles or hors:¦        if False:¦une phrase jugée deux fois"
"$NF¦            lue = None if revision else date_du_passage(el.passage)¦            lue = None¦la tranche de MAI (date lue)"
"$NF¦            apres = revision or _APRES_CLOTURE.search(el.passage) is not None¦            apres = revision¦subsequent to quarter end"
"$NF¦            revision = el.type == SURPRISE and not d.get(\"ecart_non_etabli\")¦            revision = False¦la RÉVISION établie"
"$NF¦            if motif:¦            if False:¦une prévision SANS référence"
"$NF¦    if not per or per not in _normaliser(el.passage) or per not in nref:¦    if not per:¦deux prévisions de périodes différentes"
"$NF¦    if nref not in corpus and nref not in references:¦    if False:¦une référence absente du dépôt"
"$NF¦    seuil = len(lectures) // 2 + 1¦    seuil = 1¦majorité stricte, jamais l'union"
"$NF¦    return max(vues, default=None)¦    return min(vues, default=None)¦la date écrite dans une phrase se LIT"
"$NF¦                or (fichier.fraicheur_par_duree_de_vie and bool(el.get(\"couvert_par_les_comptes\"))))¦                or False)¦relue (interrupteur actif)"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
