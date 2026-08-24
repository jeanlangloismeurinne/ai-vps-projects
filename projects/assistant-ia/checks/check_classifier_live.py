"""Vérification LIVE du classifieur KB journal — appel réel à DeepInfra.

À exécuter dans le container de production (la clé DeepInfra n'est pas sur l'hôte) :

    docker exec -w /app -e PYTHONPATH=/app <container> python checks/check_classifier_live.py

Ce que ce check protège (défauts réellement observés le 2026-08-24, pas hypothétiques) :

1. `nature` hors vocabulaire. Avec Llama 3.1 8B, DeepInfra refusait `json_schema` (HTTP 405),
   le vocabulaire fermé n'était plus qu'une consigne en prose et le modèle produisait
   `nature: ["vacances"]` — un tag libre — une fois sur deux. Le validateur rejetait, et la
   note de l'utilisateur finissait en « à classer ».
2. `nature` jamais vide. La cardinalité est 0..n (categories.schema.yaml) : une note de vie
   ne relève d'aucune nature. Le modèle en inventait une (`note_de_lecture` pour un week-end
   en montagne). C'est le défaut d'origine du ticket #1787559677485.
3. Double appel API. Un `405` sur `json_schema` puis un fallback `json_object` = 2 requêtes
   facturées par classification.

Un échec ici signifie généralement que `DEEPINFRA_MODEL_CLASSIF` pointe sur un modèle qui ne
supporte pas `response_format: json_schema`.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings                       # noqa: E402
from app.services import journal_kb_classifier as C   # noqa: E402

# (libellé, texte, attentes). `nature_interdite` = valeurs qui trahiraient une nature inventée.
CAS = [
    (
        "note de vie — aucune nature ne convient (défaut #1787559677485)",
        "Super week-end en montagne avec les enfants, on a fait la rando du lac "
        "samedi et il a neigé dimanche matin. Le refuge était complet.",
        {"contexte": "personnel", "nature_exacte": set()},
    ),
    (
        "note de lecture",
        "Dans Thinking Fast and Slow, Kahneman explique que le système 1 est "
        "automatique et le système 2 demande un effort conscient. À retenir pour "
        "comprendre les biais de décision.",
        # contexte non asserté : lire Kahneman est légitimement personnel OU professionnel.
        # nature est 0..n — ["apprentissage", "note_de_lecture"] est une réponse correcte,
        # on exige donc une intersection, pas une égalité.
        {"nature_min": {"note_de_lecture"}},
    ),
    (
        "décision professionnelle",
        "J'ai décidé qu'on passerait tous les nouveaux projets sur Postgres plutôt "
        "que SQLite, pour éviter la migration douloureuse plus tard.",
        {"contexte": "professionnel", "nature_min": {"decision"}},
    ),
]


async def main() -> int:
    schema = C._load_schema()
    _, nature_vals = C._extract_vocabulary(schema)
    print(f"modèle : {settings.DEEPINFRA_MODEL_CLASSIF}\n")

    echecs: list[str] = []
    for nom, texte, att in CAS:
        r = await C.classify(texte)
        print(f"--- {nom} ---")
        print(f"  contexte={r.contexte}  nature={r.nature}  fallback={r.is_fallback}")
        print(f"  tags={r.tags}\n  title={r.title!r}\n")

        if r.is_fallback:
            # Le fallback protège la note, mais ici il signale que l'appel ou la validation
            # a échoué : c'est précisément ce qu'on veut détecter.
            echecs.append(f"{nom} : FALLBACK (appel API ou validation en échec)")
            continue

        nature = set(r.nature or [])
        hors_vocab = nature - set(nature_vals)
        if hors_vocab:
            echecs.append(f"{nom} : nature hors vocabulaire {sorted(hors_vocab)}")
        if "contexte" in att and r.contexte != att["contexte"]:
            echecs.append(f"{nom} : contexte={r.contexte!r}, attendu {att['contexte']!r}")
        if "nature_exacte" in att and nature != att["nature_exacte"]:
            echecs.append(
                f"{nom} : nature={sorted(nature)}, attendu {sorted(att['nature_exacte'])} "
                f"— une nature inventée, le défaut 0..n est de retour"
            )
        if "nature_min" in att and not (nature & att["nature_min"]):
            echecs.append(
                f"{nom} : nature={sorted(nature)}, attendu au moins "
                f"{sorted(att['nature_min'])}"
            )

    print("=" * 60)
    if echecs:
        print(f"ECHEC — {len(echecs)} assertion(s) :")
        for e in echecs:
            print(f"  ✗ {e}")
        return 1
    print(f"OK — {len(CAS)} cas, aucun fallback, vocabulaire respecté, 0..n honoré.")
    return 0


sys.exit(asyncio.run(main()))
