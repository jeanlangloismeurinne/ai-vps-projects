"""Acceptation de l'APPARIEUR contre le VRAI modèle et le VRAI dépôt (lot 3, maillon 4bis, étape 2a).

Un prompt/schéma n'est pas acquis tant qu'il n'a pas tourné contre le vrai modèle
(`feedback_verifier_contre_api_reelle`). La moitié déterministe est éprouvée gratuitement par
`tools/inventaire_apparieur.py` (le contexte, lu en texte) et par `checks/check_appariement.py` (le
pont, hors-ligne). ICI on fait produire une carte RÉELLE sur l'inventaire RÉEL de trois émetteurs
contrastés, on la LIT, et on vérifie des critères qui ne se laissent pas contourner.

POURQUOI LE CRITÈRE DE SUCCÈS NE S'ÉNONCE PAS EN TROIS LIGNES
--------------------------------------------------------------
Le réflexe serait de mesurer le TAUX DE REFUS du pont. Il est nécessaire, et il ne suffit pas : un
modèle qui répond `indisponible` partout n'est JAMAIS refusé. Le taux tomberait à zéro pendant que la
collecte se viderait — un vert qui masque la perte, exactement la faute que tout le lot 3 combat.
Symétriquement, un modèle qui répond `exact` partout serait rarement refusé aussi : `[V]` vérifie que
le concept est DÉPOSÉ, jamais qu'il répond à la question (#68).

Les quatre critères ci-dessous se lisent donc ENSEMBLE, et chacun ferme la porte que le précédent
laisse ouverte :

  [1] la carte est ACCEPTÉE par le pont, après au plus UN tour de réparation. Sans carte, il n'y a
      rien à mesurer — et un refus définitif dit que le contexte ne permet pas de répondre.
  [2] l'état `approximation` est EMPLOYÉ. C'est la case que ce maillon existe pour créer : une carte
      qui n'en contient aucune n'a rien acheté, elle a juste renommé l'ancien choix binaire.
  [3] LE CRITÈRE QUI NE SE CONTOURNE PAS — les lignes RÉCUPÉRÉES : celles que l'aiguilleur SORTANT
      (`router_source`/`poste_retenu`) envoie payer sur le WEB et que l'apparieur ancre dans le
      dépôt. Au moins une, sur chaque émetteur. C'est une comparaison au titulaire, calculée dans le
      même run et gratuitement : un repli sur `indisponible` la fait virer au rouge.

      ⚠️ C'était d'abord un DÉCOMPTE — « plus de lignes ancrées que le titulaire n'en route vers
      EDGAR » — et ce décompte a rougi sur MSFT (14 contre 17) sans rien dire de vrai. Le traducteur
      y nomme un `poste` sur 30 lignes SUR 30, donc les 17 lignes du titulaire sont majoritairement
      de FAUX appariements : c'est exactement le défaut que ce maillon existe pour retirer (#67 —
      5 des 7 lignes mesurées le 2026-09-14 étaient fausses, et `poste_retenu` ne vérifie jamais que
      le poste nommé correspond à la métrique). Un critère qui compare des VOLUMES crédite ces 17
      comme si elles étaient justes, et il devient donc d'autant plus difficile à tenir que le
      titulaire se trompe davantage. Comparer des ENSEMBLES retire cette prime à l'erreur.

      Et son pendant qui ne se garde PAS, parce qu'aucun assert ne peut le trancher (#68) : les
      lignes ABANDONNÉES — le titulaire les routait vers EDGAR, l'apparieur les dit `indisponible`.
      Chacune est soit un faux appariement correctement refusé (un GAIN), soit une frilosité (une
      PERTE), et rien dans la structure ne les distingue. Elles sont donc imprimées EN ENTIER, avec
      leur motif, pour être LUES.
  [4] LE CAS NOMMÉ — `qf_1.capital_employe` chez NVDA sort en `approximation`. C'est l'exemple qui a
      motivé la troisième case (#67) : l'émetteur dépose `Assets`, `LiabilitiesCurrent` et sa
      trésorerie, donc la soustraction est à portée et elle est en tier A. Un `indisponible` là
      serait le renoncement d'avant. Un critère nommé, parce qu'un décompte agrégé peut être vert
      pendant que le cas intéressant est faux.

Et ce qui est MESURÉ sans être gardé, parce qu'on ne durcit pas avant d'avoir chiffré (instruction de
la roadmap, `feedback_decision_figee_a_remesurer`) : le nombre de réparations, la distribution des
trois états PAR ÉMETTEUR (c'est là que se lit l'instabilité inter-tickers,
`feedback_jugement_modele_instable_entre_passages` — jamais dans une moyenne), et le nombre de
concepts nommés dont le dernier point est vieux. Ce dernier est le trou connu de `[V]` : un concept
ABANDONNÉ est réellement déposé, donc il traverse le pont, et la collecte remontera un vide.

NE PERSISTE RIEN. `apparier()` construit et valide (contrat + pont), n'écrit pas en base — la
persistance est l'étape 2b (migration 042).

⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, qui peut précéder celui
qu'on éprouve. Lanceur : `tools/acceptation_apparieur.sh`.

Codes : 0 = tous les critères tenus · 1 = un critère rouge · 2 = pas mesurable (env/modèle/SEC).
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from datetime import date

from app.agents.v2.apparieur import (
    AppariementRefuse,
    AppariementSansObjet,
    apparier,
    derniere_periode_vue,
    resumer_inventaire,
)
from app.agents.v2.collecte_executor import router_source
from app.agents.v2.collecteur import ligne_aveugle
from app.agents.v2.frameworks import CollectionPlanRefused, load_frameworks
from app.agents.v2.traducteur import traduire
from app.db.database import close_pool, init_pool
from app.knowledge.edgar_facts import EdgarUnavailable, fetch_company_facts
from app.knowledge.edgar_feed import EdgarFeedUnavailable, resolve_cik

# NVDA (rentable) vs RVMD (pré-revenus) : le contraste des deux pilotes. MSFT s'y ajoute POUR UNE
# RAISON PRÉCISE — c'est le ticker sur lequel le remède par le prompt s'est effondré (11/11 justes sur
# NVDA, 10 fausses sur 15 avec le MÊME prompt, `feedback_jugement_modele_instable_entre_passages`).
# Mesurer l'apparieur sans lui, ce serait mesurer sur le cas qui avait déjà réussi.
CAS = [
    ("NVDA", "qualite_financiere", "rentable"),
    ("MSFT", "qualite_financiere", "rentable"),
    ("RVMD", "qualite_financiere", "pre_revenus"),
]

# Le cas nommé du critère [4] : (ticker, question_id, ingredient_id, statut attendu).
CAS_NOMME = ("NVDA", "qf_1", "capital_employe", "approximation")

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def _cles_edgar_sortant(plan) -> set[tuple[str, str]]:
    """QUELLES lignes l'aiguilleur SORTANT envoie à EDGAR sur ce plan. Déterministe, gratuit.

    Un ENSEMBLE de couples `(question_id, ingredient_id)`, jamais un décompte : le critère [3]
    compare des ensembles précisément parce qu'un décompte crédite les faux appariements du
    titulaire (voir la docstring du module). Le couple, et non l'`ingredient_id` nu — un même
    ingrédient peut exister sous deux questions (contrat `CollectionPlanItem`).

    C'est la LIGNE DE BASE du critère [3], et elle se REQUIERT dans le même run plutôt que de se
    citer de mémoire : l'état de départ d'un test d'acceptation se mesure, il ne se rappelle pas
    (`feedback_ligne_de_base_est_une_mesure`). Le « 7 sur 74 » du 2026-09-14 portait sur trois plans
    et un prompt qui a changé depuis ; le recopier ici mesurerait un souvenir.
    """
    return {(it.question_id, it.ingredient_id) for it in plan.items
            if it.statut == "traduit"
            and router_source(ligne_aveugle(it, plan.ticker_id)) == "edgar"}


async def _un_cas(ticker: str, framework_id: str, archetype: str, fichier) -> int:
    """Un émetteur. Rend 2 si la mesure est impossible (SEC injoignable), 0 sinon — les critères
    rouges passent par `check()`, pas par le code de retour."""
    global fail
    print(f"\n{'='*100}\n{ticker} · {framework_id} · archétype « {archetype} »\n{'='*100}")

    # ── le plan (le titulaire et le vocabulaire atteignable viennent tous deux de là) ─────────────
    try:
        run_plan, plan = await traduire(ticker, framework_id, archetype, fichier=fichier)
    except CollectionPlanRefused as e:
        check(f"[0] {ticker} : plan de collecte produit", False, f"→ plan REFUSÉ par le pont : {e}")
        return 0
    traduits = [it for it in plan.items if it.statut == "traduit"]
    plan_par_cle = {(it.question_id, it.ingredient_id): it for it in traduits}
    cles_traduites = set(plan_par_cle)
    cles_edgar = _cles_edgar_sortant(plan)
    cles_web = cles_traduites - cles_edgar
    postes_nommes = sum(1 for it in traduits if it.poste)
    print(f"  plan : {len(plan.items)} ligne(s) dont {len(traduits)} `traduit` · "
          f"{postes_nommes} poste(s) nommé(s) par le traducteur · "
          f"LIGNE DE BASE (aiguilleur sortant) : {len(cles_edgar)} ligne(s) vers EDGAR, "
          f"{len(cles_web)} vers le web payant · ${run_plan.cost_usd:.4f}")

    # ── l'inventaire réel ─────────────────────────────────────────────────────────────────────────
    try:
        cik = await resolve_cik(ticker)
        facts = await fetch_company_facts(cik)
    except (EdgarFeedUnavailable, EdgarUnavailable) as e:
        print(f"  ABANDON mesure : dépôt SEC illisible pour {ticker} → {e}", file=sys.stderr)
        return 2
    periode = derniere_periode_vue(facts)
    fraicheur = {l.concept: l.dernier_end for l in resumer_inventaire(facts)}
    print(f"  inventaire : {len(facts)} concepts déposés · période la plus récente {periode}")

    # ── la carte ──────────────────────────────────────────────────────────────────────────────────
    try:
        res = await apparier(plan, facts)
    except AppariementSansObjet as e:
        check(f"[1] {ticker} : carte acceptée par le pont", False,
              f"→ rien à apparier, et c'est le PLAN qu'il faut relire, pas l'apparieur : {e}")
        return 0
    except AppariementRefuse as e:
        check(f"[1] {ticker} : carte acceptée par le pont", False,
              f"→ REFUS APRÈS RÉPARATION : {e}")
        return 0
    except Exception as e:  # noqa: BLE001
        check(f"[1] {ticker} : carte acceptée par le pont", False, f"→ {type(e).__name__}: {e}")
        traceback.print_exc()
        return 0
    check(f"[1] {ticker} : carte acceptée par le pont (≤ 1 réparation)", True)

    # ── LA LECTURE — c'est elle qui juge le sens, aucun assert ne peut le faire (#68) ─────────────
    par_statut: dict[str, int] = {}
    vieux: list[str] = []
    for it in res.carte.items:
        par_statut[it.statut] = par_statut.get(it.statut, 0) + 1
        print(f"\n  [{it.statut:14}] {it.question_id}.{it.ingredient_id}")
        for c in it.concepts:
            age = fraicheur.get(c)
            marque = ""
            if age and periode:
                jours = (date.fromisoformat(periode) - date.fromisoformat(age)).days
                marque = f"  (dernier point il y a {jours}j)"
                if jours > 400:
                    vieux.append(f"{it.ingredient_id}:{c}({jours}j)")
            print(f"      · {c}{marque}")
        if it.formule:
            print(f"      formule : {it.formule}   [déterministe={it.deterministe}]")
        for h in it.hypotheses:
            print(f"      hypothèse : {h}")
        for t in it.termes_web:
            print(f"      terme web : {t}")
        if it.motif:
            print(f"      motif : {it.motif}")

    print(f"\n  distribution {ticker} : "
          + " · ".join(f"{n} {s}" for s, n in sorted(par_statut.items()))
          + f" · {len(res.refus_repares)} réparation(s) · ${res.run.cost_usd:.4f}")
    for motif in res.refus_repares:
        print(f"  RÉPARÉ après : {motif.splitlines()[0][:160]}")

    # ── la confrontation au TITULAIRE, ligne à ligne et non en volume ─────────────────────────────
    par_cle = {(it.question_id, it.ingredient_id): it for it in res.carte.items}
    ancree = {c for c, it in par_cle.items() if it.statut in ("exact", "approximation")}
    recuperees = sorted(cles_web & ancree)
    conservees = sorted(cles_edgar & ancree)
    abandonnees = sorted(c for c in cles_edgar
                         if c in par_cle and par_cle[c].statut == "indisponible")
    print(f"\n  CONFRONTATION {ticker} (mêmes {len(traduits)} lignes `traduit`) : "
          f"{len(recuperees)} récupérée(s) du web · {len(conservees)} conservée(s) sur EDGAR · "
          f"{len(abandonnees)} abandonnée(s)")
    for q, i in recuperees:
        it = par_cle[(q, i)]
        print(f"    RÉCUPÉRÉE  {q}.{i} → {it.statut} : {it.formule or ', '.join(it.concepts)}")

    # ── les critères ──────────────────────────────────────────────────────────────────────────────
    check(f"[2] {ticker} : l'état `approximation` est employé (la case que #67 crée)",
          par_statut.get("approximation", 0) > 0,
          f"→ {par_statut} : une carte sans aucune approximation n'a rien acheté, elle a renommé "
          "le choix binaire d'avant")
    check(f"[3] {ticker} : {len(recuperees)} ligne(s) RÉCUPÉRÉE(S) du web payant vers le dépôt",
          len(recuperees) > 0,
          f"→ aucune des {len(cles_web)} ligne(s) que l'aiguilleur sortant envoie au web n'est "
          "ancrée dans le dépôt : le maillon ne rend au tier A aucun ingrédient que le mécanisme "
          "qu'il remplace envoyait payer, donc il ne débloque rien")
    check(f"[5] {ticker} : les {len(traduits)} lignes `traduit` ont chacune un appariement "
          f"([T] tenu, redit sur une ligne réelle)",
          len(res.carte.items) == len(traduits),
          f"→ {len(res.carte.items)} appariement(s) pour {len(traduits)} ligne(s)")

    t_nomme, q_nomme, i_nomme, attendu = CAS_NOMME
    if ticker == t_nomme:
        trouve = next((it for it in res.carte.items
                       if (it.question_id, it.ingredient_id) == (q_nomme, i_nomme)), None)
        if trouve is None:
            check(f"[4] cas nommé {t_nomme} {q_nomme}.{i_nomme} → `{attendu}`", False,
                  f"→ ABSENT de la carte : la ligne est-elle `inobtenable` au plan ? C'est alors le "
                  "PLAN qu'il faut relire — le critère porte sur l'apparieur et n'est pas mesurable")
        else:
            check(f"[4] cas nommé {t_nomme} {q_nomme}.{i_nomme} → `{attendu}` "
                  f"(sorti `{trouve.statut}`)",
                  trouve.statut == attendu,
                  "→ un `indisponible` ici est le renoncement d'avant #67 : l'émetteur dépose "
                  "l'actif total, les dettes courantes et sa trésorerie, la soustraction est à "
                  "portée et elle est en tier A")

    # ── les MESURES non gardées ───────────────────────────────────────────────────────────────────
    print(f"\n  MESURE {ticker} · concepts nommés dont le dernier point a plus de 400 jours : "
          f"{len(vieux)} {vieux[:6]}")
    print("         (non gardé : un concept ABANDONNÉ est réellement déposé, donc `[V]` le laisse "
          "passer et la collecte remontera un vide. On chiffre avant de durcir.)")

    # Le SEUL endroit du fichier où une sortie s'imprime pour être lue et non pour être comptée.
    # Aucun assert ne peut trancher ces lignes (#68) : elles sont, une par une, soit un faux
    # appariement du titulaire correctement refusé, soit une frilosité de l'apparieur.
    print(f"\n  À LIRE {ticker} · {len(abandonnees)} ligne(s) ABANDONNÉE(S) — le titulaire les "
          "routait vers EDGAR, l'apparieur les dit `indisponible` :")
    for q, i in abandonnees:
        it = plan_par_cle[(q, i)]
        print(f"    ABANDONNÉE {q}.{i}")
        print(f"      poste nommé au plan : {it.poste} · métrique : {it.metrique}")
        print(f"      motif de l'apparieur : {par_cle[(q, i)].motif}")
    if not abandonnees:
        print("    (aucune — l'apparieur ancre tout ce que le titulaire routait vers EDGAR)")
    return 0


async def main() -> int:
    url = os.environ.get("DATABASE_URL") or ""
    if not url or not os.environ.get("DEEPINFRA_API_KEY"):
        print("DATABASE_URL / DEEPINFRA_API_KEY manquantes — l'acceptation appelle le VRAI modèle, "
              "elle ne se simule pas.", file=sys.stderr)
        return 2

    fichier = load_frameworks()
    await init_pool(url)
    non_mesurables = 0
    try:
        for ticker, framework_id, archetype in CAS:
            non_mesurables += 1 if await _un_cas(ticker, framework_id, archetype, fichier) == 2 else 0
    finally:
        await close_pool()

    print(f"\n{'='*100}")
    print(f"BILAN acceptation apparieur — {len(CAS)} émetteur(s) · {ok} critère(s) OK, "
          f"{fail} échec(s), {non_mesurables} non mesurable(s)")
    print("⚠️ Le reste s'apprécie À LA LECTURE, et aucun assert ne peut le remplacer (#68) : les "
          "formules disent-elles ce que l'ingrédient demande, les hypothèses sont-elles "
          "contestables, et les `indisponible` de RVMD se lisent-ils comme une propriété de "
          "l'émetteur (biotech pré-revenus : ni chiffre d'affaires, ni stocks, ni créances "
          "clients) plutôt que comme un trou de collecte ?")
    if non_mesurables:
        return 2
    return 1 if fail else 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
