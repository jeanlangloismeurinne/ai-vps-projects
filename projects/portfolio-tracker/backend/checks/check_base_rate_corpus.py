"""Vérification du corpus base rate + ancre `valorisation.base_rate_anchor` — PUR, sans réseau ni DB.

On vérifie : (1) l'arithmétique de la distribution colle aux chiffres EXACTS de l'Exhibit 2 (somme
des colonnes = 100 %, P(≥20 %/3 ans)=11,9 %) ; (2) le classifieur range NVDA en méga-cap et une
mid-cap correctement ; (3) l'ancre méga-cap est marquée « borne haute » ; (4) une base rate n'est
jamais fondée sur une classe inventée (lève si ni CA ni capitalisation).
"""
import sys

from app.knowledge.base_rate_corpus import (
    BaseRateUnavailable, SALES_GROWTH_DISTRIBUTION, _latest_revenue_usd, _mds, base_rate_ge,
    build_base_rate_anchor_spec, classify_reference_class, size_bucket,
)

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


print("\n1. Distribution = Exhibit 2 (chiffres exacts) — colonnes somment à 100 %")
for h in ("1Y", "3Y", "5Y", "10Y"):
    total = round(sum(freq[h] for _, freq in SALES_GROWTH_DISTRIBUTION), 1)
    check(f"colonne {h} = 100 %", abs(total - 100.0) < 0.15, f"→ {total}")

print("\n2. base_rate_ge — lookup conservateur, valeurs du livre")
check("P(≥20 %/an, 3 ans) = 11,9 %", base_rate_ge(20, "3Y") == 11.9, f"→ {base_rate_ge(20, '3Y')}")
check("P(≥15 %/an, 3 ans) = 18,6 %", base_rate_ge(15, "3Y") == 18.6, f"→ {base_rate_ge(15, '3Y')}")
check("P(≥45 %/an, 3 ans) = 2,5 %", base_rate_ge(45, "3Y") == 2.5, f"→ {base_rate_ge(45, '3Y')}")
check("P(≥20 %/an, 5 ans) = 8,5 %", base_rate_ge(20, "5Y") == 8.5, f"→ {base_rate_ge(20, '5Y')}")
check("P(≥20 %/an, 10 ans) = 4,5 %", base_rate_ge(20, "10Y") == 4.5, f"→ {base_rate_ge(20, '10Y')}")
check("horizon plus long ⇒ persistance plus rare", base_rate_ge(20, "3Y") > base_rate_ge(20, "10Y"))

print("\n3. size_bucket — maille du livre (CA, méga = >50 Md$)")
check("NVDA (CA 216 Md$) = mega", size_bucket(216e9, 5.1e12)[0] == "mega")
check("CA 25 Md$ = large", size_bucket(25e9, 300e9)[0] == "large")
check("CA 4 Md$ = mid", size_bucket(4e9, 20e9)[0] == "mid")
check("CA absent → repli capitalisation (basis noté)", size_bucket(None, 300e9)[2] == "capitalisation")

print("\n4. classify + ancre NVDA (méga-cap = borne haute)")
NVDA_M1 = {
    "price": {"market_cap": 5_140_000_000_000, "currency": "USD"},
    "financials_3y": {"2026": {"revenue": 215_938_000_000}, "2025": {"revenue": 130_497_000_000}},
}
rc = classify_reference_class(NVDA_M1)
check("classe NVDA = méga-cap sur base CA", rc["size_bucket"] == "mega" and rc["size_basis"] == "CA", f"→ {rc}")
spec = build_base_rate_anchor_spec("NVDA", "NVDA", NVDA_M1)
check("field = base_rate_anchor", spec.field == "base_rate_anchor")
check("entry_type = base_rate", spec.entry_type == "base_rate")
check("tags fondent valorisation.base_rate_anchor",
      "valorisation" in spec.tags and "base_rate_anchor" in spec.tags, f"→ {spec.tags}")
check("distribution complète portée en structuré",
      len(spec.content_structured["distribution"]) == 16)
check("seuils représentatifs présents (15/20/25)",
      set(spec.content_structured["thresholds_pct_ge"]) == {"15", "20", "25"})
check("méga-cap marquée borne haute", spec.content_structured["upper_bound_for_size"] is True)
check("le content dit que c'est une fréquence, pas un multiple",
      "FRÉQUENCE" in spec.content and "multiple" in spec.content, f"→ {spec.content[:120]}")
check("borne haute explicitée pour la taille", "Borne HAUTE" in spec.content)
check("source citée (Base Rate Book)", "Base Rate Book" in spec.content and spec.source_url.endswith(".pdf"))

print("\n5. mid-cap (non méga) : PAS de borne haute")
MID_M1 = {"price": {"market_cap": 20e9}, "financials_3y": {"2026": {"revenue": 4e9}}}
mid_spec = build_base_rate_anchor_spec("MID", "MID", MID_M1)
check("mid-cap non marquée borne haute", mid_spec.content_structured["upper_bound_for_size"] is False)
check("mid-cap sans mention 'Borne HAUTE'", "Borne HAUTE" not in mid_spec.content)

print("\n6. Classe indéterminable = échec EXPLICITE (jamais une classe inventée)")
try:
    classify_reference_class({"price": {}, "financials_3y": {}})
    check("BaseRateUnavailable si ni CA ni capitalisation", False, "aucune exception !")
except BaseRateUnavailable:
    check("BaseRateUnavailable si ni CA ni capitalisation", True)

print("\n7. RVMD — le libellé de classe qualifie le CA, jamais la taille boursière (F8)")
# Cas réel : biotech clinique à 44,8 Md$ de capitalisation pour < 1 Md$ de ventes. La classe est
# calculée sur le CA (c'est la maille du Base Rate Book, et c'est juste) mais son libellé emprunte
# le vocabulaire de la capitalisation — l'entry annonçait « small-cap » à un agent qui lit du texte.
# Tous les nombres justes, le fait faux : même famille que F6(a).
RVMD_M1 = {"price": {"market_cap": 44.8e9}, "financials_3y": {"2025": {"revenue": 0.12e9}}}
rv = build_base_rate_anchor_spec("RVMD", "RVMD", RVMD_M1)
s = rv.content_structured
check("classe toujours calculée sur le CA (on ne change pas la maille du livre)",
      s["size_bucket"] == "small" and s["size_basis"] == "CA", f"→ {s['size_bucket']}/{s['size_basis']}")
check("divergence des deux mailles DÉTECTÉE", s["mailles_divergentes"] is True)
check("maille capitalisation exposée à côté", s["size_bucket_par_capitalisation"] == "large",
      f"→ {s['size_bucket_par_capitalisation']}")
check("les deux mesures sont exposées (sinon le libellé n'est pas réfutable)",
      s["sales_usd"] == 0.12e9 and s["market_cap_usd"] == 44.8e9)
check("le texte AVERTIT de ne pas lire une petite capitalisation",
      "ne pas le lire comme une petite" in rv.content, f"→ {rv.content}")
check("le texte chiffre les deux mailles", "44,8 Md$" in rv.content and "120,0 M$" in rv.content,
      f"→ {rv.content}")
check("l'écart est présenté comme l'information, pas comme un défaut",
      "pas un défaut de classement" in rv.content)

print("\n8. Mailles concordantes : AUCUN avertissement (le mettre partout le rendrait invisible)")
# Contrepartie du #42 : une mention portée par tous les cas ne distingue plus le cas qui compte.
check("NVDA (méga sur les deux mailles) ne porte pas la mention",
      spec.content_structured["mailles_divergentes"] is False
      and "ne pas le lire comme une petite" not in spec.content)
check("MID (mid sur CA, large sur cap) la porte, elle", mid_spec.content_structured["mailles_divergentes"] is True)

print("\n9. Repli capitalisation : le libellé annonce la maille RÉELLEMENT mesurée")
# Avant F8, `size_bucket(None, 300e9)` rendait « large-cap (CA 10-50 Md$) » : une tranche de CA
# affichée alors qu'aucun CA n'est connu — le repli était noté dans `basis` et démenti dans le texte.
check("maille CA inchangée mot pour mot", size_bucket(216e9, 5.1e12)[1] == "méga-cap (CA > 50 Md$)",
      f"→ {size_bucket(216e9, 5.1e12)[1]}")
check("repli capitalisation : le libellé le dit",
      size_bucket(None, 300e9)[1] == "méga-cap (capitalisation > 50 Md$)",
      f"→ {size_bucket(None, 300e9)[1]}")
check("aucune tranche de CA annoncée sans CA", "CA" not in size_bucket(None, 20e9)[1],
      f"→ {size_bucket(None, 20e9)[1]}")

print("\n10. Le montant choisit son unité — un arrondi à zéro serait un fait faux (F9)")
# Cas réel : RVMD fait 11,58 M$ de ventes. En unité fixe « Md$ », le texte de la divergence
# annonçait « 0,0 Md$ de ventes » — l'agent lit AUCUNE vente, et c'est justement ce chiffre qui
# fonde l'écart de mailles que §7 vient de déclarer. Même famille que F8 : le nombre est juste,
# la phrase est fausse.
check("11,58 M$ ne s'écrit pas « 0,0 Md$ »", _mds(11_580_000.0) == "11,6 M$", f"→ {_mds(11_580_000.0)}")
check("les milliards restent en Md$", _mds(44.86e9) == "44,9 Md$", f"→ {_mds(44.86e9)}")
check("l'unité descend jusqu'aux milliers", _mds(45_000.0) == "45,0 k$", f"→ {_mds(45_000.0)}")
check("une ABSENCE reste 'n/d', jamais un zéro", _mds(None) == "n/d")
check("un VRAI zéro se distingue d'un arrondi", _mds(0.0) == "0 $", f"→ {_mds(0.0)}")
check("aucun montant non nul ne s'arrondit à zéro",
      all(not _mds(v).startswith("0,0 ") for v in (1.0, 999.0, 1e3, 1e6 - 1, 11.58e6, 1e9 - 1)),
      f"→ {[_mds(v) for v in (1.0, 999.0, 1e3, 1e6 - 1, 11.58e6, 1e9 - 1)]}")
# Trouvé PAR le check ci-dessus, qui a viré au rouge sur 999 999 $ : l'unité était choisie avant
# l'arrondi, donc l'arrondi faisait franchir le palier à la valeur sans que l'unité suive.
check("l'arrondi PROMEUT l'unité (999 999 $ ≠ « 1000,0 k$ »)", _mds(1e6 - 1) == "1,0 M$",
      f"→ {_mds(1e6 - 1)}")
check("aucun montant n'affiche 4 chiffres devant la virgule",
      all(len(_mds(v).split(",")[0].lstrip("-")) <= 3 for v in (999.0, 1e6 - 1, 1e9 - 1, 999.9e9)),
      f"→ {[_mds(v) for v in (999.0, 1e6 - 1, 1e9 - 1, 999.9e9)]}")
check("un montant de 11,58 M$ ne s'écrit pas « 0,0 Md$ »",
      _mds(11_580_000.0) == "11,6 M$" and _mds(11_580_000.0) != "0,0 Md$")

print("\n11. Un CA NUL est une valeur, pas une absence (F11)")
# ⚠️ La fixture de §10 disait `{"2025": {"revenue": 11_580_000}}`. C'est ce que la PROD ne dit pas :
# `financials_3y` porte 2023=11,58 M$, 2024=0,0, 2025=0,0 (vérifié dans market_snapshots, et EDGAR
# concorde sous `RevenueFromContractWithCustomerExcludingAssessedTax`). La fixture était plus
# aimable que le réel — donc verte pour toujours sur un cas qui n'existe pas. Corrigée ici.
RVMD_PROD = {
    "price": {"market_cap": 44.86e9},
    "financials_3y": {"2023": {"revenue": 11_580_000.0},
                      "2024": {"revenue": 0.0},
                      "2025": {"revenue": 0.0}},
}
val, fy = _latest_revenue_usd(RVMD_PROD)
check("un 0,0 n'est PAS sauté au profit d'un exercice antérieur", val == 0.0, f"→ {val}")
check("l'exercice retenu est le plus récent, pas le dernier non nul", fy == "2025", f"→ {fy}")
check("un CA réellement absent reste None (une absence n'est pas un zéro)",
      _latest_revenue_usd({"financials_3y": {"2025": {}}}) == (None, None))
check("un CA non nul est toujours rendu avec son exercice",
      _latest_revenue_usd({"financials_3y": {"2026": {"revenue": 216e9}}}) == (216e9, "2026"))

prod = build_base_rate_anchor_spec("RVMD", "RVMD", RVMD_PROD)
ps = prod.content_structured
check("le structuré porte le CA de l'exercice courant, pas celui d'il y a deux ans",
      ps["sales_usd"] == 0.0, f"→ {ps['sales_usd']}")
check("le flux est daté (#42) — sans exercice, le chiffre n'est pas réfutable",
      ps["sales_fiscal_year"] == "2025", f"→ {ps['sales_fiscal_year']}")
check("le texte n'annonce PLUS un chiffre vieux de deux exercices",
      "11,6 M$" not in prod.content, f"→ {prod.content}")
check("le texte dit 0 $ de ventes, daté", "0 $ de ventes (FY2025)" in prod.content,
      f"→ {prod.content}")
check("la classe reste calculée sur le CA (un zéro ne change pas la maille du livre)",
      ps["size_bucket"] == "small" and ps["size_basis"] == "CA")
check("la divergence des mailles tient toujours", ps["mailles_divergentes"] is True)

print("\n12. Base de ventes nulle : la limite de l'ancre est DÉCLARÉE, l'ancre n'est pas retirée")
# Un CAGR de ventes depuis zéro est indéfini (le premier dollar vendu est une croissance infinie).
# On ne supprime pas l'ancre — la classe est juste et l'outside view sur la persistance reste
# valable ; on refuse seulement qu'un reverse-DCF en aval la prenne pour un taux applicable.
check("le drapeau est levé", ps["base_ventes_nulle"] is True)
check("le texte dit qu'un CAGR ne se calcule pas depuis zéro",
      "ne se calcule pas depuis" in prod.content, f"→ {prod.content}")
check("le texte qualifie ce zéro de propriété mesurée, pas de trou de collecte",
      "pas un trou de collecte" in prod.content)
check("l'ancre est CONSERVÉE (distribution et seuils toujours portés)",
      len(ps["distribution"]) == 16 and set(ps["thresholds_pct_ge"]) == {"15", "20", "25"})
# Contrepartie du #45 : une mention portée par tous les cas ne distingue plus le cas qui compte.
check("un émetteur qui vend ne porte pas le drapeau",
      spec.content_structured["base_ventes_nulle"] is False
      and mid_spec.content_structured["base_ventes_nulle"] is False)
check("ni le paragraphe", "ne se calcule pas depuis" not in spec.content
      and "ne se calcule pas depuis" not in mid_spec.content)
check("un CA ABSENT n'est pas un CA nul (repli capitalisation, pas de drapeau)",
      build_base_rate_anchor_spec(
          "X", "X", {"price": {"market_cap": 300e9}, "financials_3y": {}}
      ).content_structured["base_ventes_nulle"] is False)

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
