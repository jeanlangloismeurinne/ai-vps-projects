#!/usr/bin/env bash
# TEST NÉGATIF de `check_recueil_evaluateur.py` — le moteur réel (Exa), le modèle réel (DeepInfra) et
# l'évaluateur réel des sources inconnues : au moins une mutation par invariant, chacune exigeant
# exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`). La règle « un essai
# manqué garde ce qu'il a payé » vit dans le cœur (`coeur.py`) : elle s'y mute.
#   bash checks/negatif_recueil_evaluateur.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_recueil_evaluateur.py"
HOTE_SI_SANS_CONTENEUR=1
X="app/modules/recueil/adaptateurs/exa.py"
XJ="app/modules/recueil/adaptateurs/exa.json"
D="app/modules/recueil/adaptateurs/deepinfra.py"
WEB="app/modules/recueil/adaptateurs/web.py"
AD="app/modules/recueil/adaptateurs/__init__.py"
EV="app/modules/recueil/evaluateur.py"
C="app/modules/recueil/coeur.py"
EMC="app/modules/emetteurs/contrat.py"

mutations=(
# [X1] la catégorie n'est plus transmise.
"$X¦            corps[\"category\"] = _ref()[\"categories\"][categorie]¦            pass¦[X1] la demande porte la requête"
# [X1] les domaines ne sont plus transmis.
"$X¦            corps[\"includeDomains\"] = list(domaines)¦            pass¦[X1] la demande porte la requête"
# [X1] la date est perdue.
"$X¦publie_le=_jour(x.get(\"publishedDate\")))¦publie_le=\"\")¦[X1] chaque résultat garde son adresse"
# [X1] la dépense déclarée est ignorée.
"$X¦        return Depense(web_usd=float(total) if ok else repli)¦        return Depense(web_usd=repli)¦[X1] la dépense est celle qu'Exa déclare"
# [X2] sans coût déclaré, rien n'est compté.
"$X¦        return Depense(web_usd=float(total) if ok else repli)¦        return Depense(web_usd=float(total) if ok else 0.0)¦[X2]"
# [X3] un refus d'Exa devient une liste vide.
"$X¦            raise MoteurInjoignable(f\"Exa {quoi} : statut¦            return {}\n            raise MoteurInjoignable(f\"Exa {quoi} : statut¦[X3] refus, silence ou clef absente"
# [X3] l'adaptateur web laisse passer l'exception.
"$WEB¦            except MoteurInjoignable as exc:¦            except ZeroDivisionError as exc:¦[X3] l'adaptateur web nomme"
# [X4] le texte revient sous l'adresse normalisée.
"$X¦            adresse = x.get(\"id\") if x.get(\"id\") in adresses else x.get(\"url\")¦            adresse = x.get(\"url\")¦[X4] le texte revient sous l'adresse demandée"
# [X4] les doublons sont demandés.
"$X¦        adresses = [a for a in dict.fromkeys(adresses) if a]¦        adresses = [a for a in adresses if a]¦[X4] chaque adresse n'est demandée qu'une fois"
# [M1] la dépense déclarée est ignorée.
"$D¦    if isinstance(declare, (int, float)) and not isinstance(declare, bool) and declare >= 0:¦    if False:¦[M1] l'objet JSON et la dépense déclarée"
# [M1] un modèle inconnu est gratuit.
"$D¦    prix = _ref()[\"prix_usd_par_million_de_jetons\"].get(modele) or _ref()[\"prix_de_repli\"]¦    prix = _ref()[\"prix_usd_par_million_de_jetons\"].get(modele) or {\"entree\": 0, \"sortie\": 0}¦[M1] un modèle sans prix connu"
# [M1] l'objet JSON n'est plus exigé.
"$D¦                 \"response_format\": {\"type\": \"json_object\"},¦¦[M1] la demande nomme le modèle"
# [M2] plus de reprise.
"$D¦        for pause in _ref()[\"pauses_avant_reprise_s\"]:¦        for pause in []:¦[M2] « occupé » se reprend"
# [M2] un refus définitif est repris.
"$D¦            if lu.statut not in PASSAGERES:¦            if lu.statut == 200:¦[M2] un refus définitif n'est pas repris"
# [M3] une réponse coupée passe.
"$D¦        if choix.get(\"finish_reason\") == \"length\":¦        if False:¦[M3] réponse coupée"
# [M3] l'échec perd sa dépense.
"$D¦            raise ModeleEnEchec(f\"la réponse n'est pas un objet JSON ({type(exc).__name__})\", depense) from exc¦            raise ModeleEnEchec(f\"la réponse n'est pas un objet JSON ({type(exc).__name__})\") from exc¦[M3] du texte libre"
# [V1] une page d'un autre site est lue.
"$EV¦    return bool(hote) and (hote == source or hote.endswith(\".\" + source)) and chemin not in (\"\", \"/\")¦    return bool(hote) and chemin not in (\"\", \"/\")¦[V1]"
# [V1] la page d'accueil est lue comme une publication.
"$EV¦    return bool(hote) and (hote == source or hote.endswith(\".\" + source)) and chemin not in (\"\", \"/\")¦    return bool(hote) and (hote == source or hote.endswith(\".\" + source))¦[V1]"
# [V1] les pages de rubrique non datées passent devant.
"$EV¦            candidats = [x.adresse for x in sorted(trouves, key=lambda x: not x.publie_le)¦            candidats = [x.adresse for x in sorted(trouves, key=lambda x: 0)¦[V1] la rencontrée d'abord"
# [V1] la recherche n'est plus limitée au domaine.
"$EV¦            trouves, d = await self._moteur.rechercher(r[\"requete\"].format(source=source), domaines=[source],¦            trouves, d = await self._moteur.rechercher(r[\"requete\"].format(source=source), domaines=[],¦[V1] une seule recherche, limitée au domaine"
# [V1] on cherche même quand les publications rencontrées suffisent.
"$EV¦            if len(lues) >= n or not recherches:¦            if not recherches:¦[V1] assez de publications rencontrées"
# [V2] plus de second chemin par le moteur.
"$EV¦            if len(lues) < n and a_relire and hasattr(self._moteur, \"contenus\"):¦            if False:¦[V2] des pages refusées en direct"
# [V2] toutes les pages refusées partent au moteur.
"$EV¦                textes, d = await self._moteur.contenus(a_relire[: n - len(lues) + 1])¦                textes, d = await self._moteur.contenus(a_relire)¦[V2] au moteur, seulement les pages qui manquent"
# [V2] le modèle juge sur trop peu de publications.
"$EV¦        if len(publications) < n:¦        if not publications and False:¦[V2] trop peu de publications lisibles"
# [V2] l'échec perd la dépense de la recherche.
"$EV¦                + (f\" ({' ; '.join(notes[:4])})\" if notes else \"\"), depense)¦                + (f\" ({' ; '.join(notes[:4])})\" if notes else \"\"), Depense())¦[V2] l'échec porte ce que la recherche a coûté"
# [V2] une seule recherche avant de renoncer.
"$EV¦        recherches = list(ref[\"recherches\"]) if self._moteur is not None else []¦        recherches = list(ref[\"recherches\"])[:1] if self._moteur is not None else []¦[V2] les recherches du référentiel sont toutes essayées"
# [V3] les critères ne sont plus montrés au modèle.
"$EV¦        lignes.append(f\"- {cle} : {c['texte']}¦        lignes.append(f\"- {cle} : ¦[V3] chaque question et chaque critère de M1"
# [V3] le critère des pages de relations investisseurs est proposé au modèle.
"$EMC¦            \"criteres\": {k: dict(v) for k, v in ref[\"criteres\"].items() if k != CRITERE_PAGES_INVESTISSEURS},¦            \"criteres\": {k: dict(v) for k, v in ref[\"criteres\"].items()},¦[V3] le critère des pages de relations investisseurs"
# [V3] le texte de la page garde ses scripts.
"$AD¦    _MUETS = {\"script\", \"style\", \"noscript\", \"svg\", \"head\", \"template\"}¦    _MUETS = set()¦[V3] le texte de chaque publication"
# [V4] le niveau proposé par le modèle passe.
"$EV¦        natures, niveau = tuple(grille[\"criteres\"][critere][\"natures\"]), grille[\"criteres\"][critere][\"niveau_max\"]¦        natures, niveau = tuple(objet.get(\"natures\")), objet.get(\"niveau\")¦[V4] le critère choisi fixe le niveau"
# [V4] sans critère, n'importe quel niveau passe.
"$EV¦                or niveau not in grille[\"niveaux\"]):¦                or False):¦[V4] sans critère, un niveau hors échelle"
# [V4] sans critère, n'importe quelle nature passe.
"$EV¦any(n not in grille[\"natures\"] for n in natures)¦False¦[V4] sans critère, une nature hors échelle"
# [V5] une page inventée est acceptée.
"$EV¦        if adresse not in donnees:¦        if adresse is None:¦[V5] une page qu'on ne lui a pas donnée"
# [V5] un constat vide passe.
"$EV¦            if not isinstance(constat, str) or not constat.strip():¦            if not isinstance(constat, str):¦[V5] un constat vide"
# [V5] une publication oubliée passe.
"$EV¦    if manquent:¦    if False:¦[V5] une publication oubliée"
# [V5] une réponse hors forme perd la dépense du modèle.
"$EV¦            raise EvaluationImpossible(f\"réponse du modèle hors de la forme demandée : {exc}\", depense) from exc¦            raise EvaluationImpossible(f\"réponse du modèle hors de la forme demandée : {exc}\", Depense()) from exc¦[V5] une question sans réponse"
# [V6] un essai manqué perd ce qu'il a payé (détenteur : le cœur).
"$C¦            cumul = Depense(**s.get(\"depense\", {})).plus(paye if isinstance(paye, Depense) else Depense())¦            cumul = Depense(**s.get(\"depense\", {}))¦[V6] chaque essai manqué garde ce qu'il a payé"
# [V7] la consigne est écrite dans le code.
"$EV¦            objet, d = await self._modele.completer(modele=ref[\"modele\"], consigne=ref[\"consigne\"],¦            objet, d = await self._modele.completer(modele=ref[\"modele\"], consigne=\"Vous évaluez une source.\",¦[V7] la consigne et le modèle sont ceux du référentiel"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
