"""Check **sur la surface servie** : aucun lien interne du site Quartz ne mène à un 404.

`check_kb_navigation.py` garde le point d'écriture (un wikilink désigne un fichier du coffre).
Ce check-ci garde le point de lecture, et c'est le seul des deux qui aurait vu le défaut du
2026-09-06 : `[[Journal]]` et `[[Tâches]]` désignaient bien des fichiers existants du coffre —
`Journal.base` et `Tâches.base` — mais Quartz ne rend pas les `.base`. Un lien valide côté source,
404 côté site, pendant 12 jours et sans un octet de log.

D'où la règle : un contrôle se teste là où le lecteur l'éprouve. Ici, sur le HTML émis.

Usage (depuis l'hôte, kb-viewer n'a pas de python) :
    rm -rf /tmp/kbsite && docker cp kb-viewer:/usr/share/nginx/html /tmp/kbsite
    python3 checks/check_kb_site_links.py /tmp/kbsite
"""

import re
import sys
from pathlib import Path
from urllib.parse import unquote

HREF_RE = re.compile(r'href="([^"]*)"')

# Ce que Quartz ajoute à chaque page (thème, police, fil RSS, crédit) et qui n'est pas de la
# navigation de contenu. On ne les vérifie pas : ils ne dépendent pas de ce qu'on génère.
IGNORES = {"#", ".", "./", "./index.css", "./static/icon.png"}

ECHECS: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {label}")
    else:
        print(f"  ECHEC {label}" + (f" — {detail}" if detail else ""))
        ECHECS.append(label + (f" — {detail}" if detail else ""))


def resout(racine: Path, page: Path, href: str) -> bool:
    """Quartz sert `foo.html` pour l'URL `foo`, ou `foo/index.html` pour un dossier."""
    cible = href.split("#")[0].split("?")[0]
    if not cible:
        return True
    # `404.html` est émis avec des chemins absolus (`/index.css`) : il doit fonctionner servi
    # depuis n'importe quelle profondeur. Une racine d'URL se résout contre la racine du site,
    # pas contre `/` du système de fichiers — sans ça le check rougirait sur du HTML correct.
    base = racine if cible.startswith("/") else page.parent
    chemin = (base / unquote(cible).lstrip("/")).resolve()
    if not str(chemin).startswith(str(racine.resolve())):
        return False
    return (
        chemin.is_file()
        or Path(f"{chemin}.html").is_file()
        or (chemin / "index.html").is_file()
    )


def main(racine: Path) -> int:
    pages = sorted(racine.rglob("*.html"))
    print(f"site : {racine}  ·  {len(pages)} pages HTML servies")

    print("\n§A — les pages de navigation existent sur le site")
    for nom in ("Accueil", "Journal", "Tâches", "Taxonomie"):
        # C'est l'assertion qui aurait rougi avant le correctif : `Journal.html` et `Tâches.html`
        # n'existaient pas, seuls `Journal.base` / `Tâches.base` étaient dans le coffre.
        check(f"{nom}.html est servi", (racine / f"{nom}.html").is_file())

    print("\n§B — aucun lien interne mort  ⟵ le défaut du 2026-09-06")
    morts: list[str] = []
    internes = 0
    for page in pages:
        html = page.read_text(encoding="utf-8", errors="replace")
        for m in HREF_RE.finditer(html):
            href = m.group(1)
            if href.startswith(("http://", "https://", "mailto:", "#")) or href in IGNORES:
                continue
            internes += 1
            if not resout(racine, page, href):
                morts.append(f"{page.relative_to(racine)} → {href}")
    check(f"aucun lien mort ({internes} liens internes suivis)", not morts,
          f"{len(morts)} morts : {sorted(set(morts))[:10]}")
    check("des liens internes sont bien émis", internes >= 30, f"{internes} seulement")

    print("\n§C — toute note du coffre est servie, et atteignable")
    # `index.html` sous `notes/` est une page de dossier fabriquée par Quartz, pas une note du
    # coffre : le Journal n'a pas à la lister. On l'écarte ici et non dans l'assertion, pour que
    # « aucune note absente » garde son sens de couverture des notes réelles.
    notes = sorted(p for p in (racine / "notes").rglob("*.html") if p.name != "index.html")
    check("les notes sont servies", len(notes) >= 6, f"{len(notes)} pages de notes")
    journal = (racine / "Journal.html")
    if journal.is_file():
        html = journal.read_text(encoding="utf-8", errors="replace")
        cibles = {unquote(h).lstrip("./").split("#")[0] for h in HREF_RE.findall(html)}
        absentes = [
            str(n.relative_to(racine))
            for n in notes
            if str(n.relative_to(racine))[: -len(".html")] not in cibles
        ]
        check("aucune note absente du Journal servi", not absentes, f"absentes : {absentes}")
    else:
        check("Journal.html lisible pour vérifier l'atteignabilité", False, "page absente")

    print("\n" + "=" * 60)
    if ECHECS:
        print(f"ECHEC — {len(ECHECS)} assertion(s) :")
        for e in ECHECS:
            print(f"  x {e}")
        return 1
    print("OK — toutes les assertions vertes")
    return 0


sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/kbsite")))
