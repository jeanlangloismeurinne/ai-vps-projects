"""Deux modèles de valorisation FICTIFS, un par forme de fourchette arbitrée le 2026-09-29 (#97) —
partagés par `check_modele_valorisation` (contrat, pont, évaluation) et `check_signature_modele`
(signature, registre). Un seul exemplaire : deux copies re-divergeraient au premier correctif.

  · forme RVMD (incertitude BINAIRE) : arbre d'événements, somme des programmes pondérée ;
  · forme NVDA (incertitude CONTINUE) : trois scénarios nommés sur des segments.
Les chiffres éprouvent la mécanique, pas les titres.
"""
from __future__ import annotations


def piece(*ids: int) -> dict:
    return {"type": "piece", "source_entry_refs": [{"entry_id": i} for i in ids]}


def jugement(ref: int) -> dict:
    return {"type": "jugement",
            "taux_de_base": {"classe_de_reference": "programmes de phase 2 en oncologie, 2000-2020",
                             "valeur": 0.3, "source_entry_refs": [{"entry_id": ref}]},
            "ecart_justifie": "Mécanisme d'action validé chez l'homme en phase 1, au-dessus de la classe."}


def reprise(qid: str, aid: int) -> dict:
    return {"type": "reponse_reprise", "question_id": qid, "answer_id": aid}


def hyp(nom: str, valeur: float, origine: dict, segment: str | None = None) -> dict:
    return {"nom": nom, "segment": segment, "libelle": f"libellé de {nom}", "unite": "u",
            "valeur": valeur, "origine": origine}


METHODO = ("Somme des programmes : chaque molécule vaut ses ventes nettes actualisées sur sa durée "
           "d'exclusivité, pondérées par sa probabilité de succès ; on ajoute la trésorerie nette.")

ARBRE = {
    "ticker_id": "RVMD", "version": 1, "methodologie": METHODO,
    "motif_de_la_forme": "La valeur dépend d'essais qui réussissent ou échouent : incertitude binaire.",
    "segments": [
        {"id": "programme_a", "libelle": "Pancréas 1re ligne", "perimetre": "Adénocarcinome pancréatique métastatique, première ligne."},
        {"id": "programme_b", "libelle": "Poumon", "perimetre": "Cancer du poumon non à petites cellules muté."},
    ],
    "hypotheses": [
        hyp("cout_du_capital", 0.1, reprise("qf_1", 901)),
        hyp("tresorerie_nette", 10, piece(501)),
        hyp("actions", 10, piece(502)),
        hyp("marge_nette", 0.3, jugement(503)),
        hyp("probabilite", 0.5, jugement(503), "programme_a"),
        hyp("ventes_pic", 100, jugement(503), "programme_a"),
        hyp("duree", 2, piece(504), "programme_a"),
        hyp("lancement", 1, piece(504), "programme_a"),
        hyp("probabilite", 0.4, jugement(503), "programme_b"),
        hyp("ventes_pic", 50, jugement(503), "programme_b"),
        hyp("duree", 1, piece(504), "programme_b"),
        hyp("lancement", 2, piece(504), "programme_b"),
    ],
    "fourchette": {"forme": "arbre_evenements", "evenements": [
        {"id": "succes_a", "recit": "Le programme A obtient son autorisation en 1re ligne.", "probabilite": "programme_a.probabilite"},
        {"id": "succes_b", "recit": "Le programme B obtient son autorisation dans le poumon.", "probabilite": "programme_b.probabilite"},
    ]},
    "mecanique": """
valeur = 0
for nom in segments:
    p = segments[nom]
    flux = [p["ventes_pic"] * marge_nette for _ in range(p["duree"])]
    valeur += valeur_ponderee(p["probabilite"], actualiser(flux, cout_du_capital, p["lancement"]))
valeur_action = valeur_par_action(valeur_fonds_propres(valeur, -tresorerie_nette), actions)
""",
}

SCENARIOS = {
    "ticker_id": "NVDA", "version": 1,
    "methodologie": ("Modèle par segment : chaque segment dégage un flux libre égal à son chiffre d'affaires "
                     "par sa marge, qui croît trois ans avant une croissance perpétuelle ; somme actualisée."),
    "motif_de_la_forme": "Croissance et marges varient continûment avec le cycle : scénarios nommés.",
    "segments": [
        {"id": "centres_de_donnees", "libelle": "Centres de données", "perimetre": "Accélérateurs et réseaux pour l'IA."},
        {"id": "jeux", "libelle": "Jeux", "perimetre": "Cartes graphiques grand public."},
    ],
    "hypotheses": [
        hyp("cout_du_capital", 0.1, reprise("qf_1", 902)),
        hyp("croissance_terminale", 0.03, jugement(603)),
        hyp("actions", 10, piece(602)),
        hyp("ca", 100, piece(601), "centres_de_donnees"),
        hyp("marge_fcf", 0.5, piece(601), "centres_de_donnees"),
        hyp("croissance", 0.2, jugement(603), "centres_de_donnees"),
        hyp("ca", 20, piece(601), "jeux"),
        hyp("marge_fcf", 0.25, piece(601), "jeux"),
        hyp("croissance", 0.0, jugement(603), "jeux"),
    ],
    "fourchette": {"forme": "scenarios_nommes", "scenarios": [
        {"role": "bas", "recit": "Le cycle des centres de données se retourne en 2027.",
         "valeurs": {"centres_de_donnees.croissance": 0.0, "centres_de_donnees.marge_fcf": 0.4}},
        {"role": "central", "recit": "La demande d'IA suit le rythme annoncé par la direction."},
        {"role": "haut", "recit": "Les inférences en entreprise doublent la demande prévue.",
         "valeurs": {"centres_de_donnees.croissance": 0.3}},
    ]},
    "mecanique": """
flux = [0.0, 0.0, 0.0]
for nom in segments:
    s = segments[nom]
    f = flux_en_croissance(s["ca"] * s["marge_fcf"], s["croissance"], 3)
    flux = [flux[i] + f[i] for i in range(3)]
valeur_action = dcf(flux, cout_du_capital, croissance_terminale) / actions
""",
}
# Les reprises que le RÉFÉRENTIEL déclare (`repris_de`) — lues dans les données, jamais recopiées ici.
from app.agents.v2.frameworks import load_frameworks  # noqa: E402
from app.valorisation.signature import reprises_admises  # noqa: E402

REPRISES = reprises_admises(load_frameworks())
DOSSIER_RVMD = {"reponses_acquittees": {901: "qf_1"}, "pieces_du_dossier": {501, 502, 503, 504},
                "questions_sans_objet": frozenset(), "reprises_admises": REPRISES}
DOSSIER_NVDA = {"reponses_acquittees": {902: "qf_1"}, "pieces_du_dossier": {601, 602, 603},
                "questions_sans_objet": frozenset(), "reprises_admises": REPRISES}
