"""L'APPARIEUR — maillon 4bis du lot 3 : le pont entre une carte d'appariement et le RÉEL.

Le contrat (`app/contracts/appariement_schema.py`) garantit qu'une ligne d'appariement est cohérente
AVEC ELLE-MÊME : un `exact` porte un concept et rien d'autre, une `approximation` porte sa formule et
ses hypothèses. Il ne peut rien dire de plus, parce qu'un contrat valide un objet et jamais la
cohérence entre deux (#37). Or tout ce qui rend un appariement VRAI est relationnel :

  · le concept nommé est-il DÉPOSÉ par cet émetteur-là ?
  · l'ingrédient apparié existe-t-il dans le plan, et le plan a-t-il dit qu'on le cherchait ?
  · la formule repose-t-elle sur les concepts déclarés, ou sur d'autres qu'on n'a jamais vérifiés ?

C'EST LA GARDE QUI MANQUAIT, ET QUI BLOQUE LA COLLECTE RÉELLE
--------------------------------------------------------------
`collecte_executor.poste_retenu()` vérifie aujourd'hui deux choses — que le poste appartient au
catalogue, et que la métrique n'est pas une dérivation — et **jamais** que le poste nommé répond à la
métrique. « clauses restrictives (covenants) des contrats de dette → `total_liabilities` » traverse
ces deux contrôles sans une alerte : le poste est au catalogue, la métrique ne contient aucun
opérateur. Le lien de couverture porterait alors le bon libellé en face du MAUVAIS nombre (#43/#60),
et rien en aval ne le rattrape — un nombre exact est indiscernable d'un nombre juste.

Le remède par le PROMPT a été mesuré, puis disqualifié : 11 lignes / 11 justes sur NVDA, et le MÊME
prompt sur MSFT rend 15 lignes dont 10 fausses (`feedback_jugement_modele_instable_entre_passages`).
Une garantie qui dépend d'une formulation n'est pas une garantie. D'où ce fichier : le modèle
PROPOSE, le code VÉRIFIE.

CE QUE CE PONT ATTRAPE, ET CE QU'IL N'ATTRAPE PAS — À LIRE AVANT DE S'Y FIER
-----------------------------------------------------------------------------
Il attrape la classe de fautes qui est décidable sans comprendre la question :

  · un concept INVENTÉ ou approchant. C'est le mode de panne de
    `feedback_adressage_par_nom_exige_lecture` : un émetteur dépose entre 269 et 627 concepts, bien
    au-delà de ce qu'un modèle restitue de mémoire, donc il écrit un nom VOISIN (`InventoryNet` là où
    l'émetteur dépose `InventoryNetCurrent`) et fabrique un appariement silencieux. Confronté à
    l'inventaire, ce nom n'existe pas ;
  · un concept que CET émetteur-là ne dépose pas, même s'il est parfaitement réel ailleurs — les six
    postes absents de RVMD ;
  · un concept qui n'apparaît QUE dans la formule, donc qui échapperait à la vérification ci-dessus ;
  · un `deterministe=True` posé sur une formule qui contient un coefficient choisi.

Il n'attrape PAS le faux appariement SÉMANTIQUE : `Liabilities` est déposé par tous les émetteurs, et
l'apparier aux « clauses restrictives » passerait l'inventaire. Ce n'est pas un oubli, c'est la
frontière de ce qui se décide en code. Ce que le maillon 4bis oppose à cette faute-là n'est pas un
`if`, c'est la FORME de la réponse : un `exact` ne peut porter qu'UN concept nu, sans formule et sans
hypothèse, donc tout ce qui demande un raisonnement doit sortir en `approximation` — où le
raisonnement est ÉCRIT, et où le lecteur peut le contester. Le système cesse d'avoir à choisir entre
mentir et renoncer ; c'est ce que la troisième case achète.

Ces asserts gardent donc une STRUCTURE, jamais une sémantique, et ils le disent — même discipline que
`check_collecte_executor` §3bis, qui garde l'énoncé du prompt et jamais son comportement.
"""
from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import date
from typing import Any, Collection, NamedTuple, Optional

from pydantic import Field, ValidationError

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.runner import AgentRunResult, run_json_agent
from app.contracts.analysis_v2_schemas import Strict
from app.contracts.appariement_schema import AppariementCarte, AppariementItem
from app.contracts.collection_plan_schema import CollectionPlan, CollectionPlanItem
from app.knowledge.edgar_facts import duree_jours, est_point_de_flux
from app.knowledge.edgar_feed import is_annual_flow

__all__ = [
    "AppariementRefuse",
    "AppariementSansObjet",
    "Appariement",
    "AppariementSortie",
    "LigneInventaire",
    "concepts_de_la_formule",
    "coefficients_choisis",
    "resumer_inventaire",
    "rendre_inventaire",
    "LEGENDE_INVENTAIRE",
    "dernier_depot_vu",
    "derniere_periode_vue",
    "lignes_a_apparier",
    "contexte_apparieur",
    "mots_du_concept",
    "voisins_deposes",
    "concepts_absents",
    "message_apparieur",
    "message_reparation",
    "apparier",
    "valider_pont_appariement",
]


class AppariementRefuse(Exception):
    """La carte d'appariement contredit le réel (l'inventaire déposé) ou le plan dont elle dérive.

    Un refus, jamais une dégradation silencieuse : une carte à moitié valide ferait router au web des
    ingrédients dont on croirait avoir vérifié l'appariement.
    """


class AppariementSansObjet(Exception):
    """Il n'y a rien à apparier, et on le sait AVANT tout appel modèle (#40) : un plan sans aucune
    ligne `traduit`, ou un inventaire sans point daté. Même frontière que `TraducteurInapplicable` —
    on ne paie pas un appel pour apprendre ce qu'une lecture du plan dit gratuitement."""


# Un concept XBRL s'écrit en CamelCase et commence par une majuscule (`NetIncomeLoss`,
# `LiabilitiesCurrent`). Les mots en minuscules d'une formule sont de la prose ou un terme web ; ils
# ne sont pas des concepts déposés et ne se cherchent donc pas dans l'inventaire.
_RE_CONCEPT = re.compile(r"\b[A-Z][A-Za-z0-9]*\b")

# Un littéral DÉCIMAL dans une formule est la signature d'un coefficient CHOISI — « 60 % du capex est
# du maintien ». Un entier ne l'est pas : c'est une conversion d'unité ou de période (`/4` pour un
# trimestre, `*12` pour annualiser un mois), et il n'introduit aucun paramètre à débattre.
#
# ⚠️ La règle est NÉCESSAIRE, pas suffisante, et c'est délibéré : un coefficient peut se cacher dans
# un entier (`*3` pour « trois ans de capex normatif »). Ce que ce contrôle garantit, c'est qu'un
# `deterministe=True` portant un pourcentage visible est REFUSÉ — pas qu'un `deterministe=True` qui
# passe soit vrai. Le reste est porté par les hypothèses écrites, qui sont lisibles et contestables.
_RE_DECIMAL = re.compile(r"\b\d+[.,]\d+\b")


def concepts_de_la_formule(formule: str) -> set[str]:
    """Les identifiants CamelCase référencés par une formule. Pur, hors-ligne."""
    return set(_RE_CONCEPT.findall(formule))


def coefficients_choisis(formule: str) -> list[str]:
    """Les littéraux décimaux d'une formule — la signature d'un paramètre choisi. Pur, hors-ligne."""
    return _RE_DECIMAL.findall(formule)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# L'INVENTAIRE COMME OUTIL DE LECTURE — la moitié déterministe, à éprouver avant toute dépense
# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Le pont ci-dessus REFUSE un concept inventé. Il ne suffit pas : un modèle qu'on refuse sans lui
# donner de quoi lire se contente de réessayer un autre nom voisin, ou se replie sur `indisponible`
# partout — et un `indisponible` n'est jamais refusé, donc le taux de refus tomberait à zéro pendant
# que la collecte se viderait. C'est le mode de panne de `feedback_adressage_par_nom_exige_lecture` :
# un adressage par NOM exige son outil de LECTURE, et un outil qui ne couvre qu'une PARTIE du corpus
# refait la faute en `verdict=ok`.
#
# D'où les trois décisions de forme ci-dessous, chacune contre une tentation moins chère :
#
#   1. L'inventaire est donné EN ENTIER, jamais une liste courte. Un pré-appariement lexical (« voici
#      les 20 concepts dont le nom ressemble à l'ingrédient ») re-rétrécirait exactement la fenêtre
#      que ce maillon existe pour ouvrir — c'est la faute de `POSTES` avec une autre implémentation,
#      et elle serait pire : invisible, parce que le modèle ne peut pas nommer ce qu'on ne lui montre
#      pas. 627 concepts ≈ 25 k caractères, soit ~$0.0005 en entrée. L'option correcte est la moins
#      chère ; il n'y a pas d'arbitrage à faire.
#   2. Le rendu est TOTAL : une ligne par clef de l'inventaire, y compris les concepts sans point
#      exploitable. Le vocabulaire que le modèle LIT doit être exactement celui que `[V]` ACCEPTE.
#      Un rendu qui filtre (« les concepts vivants », « ceux du dernier exercice ») fabriquerait des
#      refus dont le modèle ne pouvait pas sortir, et l'analyse du taux de refus mesurerait le filtre.
#   3. Chaque ligne porte ce que `companyfacts` donne DÉJÀ gratuitement et qui change la décision :
#      flux ou solde (et sur combien de jours), l'unité, la date et la valeur du point le plus récent.
#      C'est ce qui transforme « devine ce que `AssetsCurrent` veut dire » en une LECTURE. Le `label`
#      us-gaap n'y est pas : pour un concept standard il paraphrase le nom en CamelCase, et l'ajouter
#      exigerait d'élargir le contrat de `fetch_company_facts`, seul détenteur de la lecture (#46).
#
# Tout ce bloc est PUR (l'inventaire arrive déjà lu) : il se rejoue hors-ligne, et il s'imprime EN
# TEXTE avant le premier jeton payé (`feedback_frontiere_gratuite_avant_depense_modele`).

class LigneInventaire(NamedTuple):
    """Ce qu'on sait d'UN concept déposé, sans rien aller chercher de plus.

    `nature` vaut `flux`, `instant`, `mixte` (l'émetteur dépose le concept dans les deux cadrages —
    un signal, pas un défaut) ou `sans_point` (déposé mais aucun point daté et chiffré : il reste
    NOMMABLE, donc il reste affiché).

    `nb_dates` / `premier_end` / `nb_exercices` décrivent la PROFONDEUR de la série, et ils ne sont
    pas décoratifs : sans eux, le rendu ne montre qu'un point par concept et le modèle en conclut
    qu'il n'y a pas d'historique. Mesuré sur MSFT, où six ingrédients sont sortis `indisponible`
    avec pour motif « il n'y a pas de série de plusieurs exercices » alors que `companyfacts` porte
    la série entière — une distorsion INTRODUITE PAR LE RENDU, donc un `indisponible` que nous
    avions fabriqué (même famille que `feedback_contrat_du_mesureur_ecarte_le_cas`).
    """
    concept: str
    nature: str
    duree_jours: Optional[int]
    nb_exercices: int
    unite: Optional[str]
    dernier_end: Optional[str]
    premier_end: Optional[str]
    nb_dates: int
    derniere_valeur: Optional[float]
    nb_points: int
    autres_unites: int


def resumer_inventaire(facts: dict[str, list[dict[str, Any]]]) -> list[LigneInventaire]:
    """L'inventaire brut de `fetch_company_facts`, résumé en une ligne par concept. Pur, hors-ligne.

    TOTAL par construction (`for concept in sorted(facts)`) : la liste rendue a exactement autant
    d'éléments que l'inventaire a de clefs — c'est l'invariant qui empêche le rendu de devenir une
    liste partielle, et il se vérifie par une égalité d'ensembles, jamais par un décompte.

    Tri ALPHABÉTIQUE, et non par fraîcheur ni par nombre de points : le modèle doit pouvoir LOCALISER
    un nom et voir ses voisins (`InventoryNet` à côté de `InventoryNetCurrent`), ce qui est
    précisément la confusion à lui éviter. Un tri par pertinence supposerait qu'on sait déjà ce qu'il
    cherche — autrement dit qu'on a fait l'appariement à sa place.
    """
    lignes: list[LigneInventaire] = []
    for concept in sorted(facts):
        points = facts.get(concept) or []
        # « Exploitable » = daté ET chiffré. Un point sans `val` ne se recopie pas, un point sans
        # `end` ne se date pas ; aucun des deux ne peut fonder un appariement.
        utiles = [p for p in points if p.get("end") and p.get("val") is not None]
        if not utiles:
            lignes.append(LigneInventaire(
                concept=concept, nature="sans_point", duree_jours=None, nb_exercices=0,
                unite=None, dernier_end=None, premier_end=None, nb_dates=0,
                derniere_valeur=None, nb_points=len(points), autres_unites=0))
            continue
        recent = max(utiles, key=lambda p: (str(p.get("end")), str(p.get("filed") or "")))
        flux = [est_point_de_flux(p) for p in utiles]
        nature = "flux" if all(flux) else ("instant" if not any(flux) else "mixte")
        unites = {str(p.get("unit")) for p in utiles}
        # Les DATES DISTINCTES, pas les points : `companyfacts` republie le même `end` à chaque
        # dépôt qui le reprend en comparatif, donc `len(utiles)` surestimerait la profondeur d'un
        # facteur 3 ou 4 et ferait lire « 40 dates » là où l'émetteur n'en a publié que 12.
        dates = {str(p.get("end")) for p in utiles}
        lignes.append(LigneInventaire(
            concept=concept,
            nature=nature,
            duree_jours=duree_jours(recent),
            # `is_annual_flow` est appelé, jamais réécrit (#46) : c'est LUI qui tient « ce point
            # couvre-t-il un exercice ? », avec ses bornes mesurées. Sans cette colonne, le rendu
            # MENTIRAIT par omission — `Revenues` dont le point le plus récent est un semestre se
            # lirait comme une métrique semestrielle, alors que le concept porte aussi l'annuel.
            # Le COMPTE et non plus un booléen : « un exercice annuel existe » ne dit pas si la
            # question « cinq exercices » est servable, et c'est cette question-là que le plan pose.
            nb_exercices=len({str(p.get("end")) for p in utiles if is_annual_flow(p)}),
            unite=str(recent.get("unit")),
            dernier_end=str(recent.get("end")),
            premier_end=min(dates),
            nb_dates=len(dates),
            derniere_valeur=float(recent["val"]),
            nb_points=len(points),
            autres_unites=len(unites) - 1,
        ))
    return lignes


def _valeur_lisible(v: float) -> str:
    """Un montant qui se lit d'un coup d'œil. Séparateurs de milliers : c'est l'ORDRE DE GRANDEUR
    qui permet au modèle de reconnaître un total de bilan d'une ligne de détail."""
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:g}"


# La LÉGENDE des colonnes, séparée du rendu et non dedans : le rendu doit rester une ligne par
# concept, relisible par son premier mot — c'est ce qui permet de vérifier sa TOTALITÉ en comparant
# les noms relus aux clefs de l'inventaire. Une légende insérée dans la table serait une ligne qui
# n'est pas un concept, et le contrôle de totalité se mettrait à compter une intruse.
LEGENDE_INVENTAIRE = (
    "colonnes : CONCEPT · CADRAGE · date et valeur du point le PLUS RÉCENT de ce concept · unité · "
    "PROFONDEUR de la série.\n"
    "  · `instant` = solde à une date (poste de bilan). `flux Nj` = montant couvrant N jours ; "
    "`+A×K` signale que K exercices ANNUELS distincts sont déposés pour ce concept, même si le point "
    "le plus récent est plus court. `mixte` = déposé dans les deux cadrages. `aucun point "
    "exploitable` = nommable, mais rien de chiffré à relever.\n"
    "  · LA TABLE NE MONTRE QU'UN POINT PAR CONCEPT — le plus récent. La colonne de profondeur "
    "(`N dates depuis AAAA-MM-JJ`) dit ce que l'émetteur a déposé D'AUTRE sur ce même concept, et "
    "TOUT cet historique est récupérable. Ne conclus donc JAMAIS à l'absence de série pluriannuelle "
    "depuis cette table : un concept marqué `12 dates depuis 2013-06-30` sert une question sur cinq "
    "exercices, et `+A×5` le sert au grain annuel. Un `indisponible` motivé par « pas de série » est "
    "faux si la profondeur est là.\n"
    "  · LA DATE DU DERNIER POINT EST DÉCISIVE. Un concept dont le dernier point est très antérieur "
    "à la période ci-dessus n'est PLUS ALIMENTÉ : l'émetteur a changé d'étiquette. Le nommer ne rend "
    "aucune erreur — il rend un vide, ou un nombre vieux de plusieurs années."
)


def rendre_inventaire(lignes: list[LigneInventaire]) -> str:
    """L'inventaire en TEXTE ALIGNÉ, pas en JSON. Déterministe.

    Le choix du texte n'est pas cosmétique : le même contenu en JSON coûte ~3× les jetons (une clef
    répétée par champ et par concept) et se lit moins bien en colonnes. Le contexte du modèle est donc
    MIXTE — les ingrédients en JSON (ils se répondent en JSON), l'inventaire en table.

    Une ligne par concept, le nom EN PREMIER : c'est ce qui rend la table relisible, donc vérifiable.
    """
    out = []
    for l in lignes:
        if l.nature == "sans_point":
            out.append(f"  {l.concept:<58} aucun point exploitable ({l.nb_points} point(s) déposé(s))")
            continue
        cadre = l.nature if l.duree_jours is None else f"{l.nature} {l.duree_jours}j"
        if l.nb_exercices:
            cadre += f"+A×{l.nb_exercices}"
        # La profondeur est imprimée MÊME quand elle vaut 1 : « 1 seule date » est l'information qui
        # rend un `indisponible` LÉGITIME sur une question pluriannuelle. L'omettre dans ce cas
        # laisserait le modèle deviner, et c'est précisément la devinette qu'on lui retire.
        profondeur = (f"  · {l.nb_dates} dates depuis {l.premier_end}" if l.nb_dates > 1
                      else "  · 1 seule date")
        suffixe = f"  [+{l.autres_unites} autre(s) unité(s)]" if l.autres_unites else ""
        out.append(f"  {l.concept:<58} {cadre:<18} {l.dernier_end}  "
                   f"{_valeur_lisible(l.derniere_valeur):>20} {l.unite}{profondeur}{suffixe}")
    return "\n".join(out)


def derniere_periode_vue(facts: dict[str, list[dict[str, Any]]], *,
                         aujourdhui: Optional[date] = None) -> Optional[str]:
    """La période la plus récente que l'inventaire couvre (max `end`), bornée à aujourd'hui.

    C'est la RÉFÉRENCE contre laquelle une date de dernier point se lit. Sans elle, la colonne de
    date de `rendre_inventaire` n'est qu'un nombre : le modèle ne peut pas savoir si `2025-10-26` est
    frais ou mort. Avec elle, la faute dominante mesurée sur l'inventaire de NVDA devient LISIBLE —
    l'émetteur dépose une vingtaine de concepts au nom quasi identique (`AvailableForSaleSecurities`,
    `...AmortizedCost`, `...DebtMaturitiesFairValue`…) dont la plupart sont arrêtés en 2015-2020, et
    l'un d'eux, vivant, porte le vrai nombre. Ce n'est PAS la faute que `[V]` attrape : ces concepts
    sont réellement déposés, donc un nom mort traverse le pont sans une alerte et la collecte
    remontera un vide (ou, via `select_concept`, rien du tout).

    Bornée à aujourd'hui parce qu'un `end` peut être postérieur au dépôt (échéancier de dette,
    période comparative) : une référence dans le futur ferait paraître périmé tout l'inventaire.
    Rend None si aucun `end` n'est lisible — l'appelant décide alors, plutôt que de recevoir une
    date fabriquée qui se lirait comme une mesure.
    """
    limite = aujourdhui or date.today()
    ends = []
    for points in facts.values():
        for p in points:
            e = p.get("end")
            if not e:
                continue
            try:
                d = date.fromisoformat(str(e))
            except (TypeError, ValueError):
                continue
            if d <= limite:
                ends.append(d.isoformat())
    return max(ends) if ends else None


def dernier_depot_vu(facts: dict[str, list[dict[str, Any]]]) -> str:
    """La date du DÉPÔT le plus récent de l'inventaire (ISO) — ce qui rend la carte révisable (#54).

    C'est le `filed` maximum, et non le `end` maximum, pour deux raisons qui se mesurent :

      · un 10-K/A rectificatif peut AJOUTER des concepts en gardant la même clôture. Le `end`
        maximum, lui, n'aurait pas bougé : la carte se relirait comme à jour et continuerait de router
        au web des ingrédients devenus tier A — le VERT qui masque la perte ;
      · un `end` peut être postérieur au dépôt (échéancier, période comparative), donc figer une
        borne qu'aucun dépôt réel ne franchira.

    Le nom du champ dit exactement ce qu'on stocke : le dernier DÉPÔT vu, pas la dernière période
    vue. Lève plutôt que de rendre une chaîne vide : une date absente ferait une carte que la
    revérification à la lecture ne saurait pas dater, donc qu'elle accepterait pour toujours.
    """
    deposes = []
    for points in facts.values():
        for p in points:
            f = p.get("filed")
            if not f:
                continue
            try:
                deposes.append(date.fromisoformat(str(f)).isoformat())
            except (TypeError, ValueError):
                continue
    if not deposes:
        raise AppariementSansObjet(
            "inventaire sans aucune date de dépôt (`filed`) lisible : c'est un défaut de "
            "récupération, jamais un émetteur muet (même lecture que `EdgarUnavailable`). Sans date, "
            "la carte ne pourrait plus se revérifier à la lecture — elle serait valable pour toujours")
    return max(deposes)


def lignes_a_apparier(plan: CollectionPlan) -> list[CollectionPlanItem]:
    """Les lignes du plan qui ATTENDENT un appariement — les `traduit`, et elles seules. Pur.

    Miroir exact de [S] et [T] : le pont refuse un appariement posé sur une ligne `inobtenable` [S],
    et refuse une carte qui omet une seule ligne `traduit` [T]. Montrer au modèle une ligne
    `inobtenable`, ou lui cacher une `traduit`, fabriquerait un refus dont il ne pouvait pas sortir —
    et le taux de refus mesurerait alors notre contexte, pas son appariement.

    Même discipline que `analyste.statuts_admissibles` : ce que le pont refusera se CALCULE avant la
    dépense et se publie en vocabulaire fermé, au lieu d'être laissé au modèle à deviner.
    """
    return [it for it in plan.items if it.statut == "traduit"]


def contexte_apparieur(plan: CollectionPlan, facts: dict[str, Any]) -> dict[str, Any]:
    """CE QUE LE MODÈLE VOIT, côté ingrédients — lever-free, et sans l'en-tête qu'il ne pose pas.

    Ne porte QUE le ticker, l'identité du framework, et pour chaque ligne `traduit` son couple
    (question, ingrédient) et la `metrique` — c'est-à-dire le nom que le traducteur a donné à
    l'ingrédient DANS LE VOCABULAIRE DE CETTE ENTREPRISE. C'est la seule chose dont l'appariement a
    besoin : « ce que cette société appelle ainsi, quel(s) champ(s) déposé(s) y répondent ? »

    Sont volontairement ABSENTS, chacun pour une raison qui se lit comme un mode de panne :

      · `poste` — le poste du catalogue que le traducteur avait cru reconnaître. Le montrer
        ré-ancrerait le modèle sur les 33 recettes de `POSTES`, qui est exactement la fenêtre que
        #67 rouvre ; et un `poste` FAUX (5 des 7 mesurés le 2026-09-14) deviendrait une suggestion ;
      · `source_pressentie` et `ancre` — ils disent où chercher sur le WEB et à quand dater le fait.
        Un appariement se décide contre le dépôt, quoi qu'ait pressenti le traducteur : montrer
        « communiqué trimestriel » ferait conclure `indisponible` sur un concept pourtant déposé ;
      · tout plancher/tier/nature attendue — même absence que dans le plan de collecte (#59). Le tier
        se DÉRIVE de `deterministe` (`derive_tier_calcul`, #67) ; le montrer inviterait le modèle à
        qualifier lui-même la fiabilité de ce qu'il vient de proposer.

    L'en-tête (ticker, framework, version, `dernier_depot_vu`) n'est pas ici non plus : il est posé
    par le CODE au moment de construire la carte, comme pour le plan de collecte (#57/#53). Un modèle
    qui daterait lui-même l'inventaire qu'il vient de lire pourrait affirmer une fraîcheur qu'il n'a
    pas vérifiée — et c'est cette date qui décide plus tard si la carte est encore valable.

    Ne prend PAS l'énoncé de la question du référentiel : le plan est autosuffisant par construction
    (le collecteur travaille déjà en aveugle sur la seule `metrique`, §3.6). L'ajouter serait une
    capacité décidée avant d'être mesurée (`feedback_decision_figee_a_remesurer`) ; si l'analyse des
    refus montre une dérive sémantique, ce sera le premier levier à essayer — et il se mesurera.
    """
    lignes = lignes_a_apparier(plan)
    if not lignes:
        raise AppariementSansObjet(
            f"le plan de {plan.ticker_id} · {plan.framework_id} ne porte aucune ligne `traduit` "
            f"({len(plan.items)} ligne(s), toutes `inobtenable`) : il n'y a rien à apparier, et une "
            "carte vide est refusée par le contrat (`items` non vide). Rien à payer ici")
    if not facts:
        raise AppariementSansObjet(
            "inventaire VIDE : un inventaire vide est un défaut de récupération, jamais un émetteur "
            "muet (#25). Apparier contre lui rendrait une carte tout `indisponible`, qui se relirait "
            "comme un émetteur qui ne publie rien — et qui PASSERAIT le pont")
    return {
        "ticker": plan.ticker_id,
        "framework": plan.framework_id,
        "ingredients": [
            {"question_id": it.question_id,
             "ingredient_id": it.ingredient_id,
             "metrique": it.metrique}
            for it in lignes
        ],
    }


def valider_pont_appariement(
    carte: AppariementCarte,
    inventaire: Collection[str],
    *,
    plan: Optional[CollectionPlan] = None,
) -> None:
    """Vérifie qu'une carte d'appariement est cohérente avec l'INVENTAIRE réel et avec son plan.
    Ne rend rien : le seul résultat possible est « pas de refus ».

    `inventaire` = les noms de concepts `us-gaap` RÉELLEMENT déposés par cet émetteur, tels que
    `edgar_facts.fetch_company_facts()` les rend. On le reçoit déjà lu plutôt que de l'aller chercher
    ici : le pont reste PUR, donc rejouable hors-ligne et testable sans réseau — la frontière
    gratuite avant toute dépense.

    `plan` est facultatif pour que la carte puisse se valider seule contre l'inventaire (le cas de la
    REVÉRIFICATION À LA LECTURE, où le plan n'est pas forcément rechargé). Quand il est fourni, les
    invariants relationnels [S]/[T]/[U] s'y ajoutent.

    Les invariants, chacun gardant un mode de panne qui se lit comme un succès :

      U. la carte et le plan parlent du MÊME (ticker, framework, version). Une carte appliquée au
         plan d'une autre version apparie des ingrédients qui ont pu changer de sens ;
      S. chaque appariement correspond à une ligne `traduit` du plan. Apparier une ligne
         `inobtenable` est une contradiction : le plan a déjà établi qu'aucune source ne la produit ;
      T. chaque ligne `traduit` a un appariement. Une omission n'est pas un trou — c'est la carte qui
         est REFUSÉE. Un ingrédient sans appariement repart au web en silence, donc en tier B, pour
         un niveau brut que la SEC publie en tier A : le VERT qui masque la perte ;
      V. LE CŒUR — chaque concept nommé est DÉPOSÉ par CET émetteur. C'est la garde absente de
         `poste_retenu()`, et la seule qui ne puisse pas se remplacer par une formulation ;
      W. la formule ne référence QUE des concepts déclarés, et les déclare TOUS. Un concept présent
         dans la seule formule échapperait à [V] ; un concept déclaré et jamais utilisé fait compter
         au tier un ingrédient qui n'entre pas dans le calcul ;
      X. `deterministe=True` interdit un coefficient décimal visible dans la formule.
    """
    if not inventaire:
        raise AppariementRefuse(
            "[V] inventaire VIDE : un inventaire vide est un défaut de récupération, jamais un "
            "émetteur muet (même lecture que `EdgarUnavailable`). Valider une carte contre un "
            "inventaire vide refuserait tous les concepts, et la carte se relirait comme un émetteur "
            "qui ne publie rien")
    depose = set(inventaire)

    if plan is not None:
        # U. même sujet, même version.
        if (carte.ticker_id, carte.framework_id, carte.framework_version) != (
                plan.ticker_id, plan.framework_id, plan.framework_version):
            raise AppariementRefuse(
                f"[U] la carte porte sur ({carte.ticker_id}, {carte.framework_id}, "
                f"{carte.framework_version}) et le plan sur ({plan.ticker_id}, {plan.framework_id}, "
                f"{plan.framework_version}) : une carte appariée contre un autre plan décrit des "
                "ingrédients qui ont pu changer de sens entre deux versions")

        traduits = {(it.question_id, it.ingredient_id)
                    for it in plan.items if it.statut == "traduit"}
        inobtenables = {(it.question_id, it.ingredient_id)
                        for it in plan.items if it.statut == "inobtenable"}

        # S. on n'apparie que ce que le plan a dit chercher.
        for it in carte.items:
            couple = (it.question_id, it.ingredient_id)
            if couple in inobtenables:
                raise AppariementRefuse(
                    f"[S] `{it.question_id}.{it.ingredient_id}` est `inobtenable` au plan et porte "
                    f"pourtant un appariement `{it.statut}` : le plan a établi qu'aucune source "
                    "connue ne produit cet ingrédient ; lui trouver un champ déposé contredit le "
                    "motif qui l'accompagne, et l'un des deux est faux")
            if couple not in traduits:
                raise AppariementRefuse(
                    f"[S] `{it.question_id}.{it.ingredient_id}` est apparié sans ligne au plan : un "
                    "appariement qui ne s'indexe sur aucune ligne relie un champ déposé à rien, et "
                    "sa collecte ne rejoindra aucune question")

        # T. et on apparie TOUT ce que le plan a dit chercher.
        apparies = {(it.question_id, it.ingredient_id) for it in carte.items}
        manquants = sorted(traduits - apparies)
        if manquants:
            raise AppariementRefuse(
                f"[T] {len(manquants)} ligne(s) `traduit` du plan n'ont AUCUN appariement "
                f"{manquants[:5]} : une omission n'est pas un trou, c'est une carte REFUSÉE. Un "
                "ingrédient sans appariement repart chercher au web, en tier B, un niveau brut que "
                "la SEC publie en tier A — et la couverture restera à 100 % sur ce qui reste")

    # V + W + X. le réel, ligne par ligne.
    for it in carte.items:
        _valider_ligne(it, depose)


def _valider_ligne(it: AppariementItem, depose: set[str]) -> None:
    """Les trois invariants qui ne regardent QUE la ligne et l'inventaire. Séparé pour que la
    revérification à la lecture (#54) puisse l'appeler ligne à ligne sans recharger un plan."""
    ou = f"`{it.question_id}.{it.ingredient_id}`"

    # V. LE CŒUR. Chaque concept nommé est déposé par CET émetteur.
    absents = sorted(c for c in it.concepts if c not in depose)
    if absents:
        raise AppariementRefuse(
            f"[V] {ou} nomme {absents}, que cet émetteur NE DÉPOSE PAS (inventaire de "
            f"{len(depose)} concepts). Un nom voisin d'un concept réel est le mode de panne d'un "
            "adressage par nom sans outil de lecture : il produit un appariement d'apparence "
            "normale, et la collecte remontera un vide ou un autre nombre")

    if it.statut != "approximation":
        return
    assert it.formule is not None  # garanti par le contrat : `approximation` ⟹ formule

    # W. la formule et les concepts déclarés disent la même chose.
    refs = concepts_de_la_formule(it.formule)
    declares = set(it.concepts)
    hors_declaration = sorted(refs - declares)
    if hors_declaration:
        raise AppariementRefuse(
            f"[W] {ou} référence {hors_declaration} dans sa formule sans les déclarer en "
            f"`concepts` : un concept qui n'existe que dans la formule échappe à la confrontation "
            "avec l'inventaire [V] — c'est la porte dérobée par laquelle un concept inventé "
            "rentrerait quand même dans le calcul")
    inutilises = sorted(declares - refs)
    if inutilises:
        raise AppariementRefuse(
            f"[W] {ou} déclare {inutilises} sans les employer dans sa formule : un ingrédient qui "
            "n'entre pas dans le calcul pèse quand même sur le tier dérivé (#67 lit le plus FAIBLE "
            "des ingrédients) — il ferait monter ou descendre la fiabilité d'un nombre auquel il ne "
            "contribue pas")

    # X. un déterminisme déclaré ne survit pas à un coefficient visible.
    if it.deterministe:
        coefs = coefficients_choisis(it.formule)
        if coefs:
            raise AppariementRefuse(
                f"[X] {ou} se déclare `deterministe` mais sa formule porte {coefs} : un coefficient "
                "décimal est un paramètre CHOISI, donc un calcul non déterministe — il descend d'un "
                "cran (#67). C'est exactement ce qui sépare `capital_employe` (une soustraction de "
                "postes déposés) de `investissement_de_maintien` (« la PART du capex nécessaire au "
                "maintien »), et le confondre rendrait une estimation en tier A")


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# L'AGENT — le modèle PROPOSE, le pont VÉRIFIE, et le refus devient un OUTIL DE LECTURE
# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Un refus sec ne corrige rien : un modèle à qui l'on dit « ce concept n'existe pas » sur un
# inventaire de 627 noms réessaie un autre nom voisin, ou se replie sur `indisponible` partout. Le
# second cas est le plus dangereux, parce qu'il n'est JAMAIS refusé : le taux de refus tomberait à
# zéro pendant que la collecte se viderait — c'est pourquoi ce taux ne se lit jamais seul, mais
# TOUJOURS avec la distribution des trois états (cf. `tools/acceptation_apparieur.py`).
#
# D'où la forme du tour de réparation : le code LISTE les noms réellement déposés qui partagent un
# mot avec le nom absent, et le modèle DÉCIDE. Ce n'est pas la liste partielle que
# `feedback_adressage_par_nom_exige_lecture` interdit — l'inventaire ENTIER reste dans la
# conversation, juste au-dessus ; cette liste-ci ne restreint rien, elle pointe.

class AppariementSortie(Strict):
    """Ce que le MODÈLE produit — rien que les lignes. L'en-tête (ticker, framework, version,
    `dernier_depot_vu`) est posé par le code, jamais par le modèle : la date de dépôt est ce qui
    décidera plus tard si la carte est encore valable, et un modèle qui daterait lui-même
    l'inventaire qu'il vient de lire affirmerait une fraîcheur qu'il n'a pas vérifiée (#57/#53)."""
    items: list[AppariementItem] = Field(min_length=1)


class Appariement(NamedTuple):
    """Ce qu'un appariement rend : la carte VALIDÉE, la télémétrie, et les refus qu'il a fallu
    réparer. Les refus sont rendus plutôt que jetés : c'est la seule mesure du taux d'invention, et
    un échec qui ne se compte pas est un échec qu'on ne cherche pas à réduire."""
    run: AgentRunResult
    carte: AppariementCarte
    refus_repares: list[str]


def mots_du_concept(concept: str) -> set[str]:
    """Les mots d'un nom XBRL en CamelCase, en minuscules. Pur — `InventoryNetCurrent` →
    {inventory, net, current}. Sert à POINTER des voisins déposés, jamais à choisir à la place."""
    return {m.lower() for m in re.findall(r"[A-Z][a-z0-9]*|[a-z0-9]+", concept)}


def voisins_deposes(absent: str, inventaire: Collection[str], *, limite: int = 12) -> list[str]:
    """Les concepts RÉELLEMENT déposés qui partagent au moins un mot avec un nom absent. Pur.

    Classés par nombre de mots communs décroissant, puis par ordre alphabétique — donc déterministe,
    et rejouable hors-ligne. Aucune notion de « meilleur » candidat : ce serait faire l'appariement à
    la place du modèle, et sur un critère lexical, c'est-à-dire exactement la table de sous-chaînes
    dont la mesure du 2026-09-14 a montré qu'elle produisait 5 faux appariements sur 7.
    """
    cibles = mots_du_concept(absent)
    if not cibles:
        return []
    scores = []
    for c in inventaire:
        communs = len(cibles & mots_du_concept(c))
        if communs:
            scores.append((-communs, c))
    return [c for _, c in sorted(scores)[:limite]]


def concepts_absents(carte: AppariementCarte, inventaire: Collection[str]) -> list[str]:
    """Les concepts nommés par la carte que l'inventaire ne porte pas. Pur.

    N'est PAS un second juge : le verdict reste celui de `valider_pont_appariement` [V], appelé
    avant. Cette fonction ne sert qu'à NOMMER de quoi il faut aider le modèle, et elle n'est lue
    qu'après un refus — si elle divergeait de [V], elle rendrait une aide vide, jamais un passage.
    """
    depose = set(inventaire)
    return sorted({c for it in carte.items for c in it.concepts if c not in depose})


_APPARIEUR_SYSTEM_PROMPT = (
    "Tu es l'APPARIEUR d'une chaîne d'analyse d'investissement. On te donne DEUX choses : la liste "
    "COMPLÈTE des champs comptables que CETTE entreprise-là dépose réellement auprès de la SEC "
    "(étiquettes us-gaap, avec leur cadrage, leur date et leur dernière valeur), et une liste "
    "d'ingrédients à collecter, chacun nommé dans le vocabulaire de cette entreprise. Pour CHAQUE "
    "ingrédient, tu dis quel(s) champ(s) déposé(s) y répondent, et à quel prix.\n\n"

    "LA TABLE EST TON SEUL VOCABULAIRE. Tout nom que tu écris dans `concepts` doit être RECOPIÉ "
    "caractère pour caractère depuis la table ci-dessus. Ne cite JAMAIS un nom de mémoire : cette "
    "entreprise dépose plusieurs centaines de champs, bien au-delà de ce que l'on retient, et les "
    "noms se ressemblent énormément (un même concept existe souvent en version `...Current`, "
    "`...Gross`, `...NetOfTax`, `...AmortizedCost`). Avant d'écrire un nom, RETROUVE-LE dans la "
    "table. Si tu ne le trouves pas, il n'existe pas POUR CET ÉMETTEUR — même s'il existe ailleurs, "
    "et même s'il serait le nom évident. Un nom absent fait refuser toute la carte.\n\n"

    "LA DATE COMPTE AUTANT QUE LE NOM. Un champ déposé peut être ABANDONNÉ : l'émetteur a changé "
    "d'étiquette il y a des années et la ligne reste dans la table, avec son dernier point daté de "
    "2015 ou 2018. Le nommer ne produit aucune erreur visible — il produit un vide, ou un nombre "
    "vieux de plusieurs années présenté comme actuel. Quand plusieurs champs au nom voisin "
    "conviendraient, prends celui dont le dernier point est proche de la période la plus récente "
    "indiquée, et ignore les autres.\n\n"

    "TROIS ÉTATS, ET LE MILIEU EST LE PLUS UTILE :\n"
    "  • `exact` — UN champ déposé, UN SEUL, répond tel quel. Le test, littéralement : « si je "
    "relève ce nombre et que je le recopie sans rien y ajouter ni en retrancher, ai-je répondu à "
    "l'ingrédient COMPLÈTEMENT et EXACTEMENT ? » Remplis `concepts` avec ce seul nom, et RIEN "
    "d'autre : pas de formule, pas d'hypothèse, pas de `deterministe`.\n"
    "  • `approximation` — il faut un CALCUL sur plusieurs champs déposés, ou une hypothèse. C'est "
    "le cas le plus fréquent d'un appariement bien fait, et ce n'est pas un aveu de faiblesse : "
    "c'est là que l'information passe. Remplis `concepts` (tous les champs employés), `formule` "
    "(écrite AVEC LES NOMS DE CHAMPS, par exemple une soustraction d'un total d'actif, des dettes "
    "courantes et de la trésorerie pour un capital employé), `hypotheses` (une PHRASE COMPLÈTE par "
    "hypothèse, celle qu'un lecteur pourra contester — « les placements à court terme sont assimilés "
    "à de la trésorerie »), et `deterministe`.\n"

    "`formule` EST UNE EXPRESSION DE CALCUL, PAS UNE PHRASE. Elle ne contient QUE des noms de "
    "champs recopiés de la table, des opérateurs (`+ - * / ( )`) et des nombres entiers de "
    "conversion. Aucun mot de français, aucune virgule d'énumération, aucun « Pour chaque… », aucune "
    "explication : tout ce qui s'explique va dans `hypotheses`, dont c'est exactement le rôle. Un "
    "mot commençant par une majuscule dans la formule est lu comme un nom de champ et sera cherché "
    "dans la table — une phrase y fait donc refuser toute la carte.\n"

    "UN INGRÉDIENT QUI DEMANDE PLUSIEURS EXERCICES (« sur cinq exercices consécutifs », « par "
    "exercice », « évolution de… ») ne demande PAS une formule par année. La table te dit, sur "
    "chaque champ, combien d'exercices annuels et combien de dates sont déposés : écris la formule "
    "de la relation UNE SEULE FOIS, avec les noms de champs, et dis dans une hypothèse qu'elle "
    "s'applique à chacun des exercices déposés (en citant leur nombre). Si la profondeur affichée "
    "suffit, l'ingrédient est servi — ce n'est pas un `indisponible`.\n"
    "  • `indisponible` — AUCUN champ déposé n'y contribue, même partiellement. Remplis `motif` "
    "(une phrase disant ce que tu as cherché dans la table et pourquoi rien ne convient) et rien "
    "d'autre.\n\n"

    "LES DEUX FAÇONS DE SE TROMPER, ET ELLES SE VALENT :\n"
    "  — déclarer `exact` un champ qui répond à une question VOISINE. Le nombre sera juste et hors "
    "sujet, et personne ne s'en apercevra : c'est la faute la plus grave. S'il faut additionner, "
    "soustraire, diviser, prendre une part, changer de période ou lire du texte à côté du nombre, "
    "alors ce n'est pas `exact`.\n"
    "  — déclarer `indisponible` parce qu'aucun champ ne répond À LUI SEUL. C'est la faute "
    "symétrique, et elle est invisible aussi : l'ingrédient part alors chercher sur le web un nombre "
    "que personne ne publie, alors que les termes du calcul étaient déposés. Avant tout "
    "`indisponible`, demande-toi si DEUX champs de la table, combinés, ne répondent pas.\n\n"

    "`deterministe` (obligatoire sur une `approximation`, interdit ailleurs) : vrai si la formule est "
    "FERMÉE — elle n'emploie que des champs déposés et des opérations, sans qu'on ait eu à CHOISIR un "
    "paramètre. Faux dès qu'il faut choisir : une part (« 60 % du capex est du maintien »), une "
    "durée, un taux normatif. N'écris jamais de pourcentage ni de coefficient décimal dans une "
    "formule déclarée déterministe — c'est contradictoire, et la carte sera refusée.\n\n"

    "`termes_web` (facultatif, seulement sur une `approximation`) : un terme du CALCUL que le dépôt "
    "ne porte pas et qu'il faudra chercher ailleurs. Ce n'est pas une excuse ni une note de bas de "
    "page : c'est un ingrédient manquant, nommé pour être collecté.\n\n"

    "TU NE JUGES PAS LA FIABILITÉ. Ni tier, ni score, ni niveau de confiance : la fiabilité se "
    "DÉDUIT de ce que tu déclares (les champs employés et `deterministe`), elle ne se déclare pas. "
    "N'ajoute aucun champ hors contrat.\n\n"

    "UNE LIGNE PAR INGRÉDIENT, TOUS LES INGRÉDIENTS. Reprends `question_id` et `ingredient_id` tels "
    "quels — n'en invente aucun, n'en omets aucun : une omission fait refuser toute la carte. Sortie : "
    "UNIQUEMENT l'objet JSON `{\"items\": [ ... ]}`, commençant par `{` et finissant par `}`, sans "
    "aucun texte autour."
)


def message_apparieur(contexte: dict[str, Any], inventaire_texte: str,
                      *, derniere_periode: Optional[str]) -> str:
    """Le message utilisateur : les ingrédients en JSON, l'inventaire en table. Déterministe.

    La période la plus récente est posée par le CODE, jamais demandée au modèle : c'est la référence
    contre laquelle il lit les dates de la table, et un modèle qui daterait lui-même l'inventaire
    qu'il vient de lire affirmerait une fraîcheur qu'il n'a pas vérifiée (#57, et
    `feedback_agent_sans_horloge` : sans date fournie, un modèle date « aujourd'hui » à sa coupure).
    """
    periode = (f"Période la plus récente couverte par ce dépôt : {derniere_periode}.\n"
               if derniere_periode else "")
    return (
        "[mode: appariement]\n\n"
        f"Ingrédients à apparier (chacun attend exactement une ligne) :\n"
        f"{json.dumps(contexte, ensure_ascii=False, indent=2)}\n\n"
        f"CHAMPS DÉPOSÉS PAR {contexte['ticker']} — c'est la liste COMPLÈTE, et ton seul vocabulaire "
        f"pour `concepts`.\n{periode}{LEGENDE_INVENTAIRE}\n\n"
        f"{inventaire_texte}\n\n"
        "Produis l'objet JSON `{\"items\": [ ... ]}` : une ligne par ingrédient ci-dessus, avec son "
        "`question_id`, son `ingredient_id`, et son `statut` (`exact` avec UN concept recopié de la "
        "table ; `approximation` avec concepts + formule + hypothèses + `deterministe` ; "
        "`indisponible` avec motif). Chaque nom de `concepts` doit se retrouver à l'identique dans la "
        "table ci-dessus."
    )


def message_reparation(refus: str, absents: list[str], inventaire: Collection[str]) -> str:
    """Le tour de réparation : le refus du pont, PUIS les noms déposés qui pointent vers l'absent.

    Le refus est réinjecté tel quel — il est écrit pour être lu, il nomme l'invariant et le mode de
    panne. S'y ajoute, pour chaque nom absent, la liste des concepts DÉPOSÉS qui partagent un mot
    avec lui : le code liste, le modèle décide. Aucune suggestion de remplacement, aucun « le plus
    proche est » — sur un critère lexical, ce serait la table de sous-chaînes qui fabriquait 5 faux
    appariements sur 7 (mesure du 2026-09-14).
    """
    aide = ""
    for nom in absents:
        voisins = voisins_deposes(nom, inventaire)
        aide += (f"\n  `{nom}` n'est pas déposé. Champs déposés partageant un mot avec lui "
                 f"(recopie l'un d'eux s'il répond, sinon passe en `indisponible` avec un motif) :\n"
                 + ("".join(f"      · {v}\n" for v in voisins)
                    if voisins else "      (aucun — ce nom n'a aucun équivalent chez cet émetteur)\n"))
    return (
        "Ta carte a été REFUSÉE par la vérification contre le dépôt réel. Le motif, mot pour mot :\n\n"
        f"{refus}\n"
        + (f"\nPOUR T'AIDER À RELIRE LA TABLE (elle est inchangée, ci-dessus) :{aide}" if aide else "")
        # Rappelé INCONDITIONNELLEMENT, et non conditionné à ce que le motif ressemble à `[W]` :
        # un `if "[W]" in refus` ferait dépendre la réparation du LIBELLÉ d'un invariant de l'étape
        # 1, donc se romprait en silence à la première reformulation. Ce rappel est vrai dans tous
        # les cas, il ne coûte que deux lignes, et il nomme la faute que le motif décrit mal : le
        # pont dit « concept non déclaré » là où la cause est souvent « une phrase dans `formule` ».
        + "\nRAPPEL DE FORME : `formule` ne contient QUE des noms de champs recopiés de la table, "
          "des opérateurs et des entiers — jamais un mot de français, jamais une énumération, "
          "jamais une explication (elle va dans `hypotheses`). Tout mot à majuscule y est cherché "
          "dans la table comme un nom de champ.\n"
        + "\nRenvoie l'objet JSON COMPLET corrigé — tous les ingrédients, pas seulement les lignes "
          "fautives."
    )


async def _resolve_apparieur_agent() -> ResolvedAgent:
    """Réutilise provider + modèle de l'ingestion-agent (config en DB, source de vérité), avec le
    prompt système de l'APPARIEUR. Même montage que le traducteur et la synthèse (#54) : le prompt de
    ce mode vit dans le code tant qu'aucune migration ne l'exige."""
    base = await get_agent_provider("ingestion-agent", "v2")
    return ResolvedAgent(
        agent_name="ingestion-agent",
        flow_version="v2",
        provider=base.provider,
        model=base.model,
        system_prompt=_APPARIEUR_SYSTEM_PROMPT,
    )


def _cumuler(premier: AgentRunResult, second: AgentRunResult) -> AgentRunResult:
    """La télémétrie des DEUX tours, portée par le second. Un tour de réparation est facturé comme un
    succès : le compter pour zéro rendrait le coût du taux d'invention invisible, donc jamais réduit."""
    return replace(
        second,
        tokens_in=premier.tokens_in + second.tokens_in,
        tokens_out=premier.tokens_out + second.tokens_out,
        cost_usd=premier.cost_usd + second.cost_usd,
        attempts=premier.attempts + second.attempts,
    )


async def apparier(
    plan: CollectionPlan,
    facts: dict[str, list[dict[str, Any]]],
    *,
    agent: Optional[ResolvedAgent] = None,
) -> Appariement:
    """Produit et VALIDE la carte d'appariement d'un (ticker × framework × version).

    `facts` arrive DÉJÀ LU (`edgar_facts.fetch_company_facts`) : l'appariement reste ainsi rejouable
    sur un inventaire figé, et l'appelant garde la main sur le seul appel réseau. C'est la même
    frontière que celle du pont, pour la même raison.

    Ordre : (1) refuser le sans-objet AVANT toute dépense (#40) ; (2) assembler le contexte et la
    table ; (3) le modèle produit les LIGNES ; (4) le CODE pose l'en-tête et construit la carte ;
    (5) le pont contre le RÉEL — et un refus ouvre UN tour de réparation, pas plus.

    Pourquoi un seul tour : le nombre de réparations est le SIGNAL qu'on mesure (taux d'invention de
    noms). En autoriser plusieurs le diluerait jusqu'à ce que « ça finit par passer » remplace « ça
    passe », et masquerait exactement ce que l'étape 2a doit chiffrer avant de durcir quoi que ce
    soit. Un second refus lève : une carte à moitié valide ferait router au web des ingrédients dont
    on croirait avoir vérifié l'appariement.
    """
    contexte = contexte_apparieur(plan, facts)          # (1) lève AppariementSansObjet, sans dépense
    depot = dernier_depot_vu(facts)                     # (1) idem : une carte non datable est inutile
    inventaire_texte = rendre_inventaire(resumer_inventaire(facts))  # (2)
    message = message_apparieur(contexte, inventaire_texte,
                                derniere_periode=derniere_periode_vue(facts))
    agent = agent or await _resolve_apparieur_agent()

    def construire(items: list[AppariementItem]) -> AppariementCarte:
        """(4) L'en-tête est un fait de la requête, pas un jugement de modèle : le code le pose."""
        return AppariementCarte(
            ticker_id=plan.ticker_id,
            framework_id=plan.framework_id,
            framework_version=plan.framework_version,
            dernier_depot_vu=depot,
            items=items,
        )

    convo: list[dict[str, Any]] = [{"role": "user", "content": message}]
    # json_object=False : DeepSeek-V4-Flash est non fiable en mode json_object (cf. run_json_agent).
    run = await run_json_agent(agent, convo, AppariementSortie, json_object=False)  # (3)

    refus_repares: list[str] = []
    try:
        carte = construire(run.parsed.items)
        valider_pont_appariement(carte, facts.keys(), plan=plan)                    # (5)
        return Appariement(run=run, carte=carte, refus_repares=refus_repares)
    except (AppariementRefuse, ValidationError) as premier_refus:
        # Un `ValidationError` ici ne vient PAS du contrat de ligne (le runner l'a déjà réparé) : il
        # vient du validateur de la CARTE — un ingrédient apparié deux fois. Même traitement, parce
        # que c'est la même faute du point de vue du modèle : une carte qui se contredit.
        motif = str(premier_refus)
        refus_repares.append(motif)

    absents = []
    try:
        absents = concepts_absents(construire(run.parsed.items), facts.keys())
    except ValidationError:
        pass  # carte inconstructible (doublon) : le motif suffit, il n'y a pas de nom à pointer
    convo = convo + [
        {"role": "assistant", "content": run.raw_content},
        {"role": "user", "content": message_reparation(motif, absents, facts.keys())},
    ]
    run2 = _cumuler(run, await run_json_agent(agent, convo, AppariementSortie, json_object=False))
    carte = construire(run2.parsed.items)
    valider_pont_appariement(carte, facts.keys(), plan=plan)  # un second refus LÈVE, il ne dégrade pas
    return Appariement(run=run2, carte=carte, refus_repares=refus_repares)
