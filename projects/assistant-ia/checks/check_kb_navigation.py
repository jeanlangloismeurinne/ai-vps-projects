"""Checks hors-ligne des pages de navigation du coffre (`kb_schema_notes`).

Le défaut réparé, mesuré le 2026-09-06 : `Accueil.md` proposait `[[Tâches]]` et `[[Journal]]`, deux
fichiers `.base` que Quartz ne rend pas. Les deux liens étaient **404 sur le site**, et rien ne le
signalait — un lien mort ne lève aucune erreur, il déçoit juste le lecteur.

D'où l'assertion centrale, écrite au point de lecture et pas au point d'écriture : **tout wikilink
émis par une page désigne un fichier qui existe dans le coffre**. Elle tient quelle que soit la
raison du lien mort (fichier renommé, supprimé, `.base` non rendu, note désindexée).

Le coffre de test est **copié de la forme réelle** — mêmes répertoires, même front-matter que ce
que `journal_vault.write_entry` produit. Une fixture plus favorable que la prod serait un check
aveugle au vert, et neutraliserait aussi la passe négative.

Usage : python checks/check_kb_navigation.py
"""

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import kb_schema_notes as nav

ECHECS: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {label}")
    else:
        print(f"  ECHEC {label}" + (f" — {detail}" if detail else ""))
        ECHECS.append(f"{label}" + (f" — {detail}" if detail else ""))


NOTE = """---
doc_id: assistant-ia:vps_files:notes/{slug}
contexte: {contexte}
nature:
- note_de_lecture
tags:
{tags}
created_at: '{date}T10:00:00Z'
slack_ts: '1787584183.445949'
---

Corps de la note {slug}.
"""

TACHE = """---
type: task
card_id: 00000000-0000-0000-0000-00000000000{n}
board: {board}
column: {column}
position: 0
due: '{due}'
status: reminder
tags: []
created_at: '2026-08-24T20:14:45Z'
updated_at: '2026-08-24T20:14:45Z'
source: kanban
---
"""


def construire_coffre(base: Path) -> None:
    """Trois notes partageant le tag `Safran`, une note qui ne partage rien, une tâche."""
    notes = base / "notes" / "2026"
    notes.mkdir(parents=True)
    specs = [
        ("2026-08-24-eu-space-act", "professionnel", ["Safran", "EU Space Act"], "2026-08-24"),
        ("2026-08-24-propulsion-electrique", "professionnel", ["Safran", "propulsion"], "2026-08-24"),
        ("2026-08-24-stations-sol", "professionnel", ["Safran"], "2026-08-24"),
        # L'isolée : aucun tag en commun avec les autres. C'est elle qui rend le regroupement
        # falsifiable — un regroupeur qui range tout la rattacherait à `Safran`.
        ("2026-09-06-memoires-de-de-gaulle", "personnel", ["histoire"], "2026-09-06"),
    ]
    for slug, contexte, tags, date in specs:
        (notes / f"{slug}.md").write_text(
            NOTE.format(
                slug=slug, contexte=contexte, date=date,
                tags="\n".join(f"- {t}" for t in tags),
            ),
            encoding="utf-8",
        )

    # Un fichier sans doc_id : il ne doit apparaître dans aucune page (ni comme note, ni comme lien).
    (base / "notes" / "brouillon-sans-doc-id.md").write_text(
        "# Brouillon\n\npas de front-matter\n", encoding="utf-8")

    taches = base / "tasks" / "famille"
    taches.mkdir(parents=True)
    (taches / "visite-ikea.md").write_text(
        TACHE.format(n=1, board="Famille", column="Rappels", due="2026-08-29"), encoding="utf-8")

    (base / "README.md").write_text("# readme\n", encoding="utf-8")


WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        construire_coffre(root)

        notes = nav._scanner_notes(root, titres={
            "notes/2026/2026-08-24-eu-space-act.md": "Opportunité du EU Space Act",
        })
        taches = nav._scanner_taches(root)

        pages = {
            nav._ACCUEIL: nav._accueil_md(notes, taches),
            nav._JOURNAL: nav._journal_md(notes),
            nav._TACHES: nav._taches_md(taches),
            nav._TAXONOMIE: nav._taxonomie_md(),
        }
        for nom, contenu in pages.items():
            (root / nom).write_text(contenu, encoding="utf-8")

        print("\n§A — le balayage voit les notes, et rien d'autre")
        check("les 4 notes sont vues", len(notes) == 4, f"{len(notes)} vues")
        check("le fichier sans doc_id est ignoré",
              all("brouillon" not in n["chemin"] for n in notes))
        check("les tâches ne sont pas comptées comme des notes",
              all(not n["chemin"].startswith("tasks/") for n in notes))
        check("la tâche est vue", len(taches) == 1, f"{len(taches)} vues")

        print("\n§B — tout wikilink désigne un fichier qui existe  ⟵ le défaut de 2026-09-06")
        morts: list[str] = []
        total = 0
        for nom, contenu in pages.items():
            for m in WIKILINK_RE.finditer(contenu):
                total += 1
                cible = m.group(1)
                if not (root / f"{cible}.md").exists():
                    morts.append(f"{nom} → [[{cible}]]")
        check(f"aucun lien mort ({total} liens vérifiés)", not morts, f"morts : {morts}")
        check("des liens sont bien émis", total >= 6, f"{total} liens seulement")

        print("\n§C — aucune page ne référence un .base (Quartz ne les rend pas)")
        bases = [m.group(1) for c in pages.values() for m in WIKILINK_RE.finditer(c)
                 if "base" in m.group(1).lower() and not (root / f"{m.group(1)}.md").exists()]
        check("aucun wikilink vers une vue .base", not bases, f"trouvés : {bases}")
        for attendu in ("Journal", "Tâches", "Taxonomie"):
            check(f"l'accueil mène à [[{attendu}]]",
                  f"[[{attendu}]]" in pages.get(nav._ACCUEIL, ""))

        print("\n§D — le regroupement par thème, et son orphelin")
        themes, isolees = nav._grouper_par_theme(notes)
        noms_themes = {t for t, _ in themes}
        check("`Safran` est un thème", "Safran" in noms_themes, f"thèmes : {sorted(noms_themes)}")
        safran = dict(themes).get("Safran", [])
        check("le thème `Safran` porte ses 3 notes", len(safran) == 3, f"{len(safran)} notes")
        check("un tag à une seule note ne fait pas un thème",
              "propulsion" not in noms_themes and "histoire" not in noms_themes,
              f"thèmes : {sorted(noms_themes)}")
        check("la note sans tag partagé reste isolée",
              [n["chemin"] for n in isolees] == ["notes/2026/2026-09-06-memoires-de-de-gaulle"],
              f"isolées : {[n['chemin'] for n in isolees]}")
        check("l'accueil nomme la section des isolées", "Notes isolées" in pages[nav._ACCUEIL])

        print("\n§E — les libellés")
        eu = next(n for n in notes if "eu-space-act" in n["chemin"])
        check("un titre d'index est utilisé", eu["titre"] == "Opportunité du EU Space Act", eu["titre"])
        gaulle = next(n for n in notes if "de-gaulle" in n["chemin"])
        check("sans titre d'index, repli déslugifié sans la date",
              gaulle["titre"] == "Memoires de de gaulle", gaulle["titre"])

        print("\n§F — toutes les notes sont atteignables depuis le Journal")
        # `.get` et non `[]` : si la page n'est pas générée du tout, l'assertion doit **rougir**,
        # pas mourir sur un KeyError en emportant le bilan. Une passe négative qui produit une
        # trace de pile ne prouve rien de ce que le check gardait.
        cibles = {m.group(1) for m in WIKILINK_RE.finditer(pages.get(nav._JOURNAL, ""))}
        manquantes = [n["chemin"] for n in notes if n["chemin"] not in cibles]
        check("aucune note absente du Journal", not manquantes, f"absentes : {manquantes}")

    print("\n" + "=" * 60)
    if ECHECS:
        print(f"ECHEC — {len(ECHECS)} assertion(s) :")
        for e in ECHECS:
            print(f"  x {e}")
        return 1
    print(f"OK — {len(ECHECS) == 0 and 'toutes les assertions vertes'}")
    return 0


sys.exit(main())
