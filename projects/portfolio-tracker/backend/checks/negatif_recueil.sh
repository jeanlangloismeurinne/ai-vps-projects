#!/usr/bin/env bash
# TEST NÉGATIF de `check_recueil.py` — au moins une mutation par ligne d'acceptation du module M2
# (`roadmap/archive/V3-M2-collecte-sources.md` §2, lignes « société fictive »), chacune exigeant exit≠0 +
# FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`). Le module est pur bibliothèque
# standard : sans conteneur, le harnais tourne sur l'hôte et le dit. Les mutations de la règle
# « votre correction tient » visent son détenteur, `emetteurs/regles.py` (une garde déléguée se mute
# chez son détenteur).
#   bash checks/negatif_recueil.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_recueil.py"
HOTE_SI_SANS_CONTENEUR=1
C="app/modules/recueil/coeur.py"
SEC="app/modules/recueil/adaptateurs/registre_sec.py"
SECJ="app/modules/recueil/adaptateurs/registre_sec.json"
SITE="app/modules/recueil/adaptateurs/site.py"
WEB="app/modules/recueil/adaptateurs/web.py"
AD="app/modules/recueil/adaptateurs/__init__.py"
REF="app/modules/recueil/referentiel.json"
EM="app/modules/emetteurs/regles.py"

mutations=(
# [B0] le cœur ouvre lui-même une connexion.
"$C¦import hashlib¦import hashlib\nimport urllib.request¦[B0] seul adaptateurs/transport.py touche le réseau"
# [B1] le cœur reconnaît un formulaire par son nom.
"$C¦    for t in trouves:¦    trouves = [t for t in trouves if t.provenance.partie != \"10-Q\"]\n    for t in trouves:¦[B1] le cœur (code et référentiel) ne nomme aucun formulaire"
# [B1] l'ordre d'autorité n'est plus celui du référentiel : le web passe devant un registre.
"$C¦    return sorted(tous, key=lambda a: ordre.index(a.famille))¦    return sorted(tous, key=lambda a: -ordre.index(a.famille))¦[B1] un registre de plus, injecté, répond avant le site et le web"
# [B2] sans fiche, la collecte plante au lieu de le dire.
"$C¦    except E.FicheAbsente:¦    except ZeroDivisionError:¦[B2]"
# [B2] sans numéro au registre, l'adaptateur plante au lieu de dire qu'il ne s'applique pas.
"$SEC¦            return Trouvaille(raison=\"non_applicable\", detail=\"aucun numéro à ce registre sur la fiche\")¦            raise KeyError(\"numéro\")¦[B2]"
# [B2] le pas de collecte n'attend plus la fiche.
"$C¦    apres = tuple(dict.fromkeys((E.NOM_DU_PAS,) + tuple(apres)))¦    apres = tuple(apres)¦[B2] sans fiche, le chef de dossier attend l'acte"
# [B3] plus de repli sur le prospectus.
"$SECJ¦      \"a_defaut\": {¦      \"a_defaut_retire\": {¦[B3] aucun rapport annuel : le prospectus d'introduction est rendu"
# [B3] le repli est pris même quand un rapport annuel existe.
"$SEC¦        for formes, mention in ((regle[\"formulaires\"], \"\"),¦        for formes, mention in (*(((regle[\"a_defaut\"][\"formulaires\"], regle[\"a_defaut\"][\"mention\"]),) if regle.get(\"a_defaut\") else ()), (regle[\"formulaires\"], \"\"),¦[B3] dès qu'un rapport annuel existe"
# [B3] la mention du prospectus est perdue.
"$SEC¦            m = mention if ligne¦            m = \"\" if ligne¦[B3] l'origine dit que le prospectus tient lieu"
# [B3] un trimestre passe pour une année : les comptes intermédiaires entrent dans le repli.
"$SECJ¦          \"424B4\",¦          \"10-Q\", \"424B4\",¦[B3] aucun rapport annuel : le prospectus"
# [B4] l'empreinte ne dit plus le contenu : deux documents différents se confondent.
"$C¦        empreinte = hashlib.sha256(contenu).hexdigest()¦        empreinte = hashlib.sha256(demande.cle.encode()).hexdigest()¦[B4]"
# [B4] un amendement ne cite plus le document qu'il amende.
"$SEC¦                    remplace=self._remplace(ligne, lignes), mention=mention)¦                    remplace=\"\", mention=mention)¦[B4] le dernier rapport annuel, puis son amendement"
# [B4] les amendements ne sont plus collectés.
"$SEC¦                amendements = [l for l in lignes if l[\"form\"] == forme + suffixe¦                amendements = [l for l in [] if l[\"form\"] == forme + suffixe¦[B4] le dernier rapport annuel, puis son amendement"
# [B4] la seconde collecte retélécharge ce qui est rangé.
"$SEC¦            deja = (await appel.deja(acc)).get(partie)¦            deja = None¦[B4] la seconde collecte ne retélécharge pas"
# [B5] un document non admis passe pour admis.
"$C¦                     \"qualification\": {\"admise\": q.admise,¦                     \"qualification\": {\"admise\": True,¦[B5]"
# [B5] la date des faits est perdue.
"$SEC¦publie_le=ligne[\"filingDate\"], faits_au=ligne[\"reportDate\"],¦publie_le=ligne[\"filingDate\"], faits_au=\"\",¦[B5] un document dit son adresse"
# [B5] toutes les pièces d'une soumission sont rangées, images comprises.
"$SEC¦            if typ != ligne[\"form\"].upper() and not typ.startswith(jointes):¦            if False:¦[B5] seules les pièces que le référentiel nomme"
# [B5] le web cherche d'abord le web ouvert : le site de l'émetteur passe après.
"$WEB¦        for restreint in ([domaines] if domaines else []) + [[]]:¦        for restreint in [[]] + ([domaines] if domaines else []):¦[B5] le site de l'émetteur trouvé par le web"
# [B6] une source inconnue n'est plus présentée à l'évaluateur.
"$C¦        if not q.admise and not q.source and q.niveau != illisible:¦        if False:¦[B6] la source inconnue est notée à évaluer"
# [B6] l'évaluateur qui plante fait tomber le passage.
"$C¦        except Exception as exc:  # noqa: BLE001 — l'évaluateur qui plante laisse la source à évaluer¦        except ZeroDivisionError as exc:¦[B6] un évaluateur qui plante"
# [B6] une source déjà évaluée est réévaluée à chaque passage.
"$C¦        if s[\"statut\"] != A_EVALUER:¦        if False:¦[B6]"
# [B7] les pages des autres sociétés ne sont plus admises.
"$C¦    if autres:¦    if False:¦[B7] la page de relations investisseurs d'une autre société"
# [B7] la société elle-même est admise comme une autre.
"$C¦              if (dom := E.domaine(a)) and not any(dom == s or dom.endswith(\".\" + s) for s in siens if s)]¦              if (dom := E.domaine(a))]¦[B7] les pages de la société elle-même"
# [B8] le pas fait tout de suite, sans attendre la collecte.
"$C¦            return Resultat(issue=EN_COURS, depense=nouvelle,¦            return Resultat(issue=FAIT, depense=nouvelle,¦[B8] pendant la collecte"
# [B8] une demande en échec n'est jamais relancée.
"$C¦            if t is None or t[\"statut\"] == ECHOUEE:¦            if t is None:¦[B8] une collecte en échec est relancée une fois"
# [B8] la reprise relance aussi les demandes déjà répondues.
"$C¦        if t[\"statut\"] != LANCEE:¦        if t[\"statut\"] == ECHOUEE:¦[B8] la reprise ne recollecte pas"
# [B8] un échec d'infrastructure est avalé comme une réponse.
"$C¦            return Resultat(issue=ECHEC, depense=nouvelle, motif=f\"collecte de « {d.genre} » en échec : {t['motif']}\")¦            return Resultat(issue=EN_COURS, depense=nouvelle, motif=\"x\")¦[B8] deux échecs de suite arrêtent le dossier"
# [B9] la dépense de la collecte n'est jamais déclarée.
"$C¦                envoi.declare[d.cle] = dep¦                pass¦[B9] une dépense déclarée ne l'est qu'une fois"
# [B9] la dépense déclarée n'est pas retenue : elle est redéclarée à chaque passage.
"$C¦            if dep != decl:¦            if True:\n                decl = Depense()¦[B9]"
# [B9] l'évaluateur n'est pas compté au travail qui a rencontré la source.
"$C¦                envoi.declare_sources[src] = dep¦                pass¦[B9] la dépense de l'évaluateur, une fois déclarée, est notée"
# [B9] l'évaluation des sources retient le dossier : la collecte n'est « faite » qu'après le jugement.
"$C¦        attendues = [s[\"source\"] for s in vue.sources.values() if s[\"statut\"] in (A_EVALUER, EN_ECHEC)]¦        attendues = []¦[B9] la collecte faite, l'évaluation des sources reste en cours"
# [B6] un évaluateur qui plante deux fois ne s'arrête jamais : la source reste à évaluer sans fin.
"$C¦            statut = EN_ECHEC if essais >= ESSAIS_PAR_DEMANDE else A_EVALUER¦            statut = A_EVALUER¦[B6] l'évaluateur qui plante deux fois"
# [B10] le registre n'est plus consulté sur l'identité.
"$C¦        if adaptateur.famille == A.REGISTRE and hasattr(adaptateur, \"identifier\"):¦        if False:¦[B10] la fiche se complète depuis le registre"
# [B10] votre correction ne tient plus.
"$EM¦            tenus |= {c for c in CHAMPS_IDENTITE if avant.get(c) != apres.get(c)}¦            pass¦[B10] votre correction tient"
# [B10] la saisie d'ouverture est tenue comme une correction : le registre ne complète plus rien.
"$EM¦        if systeme_vu:¦        if True:¦[B10] la saisie d'ouverture"
# [B10] le système touche les lieux de publication.
"$EM¦    nouvelle.update({c: propose[c] for c in change})¦    nouvelle.update({c: propose[c] for c in change})\n    nouvelle[\"lieux\"] = []¦[B10] les lieux de publication ne sont jamais touchés"
# [B10] un homonyme est tranché : le premier trouvé l'emporte.
"$SEC¦            if len(trouves) > 1:¦            if False:¦[B10] un homonyme n'est jamais tranché"
# [B10] l'acte enregistré ne relance pas la collecte.
"$C¦            elif t[\"statut\"] == REPONDUE and t.get(\"acte_attendu\") and int(t.get(\"actes_traites\", 0)) < actes:¦            elif False:¦[B10] votre acte enregistré"
# [B10] le système signe comme l'utilisateur.
"$EM¦    if not _est_systeme(auteur):¦    if False:¦[B10] compléter depuis un registre est un acte du système"
# [B11] plus de seconde tentative.
"$AD¦    if lu.statut in PASSAGERES:¦    if False:¦[B11] une erreur passagère"
# [B11] un document vide est rangé.
"$C¦        if not contenu.strip():¦        if False:¦[B11] le cœur refuse lui-même un document vide"
# [B11] un PDF est lu comme une page.
"$AD¦    if lu.contenu[:5] == b\"%PDF-\" or tm == \"application/pdf\":¦    if False:¦[B11]"
# [B11] la priorité des raisons met l'injoignable devant l'illisible.
"$REF¦\"homonyme\", \"illisible\", \"apercu\", \"trop_volumineux\", \"injoignable\",¦\"homonyme\", \"injoignable\", \"illisible\", \"apercu\", \"trop_volumineux\",¦[B11] un document vide"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
