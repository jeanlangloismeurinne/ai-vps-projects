#!/usr/bin/env bash
# TEST NÉGATIF de `check_connaissance.py` — au moins une mutation par ligne d'acceptation « société
# fictive » du module M3 (`roadmap/archive/V3-M3-base-connaissance.md` §3), chacune exigeant exit≠0 + FAIL
# sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`). Module pur bibliothèque standard : sans
# conteneur, le harnais tourne sur l'hôte et le dit. La vérification mot pour mot est déléguée à
# `citation.py` : elle se mute chez son détenteur.
#   bash checks/negatif_connaissance.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_connaissance.py"
HOTE_SI_SANS_CONTENEUR=1
C="app/modules/connaissance/coeur.py"
L="app/modules/connaissance/lecteur.py"
J="app/modules/connaissance/referentiel.json"
K="app/modules/connaissance/contrat.py"
CIT="app/modules/connaissance/citation.py"

mutations=(
# [K0] le cœur ouvre lui-même une connexion.
"$C¦import hashlib¦import hashlib\nimport urllib.request¦[K0]"
# [K1] un document inconnu donne une pièce (ou plante) au lieu d'un refus nommé.
"$C¦    if lecture is None:¦    if False:¦[K1] un document inconnu ne donne pas de pièce"
# [K1] une lecture impossible donne une pièce.
"$C¦    if lecture[\"statut\"] != L.LUE:¦    if False:¦[K1] une lecture impossible ne donne pas de pièce"
# [K1] une pièce sans auteur passe.
"$C¦    if not auteur.strip():¦    if False:¦[K1] une pièce nomme son auteur"
# [K1] les lignes sont décalées d'une.
"$C¦ligne_debut=ligne_debut,¦ligne_debut=ligne_debut + 1,¦[K1] la pièce nomme son document et ses lignes"
# [K2] relire relit tout.
"$C¦        if d.empreinte in deja:¦        if False:¦[K2] relire ne relit pas"
# [K2] la version du lecteur ne compte plus : un lecteur amélioré ne relit rien.
"$C¦    return {l[\"empreinte\"]: l for l in await depot.lectures(emetteur) if l[\"lecteur\"] == v}¦    return {l[\"empreinte\"]: l for l in await depot.lectures(emetteur)}¦[K2] un lecteur amélioré produit une lecture nouvelle"
# [K3] ce qui est masqué est lu.
"$J¦    \"masques\": [\"display:none\"],¦    \"masques\": [],¦[K3] ce qui est masqué"
# [K3] les scripts sont lus.
"$J¦    \"muets\": [\"script\", ¦    \"muets\": [¦[K3] scripts, styles"
# [K3] les cellules ne s'ouvrent plus sur une tabulation.
"$L¦            self.morceaux.append(\"\\t\")¦            self.morceaux.append(\" \")¦[K3] une ligne de tableau du communiqué réel"
# [K3] les cellules sans lettre ni chiffre ne sont plus recollées.
"$L¦        if not any(ch.isalnum() for ch in c) and c not in _NEANT:¦        if False:¦[K3] une ligne de tableau du communiqué réel"
# [K3] une parenthèse ouvrante part à la cellule d'avant.
"$L¦_OUVRANTS = \"([\" + _DEVISES¦_OUVRANTS = _DEVISES¦[K3] symbole monétaire au nombre qui suit"
# [K3] un bloc dans une cellule coupe la ligne.
"$L¦            self._dans_cellule = 1¦            self._dans_cellule = 0¦[K3] un bloc dans une cellule"
# [K3] les blancs du code source redeviennent des sauts de ligne (lecteur 1.1.0).
"$L¦            self.morceaux.append(garde.sub(\" \", data))¦            self.morceaux.append(data)¦[K3] procuration réelle mise en forme ligne à ligne"
# [K3] un saut de ligne (<br/>) dans une cellule ne vaut plus une espace : les mots se collent.
"$L¦        if self._cache is None and tag in self._blocs:¦        if self._cache is None and tag in self._blocs and not self._dans_cellule:¦[K3] un saut de ligne dans une cellule vaut une espace"
# [K3] un tiret seul est recollé à la cellule d'avant.
"$L¦_NEANT = frozenset({¦_NEANT = frozenset() and frozenset({¦[K3] un tiret seul garde sa cellule"
# [K3] le bloc préformaté perd ses retours à la ligne.
"$L¦_BLANCS_PREFORMATES = re.compile(r\"[\\t\\f\\v]\")¦_BLANCS_PREFORMATES = _BLANCS¦[K3] les blancs du code source valent une espace"
# [K3] les données structurées passent pour illisibles.
"$J¦    \"formats_sans_objet\": [\"application/json\", ¦    \"formats_sans_objet\": [¦[K3] données structurées"
# [K3] une page sans texte est « lue ».
"$L¦    if not lignes:¦    if False:¦[K3] une page sans texte visible"
# [K4] la pièce porte l'extrait de l'auteur.
"$C¦    texte_du_document = t1[debut:fin]¦    texte_du_document = extrait¦[K4] la pièce porte le texte du DOCUMENT"
# [K4] un extrait court ambigu passe (chez le détenteur).
"$CIT¦            if len(passages) > 1:¦            if False:¦[K4] un extrait court ambigu est refusé"
# [K4] un extrait introuvable passe (chez le détenteur).
"$CIT¦            if extrait_introuvable([e], textes) is not None:¦            if False:¦[K4] une paraphrase est refusée"
# [K4] les autres occurrences ne sont plus nommées.
"$C¦for d, _ in positions[1:]}¦for d, _ in positions[:0]}¦[K4] une phrase répétée"
# [K5] une pièce citée deux fois est réécrite.
"$K¦        if piece[\"identifiant\"] in self._pieces:¦        if False:¦[K5] la même pièce citée deux fois"
# [K5] la période ne compte plus dans l'identité.
"$C¦    cle = \"|\".join((empreinte, lecteur, str(debut), str(fin), C.normaliser(extrait), periode.strip()))¦    cle = \"|\".join((empreinte, lecteur, str(debut), str(fin), C.normaliser(extrait)))¦[K5] le même extrait pour une autre période"
# [K6] la période dite par l'auteur est perdue.
"$C¦ auteur=auteur, periode=periode.strip(), cite_le=le,¦ auteur=auteur, periode=\"\", cite_le=le,¦[K6] la période dite par l'auteur"
# [K6] une date absente est devinée (date de lecture).
"$C¦            adresse=d.provenance.adresse, publie_le=d.provenance.publie_le,¦            adresse=d.provenance.adresse, publie_le=d.provenance.publie_le or le,¦[K6] un document sans date"
# [K7] la révocation n'est plus relue.
"$C¦    if signal:¦    if False:¦[K7] révoquée après la citation"
# [K7] une source non admise passe pour admise.
"$C¦    return Valeur(admise=q.admise, niveau=q.niveau, motif=q.motif, source=q.source)¦    return Valeur(admise=True, niveau=q.niveau, motif=q.motif, source=q.source)¦[K7] une pièce d'une source non admise"
# [K8] un seul mot suffit.
"$C¦            if all(m in n for m in demandes):¦            if any(m in n for m in demandes):¦[K8] chaque ligne rendue contient tous les mots"
# [K8] le classement s'inverse.
"$C¦    trouves.sort(key=lambda p: (-p.occurrences,¦    trouves.sort(key=lambda p: (p.occurrences,¦[K8] les lignes les plus riches"
# [K8] le filtre par genre est ignoré.
"$C¦        if lec[\"statut\"] != L.LUE or (genre and lec[\"genre\"] != genre):¦        if lec[\"statut\"] != L.LUE:¦[K8] filtré par genre"
# [K9] le pas se dit fait avant que tout soit lu.
"$C¦        if restants:¦        if False:¦[K9] collecte faite, documents pas encore lus"
# [K9] sans document, le pas se dit fait.
"$C¦        if not vue.documents:¦        if False:¦[K9] aucun document collecté"
# [K3] le caractère nul passe tel quel : la base refuserait de ranger la lecture.
"$L¦            return contenu.decode(enc).replace(\"\\x00\", \"\\ufffd\")¦            return contenu.decode(enc)¦[K3] un caractère nul se lit"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
