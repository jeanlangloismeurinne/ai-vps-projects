"""LA SOCIÉTÉ MISE À L'ÉTUDE vue de l'écran : son dossier, ce que la collecte a trouvé ou pas, les
documents lus et les pièces (M2 B12, M3 K12 : `roadmap/V3/M3-base-connaissance.md`).

  GET  /v2/emetteurs/{emetteur}/etude                     l'étude, l'état du dossier (actes en mots de
                                                          gérant), la collecte, les documents lus, les pièces
  POST /v2/emetteurs/{emetteur}/etude                     met la société à l'étude (motif)
  POST /v2/emetteurs/{emetteur}/etude/acte                enregistre l'acte attendu (sa clé)
  POST /v2/emetteurs/{emetteur}/etude/pause               autorise un palier de dépense de plus
  POST /v2/emetteurs/{emetteur}/etude/relance             réessaie après un échec répété (un pas, ou tous)
  GET  /v2/emetteurs/{emetteur}/lectures/{empreinte}      des lignes d'un document lu (au plus 400)

Aucune règle ici : tout passe par les `contrat` des modules. Les corps n'acceptent NI auteur NI date
(`extra="forbid"`) : l'auteur est toujours l'utilisateur, la date celle du serveur. Les gestes ne
lancent rien : la tâche de fond fait avancer le dossier à son passage suivant. Rien de payant ne part
d'ici (aucun outil de collecte ni évaluateur n'est construit).

Un geste refusé (société sans fiche, acte non attendu, pause non posée) est un 409 qui dit pourquoi ;
un état rangé entre-temps par un passage, un 409 aussi (il suffit de refaire le geste).
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db.database import get_db_session
from app.modules.chef_de_dossier import contrat as CD
from app.modules.connaissance import contrat as K
from app.modules.etude import contrat as T
from app.modules.recueil import contrat as R

router = APIRouter(tags=["etude-v2"])

LIGNES_MAX = 400


class CorpsMise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motif: str


class CorpsActe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cle: str


class CorpsRelance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pas: str | None = None


class CorpsVide(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _aujourdhui() -> str:
    return date.today().isoformat()


@router.get("/v2/emetteurs/{emetteur}/etude")
async def vue_etude(emetteur: str) -> dict:
    async with get_db_session() as conn:
        monde = T.monde_en_base(conn)
        return {
            "etude": await T.vue_ecran(monde, emetteur),
            "collecte": await R.vue_ecran(monde.recueil, emetteur),
            "connaissance": await K.vue_ecran(monde.connaissance, recueil_depot=monde.recueil,
                                              emetteurs_depot=monde.emetteurs, emetteur=emetteur),
        }


async def _geste(emetteur: str, faire) -> dict:
    async with get_db_session() as conn:
        monde = T.monde_en_base(conn)
        try:
            await faire(monde)
        except T.GesteRefuse as e:
            raise HTTPException(status_code=409, detail=str(e))
        except CD.EcritureConcurrente:
            raise HTTPException(status_code=409, detail="Le dossier a avancé pendant votre geste : "
                                                        "rechargez la page et refaites-le.")
        return await T.vue_ecran(monde, emetteur)


@router.post("/v2/emetteurs/{emetteur}/etude")
async def mettre_a_l_etude(emetteur: str, corps: CorpsMise) -> dict:
    async def faire(monde):
        async with monde.transaction():
            await T.mettre_a_l_etude(monde, emetteur, par=T.UTILISATEUR, motif=corps.motif, le=_aujourdhui())
    return await _geste(emetteur, faire)


@router.post("/v2/emetteurs/{emetteur}/etude/acte")
async def enregistrer_acte(emetteur: str, corps: CorpsActe) -> dict:
    return await _geste(emetteur, lambda m: T.enregistrer_acte(m, emetteur, corps.cle, le=_aujourdhui()))


@router.post("/v2/emetteurs/{emetteur}/etude/pause")
async def lever_pause(emetteur: str, corps: CorpsVide) -> dict:
    return await _geste(emetteur, lambda m: T.lever_pause(m, emetteur, le=_aujourdhui()))


@router.post("/v2/emetteurs/{emetteur}/etude/relance")
async def relancer(emetteur: str, corps: CorpsRelance) -> dict:
    return await _geste(emetteur, lambda m: T.relancer(m, emetteur, pas=corps.pas, le=_aujourdhui()))


@router.get("/v2/emetteurs/{emetteur}/lectures/{empreinte}")
async def lignes(emetteur: str, empreinte: str, debut: int = 1, fin: int | None = None) -> dict:
    """Les lignes [debut, fin] de la lecture COURANTE d'un document de cet émetteur (celle que l'écran
    montre) ; 404 si l'émetteur n'a pas de lecture lue de ce document."""
    if fin is None or fin - debut + 1 > LIGNES_MAX:
        fin = debut + LIGNES_MAX - 1
    async with get_db_session() as conn:
        monde = T.monde_en_base(conn)
        c = await K.lire_connaissance(monde.connaissance, recueil_depot=monde.recueil,
                                      emetteurs_depot=monde.emetteurs, emetteur=emetteur)
        lecture = next((l for l in c.lectures if l.empreinte == empreinte and l.statut == K.LUE), None)
        if lecture is None:
            raise HTTPException(status_code=404, detail=f"Aucun document lu d'empreinte `{empreinte}` pour `{emetteur}`.")
        texte = await K.lire_lignes(monde.connaissance, empreinte, lecture.lecteur, debut, fin)
    return {"empreinte": empreinte, "lecteur": lecture.lecteur, "nb_lignes": lecture.nb_lignes,
            "debut": max(debut, 1), "lignes": list(texte)}
