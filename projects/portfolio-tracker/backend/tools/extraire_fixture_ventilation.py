"""Extrait une fixture de VENTILATION PUBLIÉE — COPIÉE DU RÉEL, filtrée à ce qui est utile.

Télécharge l'index d'un dépôt, son instance XBRL (`_htm.xml`) et ses étiquettes/définitions
(`_lab.xml`/`_def.xml`, ou l'`.xsd` de l'extension quand le filer les y embarque — mesuré sur RVMD
10-K `0001193125-26-071563`, voir l'en-tête de `app/knowledge/ventilation_xbrl.py`), et garde
UNIQUEMENT :
  - les contextes et unités référencés par les faits gardés ;
  - les faits qui portent au moins un axe du référentiel de ventilation (même disqualifiés par un
    axe de plus : un sous-détail reste utile à l'éprouver) ;
  - les faits SANS dimension des MÊMES concepts (le total publié, pour le raccord) ;
  - les étiquettes et les arcs de hiérarchie des SEULS membres gardés.

Réseau PUBLIC (data.sec.gov), NI base NI modèle. User-Agent `_UA` d'`edgar_facts`, une requête à la
fois, ≥ 0,25 s entre appels (#73). Instance neuve de l'image, jamais dans `portfolio-backend`.

    bash tools/extraire_fixture_ventilation.sh NVDA 0001045810-26-000021
    bash tools/extraire_fixture_ventilation.sh NVDA 0001045810-26-000075
    bash tools/extraire_fixture_ventilation.sh RVMD 0001193125-26-071563
    bash tools/extraire_fixture_ventilation.sh JPM 0001628280-26-008131

Écrit `checks/fixtures/ventilation/{TICKER}_{accn}_{inst|lab|def}.xml.gz` et un manifeste
`{TICKER}_{accn}.json` (`{cik, form, filed, inst, lab, def}`) que lisent le check, son négatif et
l'outil `montrer_ventilation.py` en mode fixture.
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

from app.knowledge.edgar_facts import _UA
from app.knowledge.edgar_feed import resolve_cik
from app.knowledge.ventilation import charger_referentiel
from app.knowledge.ventilation_xbrl import lire_instance

FIX = Path(__file__).resolve().parent.parent / "checks" / "fixtures" / "ventilation"
DELAI_S = 0.25
_INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/index.json"
_FICHIER = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/{nom}"
_HEADERS_FICHIER = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/{accn}-index-headers.html"


async def _get(client: httpx.AsyncClient, url: str) -> bytes:
    await asyncio.sleep(DELAI_S)
    r = await client.get(url)
    r.raise_for_status()
    return r.content


async def _index(client: httpx.AsyncClient, cik: int, accn: str) -> dict:
    nodash = accn.replace("-", "")
    payload = await _get(client, _INDEX.format(cik=cik, accn_nodash=nodash))
    return json.loads(payload)


def _choisir(index: dict, *, suffixe: str, repli_xsd: bool) -> Optional[str]:
    noms = [it["name"] for it in index["directory"]["item"]]
    for n in noms:
        if n.endswith(suffixe):
            return n
    if repli_xsd:
        for n in noms:
            if n.endswith(".xsd"):
                return n
    return None


async def _filed(client: httpx.AsyncClient, cik: int, accn: str) -> str:
    nodash = accn.replace("-", "")
    txt = (await _get(client, _HEADERS_FICHIER.format(cik=cik, accn_nodash=nodash, accn=accn))).decode(
        "utf-8", errors="replace")
    m = re.search(r"FILED AS OF DATE:\s*(\d{8})", txt)
    if not m:
        raise RuntimeError(f"date de dépôt introuvable dans l'en-tête du dépôt {accn}")
    s = m.group(1)
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def _filtrer_instance(xml: bytes, referentiel) -> tuple[bytes, set[str], set[str]]:
    """Garde l'ouverture de racine (xmlns), les contextes/unités/faits UTILES. Pur. Rend
    (xml_filtre, concepts_dimensionnes_gardes, membres_gardes)."""
    texte = xml.decode("utf-8")
    axes_connus = {a.axe for a in referentiel.axes}

    contextes: dict[str, str] = {}
    for m in re.finditer(r'<context id="([^"]+)">(.*?)</context>', texte, re.S):
        contextes[m.group(1)] = m.group(0)

    ctx_dims: dict[str, list[tuple[str, str]]] = {}
    for cid, bloc in contextes.items():
        ctx_dims[cid] = re.findall(r'explicitMember dimension="([^"]+)">([^<]+)<', bloc)

    ctx_utiles: set[str] = set()
    membres_gardes: set[str] = set()
    concepts_dimensionnes: set[str] = set()
    for cid, dims in ctx_dims.items():
        if any(a in axes_connus for a, _ in dims):
            ctx_utiles.add(cid)
            membres_gardes.update(m for _a, m in dims)

    # Les concepts portés par un contexte utile — pour garder aussi leurs faits SANS dimension
    # (le défaut, utile au raccord contre le total publié).
    for cid in ctx_utiles:
        for m in re.finditer(r"<([a-zA-Z][\w.-]*:[A-Za-z][\w]*)\b[^>]*contextRef=\"" + re.escape(cid) + r"\"",
                             texte):
            concepts_dimensionnes.add(m.group(1))

    for cid, dims in ctx_dims.items():
        if not dims and cid not in ctx_utiles:
            # contexte par défaut : utile seulement s'il porte un concept qu'on a gardé ailleurs
            for concept in concepts_dimensionnes:
                if re.search(r"<" + re.escape(concept) + r"\b[^>]*contextRef=\"" + re.escape(cid) + r"\"", texte):
                    ctx_utiles.add(cid)
                    break

    schema_ref = re.search(r"<link:schemaRef\b[^>]*/>", texte)
    racine_ouverture = texte[:texte.index(">", texte.index("<xbrl")) + 1]

    morceaux = [racine_ouverture]
    if schema_ref:
        morceaux.append(schema_ref.group(0))
    for cid in sorted(ctx_utiles):
        morceaux.append(contextes[cid])

    unites_gardees: set[str] = set()
    for cid in ctx_utiles:
        for m in re.finditer(r'<(\w[\w.-]*:[A-Za-z]\w*)\b[^>]*contextRef="' + re.escape(cid) + r'"[^>]*unitRef="([^"]+)"',
                             texte):
            unites_gardees.add(m.group(2))
    for m in re.finditer(r'<unit id="([^"]+)">(.*?)</unit>', texte, re.S):
        if m.group(1) in unites_gardees:
            morceaux.append(m.group(0))

    for cid in sorted(ctx_utiles):
        for m in re.finditer(r'<(\w[\w.-]*:[A-Za-z]\w*)\b[^>]*contextRef="' + re.escape(cid) + r'"[^>]*?(?:/>|>[^<]*</\1>)',
                             texte):
            morceaux.append(m.group(0))

    morceaux.append("</xbrl>")
    xml_filtre = "\n".join(morceaux).encode("utf-8")
    return xml_filtre, concepts_dimensionnes, membres_gardes


def _attr(tag_texte: str, nom: str) -> Optional[str]:
    """La valeur d'un attribut `nom="..."` DANS le texte d'UNE balise déjà isolée. Chaque attribut
    est cherché séparément (jamais enchaîné dans un seul motif) : un `xlink:arcrole` porte une URL
    pleine de `/`, et un motif qui route sur « pas de `/` » entre deux attributs échoue dès que l'un
    d'eux en contient — c'est la panne mesurée sur `labelArc`/`definitionArc` (0 arc trouvé)."""
    m = re.search(rf'{re.escape(nom)}="([^"]*)"', tag_texte)
    return m.group(1) if m else None


def _balises(texte: str, nom: str) -> list[str]:
    """Le texte intégral de chaque balise `<link:{nom} .../>`  (auto-fermante) — bornée au premier
    `>`, jamais à un comptage de `/`, donc insensible aux `/` À L'INTÉRIEUR des valeurs d'attribut."""
    return re.findall(rf"<link:{nom}\b[^>]*/>", texte)


def _filtrer_linkbase(xml: bytes, membres: set[str], *, genre: str) -> bytes:
    """Garde les `loc`/`label`/`labelArc` (genre=lab) ou `loc`/`definitionArc` dans leur
    `definitionLink` d'origine (genre=def) des SEULS membres gardés. Texte brut, pas de
    réassemblage par `ElementTree` (préserve les préfixes d'origine à l'identique)."""
    texte = xml.decode("utf-8", errors="replace")

    def frag_vers_membre(href: str) -> Optional[str]:
        if "#" not in href:
            return None
        frag = href.rsplit("#", 1)[-1]
        if "_" not in frag:
            return None
        p, n = frag.split("_", 1)
        return f"{p}:{n}"

    if genre == "lab":
        locs = _balises(texte, "loc")
        loc_vers_membre = {_attr(l, "xlink:label"): frag_vers_membre(_attr(l, "xlink:href") or "") for l in locs}
        gardes_labels = {lab for lab, m in loc_vers_membre.items() if lab and m in membres}
        arcs = _balises(texte, "labelArc")
        gardes_to = {_attr(a, "xlink:to") for a in arcs if _attr(a, "xlink:from") in gardes_labels}
        sortie = ['<?xml version="1.0" encoding="UTF-8"?>', '<link:linkbase '
                  'xmlns:link="http://www.xbrl.org/2003/linkbase" '
                  'xmlns:xlink="http://www.w3.org/1999/xlink" '
                  'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">']
        for l in locs:
            if _attr(l, "xlink:label") in gardes_labels:
                sortie.append(l)
        for m in re.finditer(r"<link:label\b.*?</link:label>", texte, re.S):
            if _attr(m.group(0), "xlink:label") in gardes_to:
                sortie.append(m.group(0))
        for a in arcs:
            if _attr(a, "xlink:from") in gardes_labels:
                sortie.append(a)
        sortie.append("</link:linkbase>")
        return "\n".join(sortie).encode("utf-8")

    # genre == "def" : garder les `definitionLink` qui touchent au moins un membre gardé,
    # À L'INTÉRIEUR, ne garder que les `loc`/`definitionArc` utiles.
    sortie = ['<?xml version="1.0" encoding="UTF-8"?>', '<link:linkbase '
              'xmlns:link="http://www.xbrl.org/2003/linkbase" '
              'xmlns:xlink="http://www.w3.org/1999/xlink" '
              'xmlns:xbrldt="http://xbrl.org/2005/xbrldt">']
    for bloc in re.finditer(r"<link:definitionLink\b([^>]*)>(.*?)</link:definitionLink>", texte, re.S):
        entete, corps = bloc.group(1), bloc.group(2)
        locs = _balises(corps, "loc")
        loc_membre = {_attr(l, "xlink:label"): frag_vers_membre(_attr(l, "xlink:href") or "") for l in locs}
        arcs = _balises(corps, "definitionArc")
        gardes: set[str] = set()
        arcs_gardes: list[str] = []
        for a in arcs:
            frm, to = _attr(a, "xlink:from"), _attr(a, "xlink:to")
            if loc_membre.get(frm) in membres or loc_membre.get(to) in membres:
                gardes.add(frm or "")
                gardes.add(to or "")
                arcs_gardes.append(a)
        if not arcs_gardes:
            continue
        role = _attr(entete, "xlink:role") or ""
        sortie.append(f'<link:definitionLink xlink:type="extended" xlink:role="{role}">')
        for l in locs:
            if _attr(l, "xlink:label") in gardes:
                sortie.append(l)
        sortie.extend(arcs_gardes)
        sortie.append("</link:definitionLink>")
    sortie.append("</link:linkbase>")
    return "\n".join(sortie).encode("utf-8")


async def un(ticker: str, accn: str) -> int:
    referentiel = charger_referentiel()
    cik = await resolve_cik(ticker)
    FIX.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True,
                                 headers={"User-Agent": _UA, "Accept": "*/*"}) as client:
        index = await _index(client, cik, accn)
        nom_inst = _choisir(index, suffixe="_htm.xml", repli_xsd=False)
        if nom_inst is None:
            print(f"BILAN fixture ventilation — {ticker} {accn} : ÉCHEC (pas d'instance `_htm.xml` à l'index)")
            return 1
        nom_lab = _choisir(index, suffixe="_lab.xml", repli_xsd=True)
        nom_def = _choisir(index, suffixe="_def.xml", repli_xsd=True)
        repli_xsd = nom_lab is not None and nom_lab.endswith(".xsd")
        nodash = accn.replace("-", "")

        inst_brut = await _get(client, _FICHIER.format(cik=cik, accn_nodash=nodash, nom=nom_inst))
        lab_brut = await _get(client, _FICHIER.format(cik=cik, accn_nodash=nodash, nom=nom_lab)) if nom_lab else b""
        def_brut = (await _get(client, _FICHIER.format(cik=cik, accn_nodash=nodash, nom=nom_def))
                   if nom_def and nom_def != nom_lab else lab_brut if repli_xsd else b"")
        filed = await _filed(client, cik, accn)

    faits = lire_instance(inst_brut)
    inst_filtre, _concepts, membres_gardes = _filtrer_instance(inst_brut, referentiel)
    lab_filtre = _filtrer_linkbase(lab_brut, membres_gardes, genre="lab") if lab_brut else b""
    def_filtre = _filtrer_linkbase(def_brut, membres_gardes, genre="def") if def_brut else b""

    m_type = re.search(rb"<dei:DocumentType[^>]*>([^<]+)</dei:DocumentType>", inst_brut)
    form = m_type.group(1).decode("utf-8").strip() if m_type else "?"
    base = FIX / f"{ticker}_{accn}"
    tailles = {}
    for suffixe, contenu in (("inst", inst_filtre), ("lab", lab_filtre), ("def", def_filtre)):
        chemin = Path(f"{base}_{suffixe}.xml.gz")
        with gzip.open(chemin, "wb") as f:
            f.write(contenu)
        tailles[suffixe] = chemin.stat().st_size

    manifeste = {
        "ticker": ticker, "cik": cik, "accn": accn, "form": form, "filed": filed,
        "source_lab_def": "xsd (embarqué)" if repli_xsd else "fichiers séparés",
        "n_faits_bruts": len(faits), "n_membres_gardes": len(membres_gardes),
    }
    Path(f"{base}.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"BILAN fixture ventilation — {ticker} {accn} : {len(faits)} faits bruts lus, "
          f"{len(membres_gardes)} membres gardés, tailles compressées {tailles} ({manifeste['source_lab_def']})")
    return 0


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("accn")
    a = ap.parse_args()
    try:
        return await un(a.ticker, a.accn)
    except Exception as e:  # pré-requis manquant : sortie ≠ 0, jamais un saut silencieux
        print(f"BILAN fixture ventilation — {a.ticker} {a.accn} : ÉCHEC ({type(e).__name__}: {e})")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
