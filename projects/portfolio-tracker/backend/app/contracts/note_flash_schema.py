"""Contrat de la NOTE FLASH — la lecture d'un communiqué dont la forme ne dit pas la substance (V3 lot 7,
maillon 2 de la taxonomie des événements, `roadmap/V3/04-taxonomie-evenements.md` §10).

Ce que ferait un vrai fonds
---------------------------
Le jour d'une publication, l'analyste qui couvre le titre la LIT et écrit une note flash : « événement
X ; incidence sur la thèse : aucune / à revoir sur tel et tel point ». Il cite le passage qui fonde son
classement ; devant un avertissement sur résultats, il répond d'abord à « l'entreprise ou le secteur ? »
(arbitrage Q2 : cause non dite = cause concurrentielle) ; et quand le communiqué ne permet pas de
trancher, il le dit — le point reste rouvert (Q3 : dans le doute, on rouvre).

Ce que le MODÈLE produit, et ce que le CODE en dérive
-----------------------------------------------------
Le modèle ne rend que sa LECTURE (`NoteFlashSortie`) : des éléments « type + passage cité », ou un
constat d'illisibilité motivé. Il ne rend jamais le type `surprise_*` lui-même : il dit `surprise` et
une CAUSE, et le code dérive le type (`type_derive`) — même forme que le rang d'une réponse, dérivé et
non déclaré (#57). Une cause `non_dite` devient `surprise_concurrence` PAR LE CODE : laisser le modèle
choisir le type ferait de l'arbitrage Q2 une consigne qu'il peut oublier.

Ce que le contrat NE PEUT PAS vérifier — et qui l'est ailleurs
--------------------------------------------------------------
Que chaque passage soit une citation LITTÉRALE du dépôt, et que chaque type existe au catalogue du
référentiel : ce sont des faits du dossier et du référentiel, pas de la forme de la sortie. Le pont
`note_flash.valider_note` les tient. Qu'un passage cité justifie VRAIMENT le type choisi : aucune
garde ne le peut (`feedback_garde_structure_pas_sens`) — la preuve de sens est la LECTURE des notes en
texte (`tools/rediger_notes_flash.sh`).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, model_validator

from app.contracts.analysis_v2_schemas import Strict

__all__ = [
    "CAUSES_SURPRISE", "SURPRISE", "ElementNoteFlash", "NoteFlashSortie", "type_derive",
]

# Le pseudo-type par lequel le modèle signale un écart aux attentes. Il n'est PAS au catalogue : seul
# le code le traduit en `surprise_<cause>`.
SURPRISE = "surprise"
CAUSES_SURPRISE = ("secteur", "concurrence", "execution", "non_dite")
Cause = Literal["secteur", "concurrence", "execution", "non_dite"]

# Une citation plus courte ne prouve rien (« FDA », « agreement ») : elle se trouverait dans n'importe
# quel dépôt. 30 caractères ≈ une proposition complète.
PASSAGE_MIN = 30


class ElementNoteFlash(Strict):
    """Un point touché par le dépôt : son type, et le passage du dépôt qui le fonde."""
    type: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    passage: str = Field(min_length=PASSAGE_MIN)
    # Pour `surprise` seulement : la cause que donne le communiqué, et le passage qui la dit.
    cause: Optional[Cause] = None
    passage_cause: Optional[str] = Field(default=None, min_length=PASSAGE_MIN)

    @model_validator(mode="after")
    def _la_cause_appartient_a_la_surprise(self) -> "ElementNoteFlash":
        if self.type == SURPRISE:
            if self.cause is None:
                raise ValueError("un écart aux attentes (`surprise`) dit sa cause — `non_dite` si "
                                 "le communiqué ne la donne pas")
            if self.cause == "non_dite" and self.passage_cause is not None:
                raise ValueError("une cause `non_dite` ne se cite pas")
            if self.cause != "non_dite" and self.passage_cause is None:
                raise ValueError(f"la cause `{self.cause}` se prouve par le passage qui la dit "
                                 "(`passage_cause`) ; sinon elle est `non_dite`")
        elif self.cause is not None or self.passage_cause is not None:
            raise ValueError(f"`cause` n'a de sens que pour `{SURPRISE}` (reçu sur `{self.type}`)")
        if self.type.startswith("surprise_"):
            raise ValueError(f"`{self.type}` : dis `{SURPRISE}` et sa cause, le type s'en déduit")
        return self


class NoteFlashSortie(Strict):
    """Ce que le MODÈLE rend. Deux formes, jamais mêlées :
    · `lisible=True` — au moins un élément, chacun cité ;
    · `lisible=False` — aucun élément, et un motif : le dépôt reste rouvert sur tout (Q3)."""
    lisible: bool
    elements: list[ElementNoteFlash] = Field(default_factory=list)
    motif: Optional[str] = Field(default=None, min_length=20)

    @model_validator(mode="after")
    def _deux_formes(self) -> "NoteFlashSortie":
        if self.lisible and not self.elements:
            raise ValueError("une note lisible range le dépôt dans au moins un type")
        if not self.lisible and (self.elements or not self.motif):
            raise ValueError("une note illisible n'a aucun élément et dit pourquoi (`motif`)")
        return self


def type_derive(element: ElementNoteFlash) -> str:
    """Le type d'événement d'un élément, tel que le CODE le fixe. `surprise` + cause non dite ⟹
    `surprise_concurrence` (arbitrage Q2 : par prudence, la barrière est mise en doute)."""
    if element.type != SURPRISE:
        return element.type
    return "surprise_" + ("concurrence" if element.cause == "non_dite" else element.cause)
