"""Garde de la probabilité de nouveau plus haut à 12 mois : à l'instant t, rien que du passé.

Hors ligne, séries synthétiques. Éprouve (1) que p(t) ne change pas quand on retire tout ce qui suit t,
(2) que les résultats sont corrects (atteint / manqué / en cours), (3) qu'aucune observation d'apprentissage
n'a son résultat postérieur à la coupure, (4) que le check VIRE AU ROUGE avec des variables qui regardent l'avenir.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.nasdaq import proba  # noqa: E402

ko: list[str] = []
ok_n = 0


def check(name: str, cond: bool) -> None:
    global ok_n
    if cond:
        ok_n += 1
    else:
        ko.append(name)


def walk(seed: int, n: int = 2600):
    r = np.random.default_rng(seed)
    c = 50 * np.exp(np.cumsum(r.normal(0.0004, 0.017, n)))
    return np.arange(15000, 15000 + n, dtype=np.int64) * 1 + (np.arange(n) // 5) * 2, c


def fake_models(day, c):
    s = proba.training_samples(day, c)
    X, y = s[2], s[3].astype(float)
    return {2012: proba.fit_logit(X, y), 2015: proba.fit_logit(X[: len(X) // 2], y[: len(y) // 2])}


def pit_ok(feat_fn) -> bool:
    """p(t) calculée sur la série complète == p(t) calculée sur la série coupée en t, pour des t échantillonnés."""
    real = proba.features
    proba.features = feat_fn
    try:
        day, c = walk(1)
        models = fake_models(day, c)
        full = proba.curve(day, c, models, years=None)
        good = True
        for k in (5, 40, 90):
            cut = len(c) - 21 * k
            part = proba.curve(day[:cut], c[:cut], models, years=None)
            fd = dict(zip(full["d"], full["p"]))
            good &= len(part['d']) > 10
            good &= all(fd[d] == p for d, p in zip(part["d"], part["p"]))
        return good
    finally:
        proba.features = real


def leaky_features(day, c, cm, idx):
    X = _orig(day, c, cm, idx)
    fut = np.minimum(idx + 126, len(c) - 1)
    X[:, 2] = np.log(c[fut] / c[idx])   # fuite : rendement des 6 mois SUIVANTS
    return X


_orig = proba.features

check("p(t) ne dépend que du passé", pit_ok(_orig))
check("le check détecte une variable qui regarde l'avenir (test négatif)", not pit_ok(leaky_features))

# Résultats : pic à la séance 100, retour au-dessus à 300 → atteint pour t=100..., manqué si > 252 séances
cm = np.maximum.accumulate(np.concatenate([np.linspace(10, 20, 100), np.linspace(20, 15, 400), np.linspace(15, 25, 100)]))
idx = np.array([50, 150, 300, 520, 599])
o = proba.outcomes(cm, idx)
check("t=50 : nouveau plus haut au plus tard à t+252 → atteint", o[0] == 1)
check("t=150 : remonte au-dessus du pic à ~550 > 150+252 → manqué", o[1] == 0)
check("t=520 : nouveau plus haut avant la fin des données → atteint", o[3] == 1)
flat = np.maximum.accumulate(np.concatenate([np.linspace(10, 20, 100), np.linspace(20, 15, 400)]))
check("t=450 : fenêtre incomplète et pas de nouveau plus haut → en cours", proba.outcomes(flat, np.array([450]))[0] == -1)
check("t=100 : 252 séances écoulées sans nouveau plus haut → manqué", proba.outcomes(flat, np.array([100]))[0] == 0)
check("t=599 (dernier) → atteint ou en cours, jamais manqué", o[4] != 0)

# Coupure d'apprentissage : toute observation retenue pour l'année Y a son résultat connu au 1er janvier de Y
day, c = walk(3)
s = proba.training_samples(day, c)
check("jour de résultat = jour de l'observation + 252 séances", bool((s[1] > s[0]).all()))
cut = int(np.median(s[1]))
check("seules des observations au résultat connu passent sous la coupure", bool((s[1][s[1] <= cut] <= cut).all()) and bool((s[0][s[1] <= cut] < cut).all()))

# Aucune probabilité avant le premier modèle
models = {2100: proba.fit_logit(s[2], s[3].astype(float))}
check("avant le premier modèle : pas de probabilité (None, jamais inventée)", proba.curve(day, c, models, years=None) is None)

if ko:
    print(f"{len(ko)} FAIL : " + " | ".join(ko))
    sys.exit(1)
print(f"nasdaq proba : {ok_n} ok / 0 FAIL")
