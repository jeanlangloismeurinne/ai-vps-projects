"""Le LECTEUR XBRL pur — instance, étiquettes, hiérarchie. AUCUN réseau ici (lot M2, spec §3).

Mesuré (2026-10-21, Opus) : la page rendue (`R#.htm`) met en forme pour un humain (en-têtes, mise à
l'échelle, colonnes) ; l'instance porte les faits EXACTS, sans mise en forme — chaque fait est un
concept, une période (durée ou instant), des MEMBRES EXPLICITES par AXE, une unité, une valeur. C'est
elle qu'on lit, trouvée par l'index du dépôt (`.../index.json`, suffixes `_htm.xml`/`_lab.xml`/
`_def.xml`) — jamais `FilingSummary.xml` ni `R#.htm`.

⚠️ Un filer peut ne PAS produire de `_lab.xml`/`_def.xml` séparés (mesuré sur RVMD 10-K
`0001193125-26-071563` : l'index ne porte que l'instance et un `.xsd` de 1,9 Mo) — les linkbases de
labels et de définitions sont alors EMBARQUÉES dans l'`.xsd` lui-même (un `<xsd:annotation>
<xsd:appinfo>` qui contient le `<link:linkbase>`). `lire_etiquettes`/`lire_hierarchie` sont AGNOSTIQUES
au conteneur : elles cherchent les éléments `link:loc`/`link:label`/`link:labelArc`/`link:definitionArc`
par leur nom local, où qu'ils soient dans l'arbre — elles lisent donc un `.xsd` embarqué exactement
comme un `_lab.xml`/`_def.xml` séparé. C'est à l'appelant (le fetch réseau, `ventilation_feed.py` /
`tools/extraire_fixture_ventilation.py`) de choisir le bon fichier dans l'index ; ce module ne choisit
jamais sa source, il la LIT.

`ElementTree` (bibliothèque standard, n'interprète pas les entités externes) ; aucun réseau ici.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from xml.etree import ElementTree as ET

_NS_XLINK = "http://www.w3.org/1999/xlink"
_NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
_NS_XBRLDI = "http://xbrl.org/2006/xbrldi"


def _local(tag: str) -> str:
    """Nom local d'une balise Clark-notée (`{uri}Local` → `Local`)."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _xlink(el, attr: str) -> Optional[str]:
    return el.get(f"{{{_NS_XLINK}}}{attr}")


@dataclass(frozen=True)
class FaitDimensionne:
    """Un fait de l'instance, après résolution du préfixe de son concept. `membres` est un tuple
    TRIÉ de (axe, membre) explicites — déjà au format `prefixe:Nom` (le préfixe des AXES/MEMBRES
    vient de l'attribut XML, écrit par le générateur SEC avec les MÊMES préfixes que ceux déclarés
    en tête d'instance ; celui du CONCEPT, lui, est résolu depuis l'espace de noms de sa balise —
    `ElementTree` la rend en Clark notation, jamais en texte préfixé)."""

    concept: str
    debut: Optional[str]
    fin: Optional[str]
    instant: Optional[str]
    membres: tuple[tuple[str, str], ...]
    unite: str
    valeur: float
    decimales: Optional[int]


def _namespaces(xml: bytes) -> dict[str, str]:
    """URI → préfixe, tel que DÉCLARÉ dans ce document (premier préfixe rencontré par URI)."""
    out: dict[str, str] = {}
    import io

    for _, (prefix, uri) in ET.iterparse(io.BytesIO(xml), events=("start-ns",)):
        if prefix and uri not in out:
            out[uri] = prefix
    return out


def _qname(tag: str, ns_map: dict[str, str]) -> Optional[str]:
    if not tag.startswith("{"):
        return tag
    uri, local = tag[1:].split("}", 1)
    prefix = ns_map.get(uri)
    return f"{prefix}:{local}" if prefix else None


def _unit_label(unit_el) -> str:
    """Le libellé d'une unité XBRL : `USD`, `shares`, `USD/shares`… Pur."""
    for child in unit_el:
        if _local(child.tag) == "measure":
            txt = (child.text or "").strip()
            return txt.rsplit(":", 1)[-1] if ":" in txt else txt
    # Une unité composée (`divide`, ex. USD/shares) : numérateur et dénominateur par nom local.
    num_txt = den_txt = None
    for child in unit_el:
        if _local(child.tag) != "divide":
            continue
        for sub in child:
            label = _local(sub.tag)
            measures = [c for c in sub if _local(c.tag) == "measure"]
            txt = (measures[0].text or "").strip() if measures else ""
            txt = txt.rsplit(":", 1)[-1] if ":" in txt else txt
            if label == "unitNumerator":
                num_txt = txt
            elif label == "unitDenominator":
                den_txt = txt
    if num_txt and den_txt:
        return f"{num_txt}/{den_txt}"
    return unit_el.get("id") or ""


def lire_instance(xml: bytes) -> list[FaitDimensionne]:
    """Les faits DIMENSIONNÉS de l'instance. Pur, aucun réseau.

    Ignore : les faits sans `contextRef` (pas des faits — des éléments de présentation du même nom
    n'existent pas dans une instance XBRL, donc ce cas ne se produit qu'en pratique pour les nœuds
    `context`/`unit`/`schemaRef` eux-mêmes, filtrés par construction ci-dessous) ; les contextes
    portant un `typedMember` (axe TYPÉ : pas une ventilation, §3) — le fait entier est écarté, pas
    seulement sa dimension typée, pour ne jamais lui laisser l'air d'un fait à exactement un axe
    retenu ; les valeurs non numériques ; `xsi:nil` (jamais lu comme 0, #47).
    """
    ns_map = _namespaces(xml)
    root = ET.fromstring(xml)

    contexts: dict[str, tuple[Optional[str], Optional[str], Optional[str]]] = {}
    membres: dict[str, tuple[tuple[str, str], ...]] = {}
    typed: set[str] = set()
    for ctx in root:
        if _local(ctx.tag) != "context":
            continue
        cid = ctx.get("id")
        if cid is None:
            continue
        debut = fin = instant = None
        dims: list[tuple[str, str]] = []
        a_type = False
        for el in ctx.iter():
            tag = _local(el.tag)
            if tag == "startDate":
                debut = (el.text or "").strip() or None
            elif tag == "endDate":
                fin = (el.text or "").strip() or None
            elif tag == "instant":
                instant = (el.text or "").strip() or None
            elif tag == "explicitMember":
                axe = el.get("dimension")
                membre = (el.text or "").strip()
                if axe and membre:
                    dims.append((axe, membre))
            elif tag == "typedMember":
                a_type = True
        contexts[cid] = (debut, fin, instant)
        if a_type:
            typed.add(cid)
        else:
            membres[cid] = tuple(sorted(dims))

    units: dict[str, str] = {}
    for u in root:
        if _local(u.tag) == "unit" and u.get("id"):
            units[u.get("id")] = _unit_label(u)

    out: list[FaitDimensionne] = []
    for el in root:
        ctx_ref = el.get("contextRef")
        if ctx_ref is None or ctx_ref not in contexts:
            continue
        if ctx_ref in typed:
            continue
        if el.get(f"{{{_NS_XSI}}}nil") == "true":
            continue
        texte = (el.text or "").strip()
        if not texte:
            continue
        try:
            valeur = float(texte)
        except ValueError:
            continue
        concept = _qname(el.tag, ns_map)
        if concept is None:
            continue
        decimales_brut = el.get("decimals")
        decimales = None
        if decimales_brut is not None and decimales_brut != "INF":
            try:
                decimales = int(decimales_brut)
            except ValueError:
                decimales = None
        debut, fin, instant = contexts[ctx_ref]
        unite = units.get(el.get("unitRef") or "", el.get("unitRef") or "")
        out.append(FaitDimensionne(
            concept=concept, debut=debut, fin=fin, instant=instant,
            membres=membres.get(ctx_ref, ()), unite=unite, valeur=valeur, decimales=decimales,
        ))
    return out


def _membre_depuis_href(href: str) -> Optional[str]:
    """`...xsd#us-gaap_OperatingSegmentsMember` → `us-gaap:OperatingSegmentsMember`. Pur.

    Le fragment après `#` est toujours `{prefixe}_{Nom}` (aucun préfixe connu de ce référentiel ne
    porte lui-même un `_` — `us-gaap` porte un tiret) : le PREMIER `_` sépare le préfixe du nom.
    """
    if "#" not in href:
        return None
    frag = href.rsplit("#", 1)[-1]
    if "_" not in frag:
        return None
    prefixe, nom = frag.split("_", 1)
    return f"{prefixe}:{nom}" if prefixe and nom else None


def lire_etiquettes(xml: bytes) -> dict[str, str]:
    """membre → libellé (`terseLabel` > `verboseLabel` > `label`, « [Member] »/« [Domain] » ôtés).

    Agnostique au conteneur (voir l'en-tête du module) : parcourt l'arbre à la recherche de
    `link:loc`/`link:label`/`link:labelArc`, que la racine soit un `<link:linkbase>` ou un
    `<xsd:schema>` qui les embarque.
    """
    root = ET.fromstring(xml)
    loc_vers_membre: dict[str, str] = {}
    label_textes: dict[str, dict[str, str]] = {}
    arcs: list[tuple[str, str]] = []
    for el in root.iter():
        tag = _local(el.tag)
        if tag == "loc":
            label = _xlink(el, "label")
            href = _xlink(el, "href") or ""
            membre = _membre_depuis_href(href)
            if label and membre:
                loc_vers_membre.setdefault(label, membre)
        elif tag == "label":
            label = _xlink(el, "label")
            role = (_xlink(el, "role") or "").rsplit("/", 1)[-1]
            if label:
                label_textes.setdefault(label, {}).setdefault(role, (el.text or "").strip())
        elif tag == "labelArc":
            frm, to = _xlink(el, "from"), _xlink(el, "to")
            if frm and to:
                arcs.append((frm, to))

    out: dict[str, str] = {}
    for frm, to in arcs:
        membre = loc_vers_membre.get(frm)
        if membre is None or membre in out:
            continue
        roles = label_textes.get(to) or {}
        texte = roles.get("terseLabel") or roles.get("verboseLabel") or roles.get("label")
        if texte is None:
            continue
        texte = texte.replace(" [Member]", "").replace(" [Domain]", "").strip()
        out[membre] = texte
    return out


def lire_hierarchie(xml: bytes) -> tuple[dict[str, str], tuple[str, ...]]:
    """membre → parent, et les CONFLITS (un membre vu avec deux parents différents) rendus en clair.

    ⚠️ ÉCART DOCUMENTÉ À LA SPEC (§3) : la spec annonce la signature `dict[membre, parent]` seule,
    mais prescrit dans la même phrase que « le conflit est rendu dans une liste `conflits` (jamais
    tu) ». Une signature qui rend UNIQUEMENT le dict ne peut pas satisfaire les deux à la fois sans
    un canal latéral tacite — un module PUR ne mute pas de variable globale pour en sortir une
    deuxième valeur. Rendre `(dict, conflits)` est le choix qui tient la promesse « jamais tu » au
    pied de la lettre ; `ventilation.relever` lit le second membre du tuple pour nourrir
    `Ventilation.conflits`.

    Parcourt TOUTES les `definitionLink`, triées par `xlink:role` (déterministe) : le PREMIER rôle
    rencontré pour un membre fixe son parent ; un rôle ultérieur qui lui donnerait un AUTRE parent
    est un conflit, nommé, jamais tu.
    """
    root = ET.fromstring(xml)
    blocs: list[tuple[str, list]] = []
    for el in root.iter():
        if _local(el.tag) == "definitionLink":
            blocs.append((_xlink(el, "role") or "", list(el)))
    blocs.sort(key=lambda b: b[0])

    parent: dict[str, str] = {}
    conflits: list[str] = []
    for _role, enfants in blocs:
        loc_vers_membre: dict[str, str] = {}
        for el in enfants:
            if _local(el.tag) == "loc":
                label = _xlink(el, "label")
                membre = _membre_depuis_href(_xlink(el, "href") or "")
                if label and membre:
                    loc_vers_membre[label] = membre
        for el in enfants:
            if _local(el.tag) != "definitionArc":
                continue
            arcrole = _xlink(el, "arcrole") or ""
            if not arcrole.endswith("/domain-member"):
                continue
            frm, to = _xlink(el, "from"), _xlink(el, "to")
            p, c = loc_vers_membre.get(frm or ""), loc_vers_membre.get(to or "")
            if not p or not c:
                continue
            if c in parent and parent[c] != p:
                conflits.append(f"« {c} » a deux parents : « {parent[c]} » (retenu) et « {p} »")
                continue
            parent.setdefault(c, p)
    return parent, tuple(conflits)
