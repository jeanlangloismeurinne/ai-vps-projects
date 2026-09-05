"""Outil `create_reminder` — premier outil à effet de bord (#1787579840505).

## Frontière modèle / code (roadmap §2.3 — non négociable)

| Le modèle fait | Le code fait |
|---|---|
| Extraire un titre et une date **décomposée** (mode + composants) | Résoudre en `TIMESTAMPTZ` depuis un `now` qu'il fournit lui-même |
| Rien d'autre | Choisir le board, la colonne, valider les bornes, écrire, confirmer, journaliser |

La surface d'attaque se réduit donc à **un titre et quelques entiers validés**. Le pire cas d'une
injection réussie est un rappel parasite, visible dans le fil et supprimable en un clic.

## Pourquoi une date décomposée plutôt qu'une date ISO

Demander une date ISO au modèle reviendrait à lui faire résoudre « demain » — donc à lui faire
deviner `now`, ce que le ticket interdit explicitement. Demander une expression libre (« mardi
prochain ») imposerait un analyseur de langue en Python : soit une dépendance au comportement
difficile à auditer, soit un analyseur maison fragile.

La décomposition est la troisième voie : le modèle fait ce qu'il sait faire — traduire une
formulation en `mode` + composants, sans connaître la date du jour — et le code fait de
l'arithmétique de calendrier, testable et lisible. Un mode inconnu est refusé, il n'existe pas de
chemin par défaut silencieux.

## L'année manquante (mesuré le 2026-09-05, rejeu de C6)

« Crée un rappel pour le 1er décembre » ne porte **pas** d'année. Le schéma n'exigeait qu'un
`AAAA-MM-JJ` : le modèle devait donc en inventer une, et il a écrit `2025-12-01` — son année de
coupure. Le code a refusé la date passée, à juste titre, le modèle a demandé une précision, et
l'action a été perdue. Le refus était bon ; **c'est la question posée au modèle qui était
impossible**, puisqu'elle lui demandait une information qu'il n'a pas et qu'on lui interdit par
ailleurs de deviner.

`date` accepte donc aussi `MM-JJ`. Le modèle n'écrit l'année que si l'utilisateur l'a dite ; sinon
le **code** choisit la prochaine occurrence. C'est la même frontière qu'ailleurs dans ce module :
le modèle rapporte ce qui a été dit, le code fait le calendrier.

## Le titre et le corps

Un rappel a deux parties de nature différente : *ce qu'il faut faire* (le titre, lu dans la
notification Slack) et *ce qu'il faut avoir sous les yeux à ce moment-là* (la liste de courses, les
références). Tant qu'il n'existait qu'un champ, tout se déversait dans le titre — 165 caractères
mesurés sur C7, seconde phrase de l'utilisateur comprise. Un champ n'est pas une préférence
d'affichage : **le modèle range mal ce qu'on ne lui a pas donné où ranger.**
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.services import kanban as kanban_svc
from app.services.agent_time import TZ, format_local, now_local
from app.services.agent_tools.base import PreparedCall, ToolContext, ToolError, ToolResult, ToolSpec
from app.services.agent_tools.manifest import Effect, RateLimit, ToolManifest

logger = logging.getLogger(__name__)

# Constantes de code, jamais des arguments du modèle : c'est ce qui garantit qu'un contenu
# injecté ne peut pas rediriger un rappel vers un autre board (roadmap §2.3).
REMINDER_COLUMN = "Rappels"
DEFAULT_BOARD_NAME = "Personnel"
DEFAULT_TIME = "09:00"

# Le titre est ce que l'utilisateur lit dans sa notification Slack : il doit tenir d'un coup d'œil.
# Dépassement = erreur explicite et non troncature — tronquer perdrait la fin de la charge utile
# sans que personne ne le voie, alors que l'erreur dit au modèle où mettre le reste (`details`).
TITLE_MAX = 60
DETAILS_MAX = 2_000
# Un rappel dans plus de deux ans n'est jamais une intention réelle — c'est une erreur de
# résolution. Refusé explicitement plutôt que corrigé en silence.
HORIZON_MAX = timedelta(days=730)
# Tolérance sur le passé : le temps qui passe entre la résolution et l'écriture ne doit pas
# transformer « dans 1 minute » en refus.
PAST_TOLERANCE = timedelta(minutes=2)

_JOURS = {
    "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3,
    "vendredi": 4, "samedi": 5, "dimanche": 6,
}

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": f"Ce qu'il faut faire, en quelques mots — {TITLE_MAX} caractères "
                           f"maximum. C'est le texte de la notification Slack. "
                           f"Ex. « acheter les courses », « appeler le garage ». "
                           f"N'y mets jamais une liste ni un détail : ils vont dans `details`.",
        },
        "details": {
            "type": "string",
            "description": "Ce que l'utilisateur doit avoir sous les yeux au moment du rappel : "
                           "les articles à acheter, les références, le lien concerné. Markdown "
                           "libre, un élément par ligne. Reprends ses mots. "
                           "N'y mets que ce qu'il demande de lui rappeler. Ce dont il dit "
                           "s'occuper lui-même, ou qu'il a déjà, ne figure **nulle part** dans "
                           "le rappel — ni en liste, ni en aparté, ni entre parenthèses. "
                           "Un rappel ne redit pas à l'utilisateur ce qu'il vient de te dire.",
        },
        "date_mode": {
            "type": "string",
            "enum": ["in_minutes", "offset_days", "weekday", "absolute"],
            "description": (
                "Comment la date a été formulée. "
                "`in_minutes` : « dans 20 minutes », « dans 2 heures » (convertir en minutes). "
                "`offset_days` : « aujourd'hui » (0), « demain » (1), « après-demain » (2), "
                "« dans 3 jours » (3). "
                "`weekday` : « mardi », « lundi prochain » — la prochaine occurrence de ce jour. "
                "`absolute` : une date explicite (« le 12 septembre »). "
                "Tu ne connais pas la date d'aujourd'hui : ne la calcule jamais toi-même."
            ),
        },
        "in_minutes": {"type": "integer", "description": "Si date_mode = in_minutes."},
        "offset_days": {"type": "integer", "description": "Si date_mode = offset_days. 0 = aujourd'hui."},
        "weekday": {
            "type": "string",
            "enum": list(_JOURS),
            "description": "Si date_mode = weekday.",
        },
        "date": {
            "type": "string",
            "description": (
                "Si date_mode = absolute. `MM-JJ` quand l'utilisateur n'a pas dit l'année "
                "(« le 1er décembre » → `12-01`) : le code choisira la prochaine occurrence. "
                "`AAAA-MM-JJ` **uniquement** si l'utilisateur a donné l'année lui-même. "
                "N'invente jamais une année : tu ne sais pas en quelle année on est."
            ),
        },
        "time": {
            "type": "string",
            "description": f"Heure locale HH:MM. Omise si date_mode = in_minutes. "
                           f"Défaut {DEFAULT_TIME} si l'utilisateur n'a pas précisé d'heure.",
        },
    },
    "required": ["title", "date_mode"],
    "additionalProperties": False,
}

MANIFEST = ToolManifest(
    name="create_reminder",
    description=(
        "Programme un rappel pour l'utilisateur : il recevra un message Slack à l'heure dite. "
        "À utiliser dès qu'il demande d'être rappelé, prévenu ou relancé à un moment donné."
    ),
    schema=SCHEMA,
    effect=Effect.WRITE,
    taints_context=False,       # n'introduit aucun contenu extérieur dans le contexte
    reversible=True,            # bouton « annuler » → suppression de la carte
    scope="données kanban de l'utilisateur",
    visibility=True,            # la confirmation apparaît dans le fil, immédiatement
    # 3 par tour : « crée-moi trois rappels » doit fonctionner. 20 par jour : plafond de dégâts
    # d'une boucle qui s'emballerait, sans gêner un usage réel (roadmap §3.5).
    rate_limit=RateLimit(per_turn=3, per_day=20),
    egress=None,
)


def _parse_time(raw: str | None) -> tuple[int, int]:
    if not raw:
        h, m = DEFAULT_TIME.split(":")
        return int(h), int(m)
    try:
        h_s, _, m_s = str(raw).partition(":")
        h, m = int(h_s), int(m_s or 0)
    except ValueError:
        raise ToolError(f"heure illisible : {raw!r} (format attendu HH:MM)")
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ToolError(f"heure hors bornes : {raw!r}")
    return h, m


def resolve_due_at(args: dict, now: datetime) -> datetime:
    """Résout les composants du modèle en un datetime aware, dans le fuseau de l'utilisateur.

    `now` est **passé en argument** : c'est ce qui rend cette fonction testable sans horloge, et
    ce qui garantit que le modèle ne fournit jamais la référence temporelle.
    """
    mode = args.get("date_mode")

    if mode == "in_minutes":
        minutes = args.get("in_minutes")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ToolError("`in_minutes` doit être un entier positif")
        return now + timedelta(minutes=minutes)

    h, m = _parse_time(args.get("time"))

    if mode == "offset_days":
        days = args.get("offset_days")
        if not isinstance(days, int) or days < 0:
            raise ToolError("`offset_days` doit être un entier positif ou nul")
        target = (now + timedelta(days=days)).replace(hour=h, minute=m, second=0, microsecond=0)

    elif mode == "weekday":
        wanted = _JOURS.get(str(args.get("weekday") or "").lower())
        if wanted is None:
            raise ToolError(f"jour de la semaine inconnu : {args.get('weekday')!r}")
        delta = (wanted - now.weekday()) % 7
        candidate = (now + timedelta(days=delta)).replace(hour=h, minute=m, second=0, microsecond=0)
        # « mardi » un mardi à 15h alors qu'il est 18h désigne le mardi suivant, pas une heure
        # déjà passée : la prochaine occurrence est toujours dans le futur.
        if candidate <= now:
            candidate += timedelta(days=7)
        target = candidate

    elif mode == "absolute":
        raw = str(args.get("date") or "").strip()
        try:
            d = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            # Pas d'année : c'est le cas nominal quand l'utilisateur n'en a pas donné. Le code
            # choisit la prochaine occurrence — la même arithmétique que `weekday`, appliquée à
            # l'année au lieu de la semaine. Le modèle n'a jamais à savoir en quelle année on est.
            try:
                # Ancré sur une année bissextile : sans quoi `02-29` serait « illisible », ce qui
                # est faux — c'est une date valide une année sur quatre.
                sans_annee = datetime.strptime(f"2024-{raw}", "%Y-%m-%d")
            except ValueError:
                raise ToolError(
                    f"date illisible : {raw!r} (attendu `MM-JJ`, ou `AAAA-MM-JJ` si "
                    f"l'utilisateur a donné l'année)"
                )
            # La prochaine occurrence réelle. La boucle, plutôt qu'un `+1`, gère le 29 février :
            # la prochaine occurrence peut être à trois ans, et `replace(year=…)` lèverait sur
            # une année commune.
            for annee in range(now.year, now.year + 9):
                try:
                    candidate = sans_annee.replace(
                        year=annee, hour=h, minute=m, second=0, microsecond=0, tzinfo=TZ
                    )
                except ValueError:
                    continue  # 29 février d'une année commune
                if candidate > now:
                    return candidate
            raise ToolError(f"aucune occurrence à venir pour {raw!r}")
        target = d.replace(hour=h, minute=m, tzinfo=TZ)

    else:
        raise ToolError(f"`date_mode` inconnu : {mode!r}")

    return target


async def _resolve(args: dict, ctx: ToolContext) -> PreparedCall:
    title = str(args.get("title") or "").strip()
    if not title:
        raise ToolError("titre vide : précise ce qu'il faut rappeler")
    if len(title) > TITLE_MAX:
        # Erreur explicite plutôt que troncature : tronquer amputerait la charge utile en silence,
        # alors que l'erreur indique au modèle le champ où elle doit aller.
        raise ToolError(
            f"titre trop long ({len(title)} caractères, {TITLE_MAX} maximum). Garde un titre "
            f"d'action court et mets la liste, les articles ou les références dans `details`."
        )

    details = str(args.get("details") or "").strip()
    if len(details) > DETAILS_MAX:
        details = details[:DETAILS_MAX].rstrip() + "…"

    now = now_local()
    due_at = resolve_due_at(args, now)

    # Bornes vérifiées **après** résolution, sur la valeur réelle. Une date passée ou aberrante
    # est refusée avec un message clair, jamais corrigée en silence : c'est en la voyant refusée
    # que l'utilisateur comprend que sa formulation était ambiguë.
    if due_at < now - PAST_TOLERANCE:
        raise ToolError(
            f"la date résolue est dans le passé ({format_local(due_at)}). "
            f"Demande à l'utilisateur de préciser le jour et l'heure."
        )
    if due_at > now + HORIZON_MAX:
        raise ToolError(
            f"la date résolue est trop lointaine ({format_local(due_at)}) — "
            f"probablement une erreur d'interprétation."
        )

    # `details` figure dans le résumé : une confirmation préalable doit montrer **tout** ce qui
    # sera écrit, sinon elle fait approuver autre chose que ce qui part en base.
    summary = f"*{title}* — {format_local(due_at)}"
    if details:
        summary += f"\n{details}"

    return PreparedCall(
        resolved={"title": title, "details": details, "due_at": due_at.isoformat()},
        summary=summary,
    )


async def _target_column() -> str:
    """Colonne de destination : `Rappels` sur le board par défaut, créée à la volée.

    Le board par défaut est créé s'il n'en existe aucun — sinon un premier rappel échouerait sur
    une base neuve, ce qui n'est pas une erreur que l'utilisateur peut comprendre depuis Slack.
    """
    board = await kanban_svc.get_default_board()
    if not board:
        boards = await kanban_svc.list_boards()
        board = boards[0] if boards else await kanban_svc.create_board(
            DEFAULT_BOARD_NAME, is_default=True
        )
    col = await kanban_svc.ensure_column(str(board["id"]), REMINDER_COLUMN)
    return str(col["id"])


def build_posterior_blocks(
    card_id: str, title: str, due_at: datetime, details: str | None = None
) -> list[dict]:
    """Confirmation *a posteriori* : le rappel existe déjà, on montre quoi et quand.

    Régime réservé au contexte propre (roadmap §3.3) : la portée est d'un message, l'erreur est
    visible immédiatement, et l'annulation tient en un clic — profil de risque sans commune
    mesure avec un diff de doc système, qui reste lui en approbation *préalable*.
    """
    corps = f"\n\n{details.strip()}" if (details or "").strip() else ""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":alarm_clock: Rappel programmé : *{title}*\n"
                        f"{format_local(due_at)}{corps}",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "action_id": "agent_reminder_edit",
                    "text": {"type": "plain_text", "text": "Éditer"},
                    "value": card_id,
                },
                {
                    "type": "button",
                    "action_id": "agent_reminder_cancel",
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Annuler"},
                    "value": card_id,
                },
            ],
        },
    ]


async def _execute(resolved: dict, ctx: ToolContext) -> ToolResult:
    """Écrit la carte. Reçoit le payload **résolu** — jamais les arguments bruts du modèle.

    Cette fonction est appelée soit directement (contexte propre), soit depuis le clic
    « Confirmer » (contexte tainté) : dans les deux cas avec le payload figé à la résolution,
    donc avec exactement la date qui a été affichée à l'utilisateur.
    """
    title = resolved["title"]
    # `.get` et non `[...]` : une confirmation figée avant ce déploiement porte un payload résolu
    # sans `details`, et un rappel en attente ne doit pas mourir d'un `KeyError` au clic.
    details = (resolved.get("details") or "").strip()
    due_at = datetime.fromisoformat(resolved["due_at"])

    column_id = await _target_column()
    card = await kanban_svc.create_card(
        column_id, title, description=details or None, due_date=due_at
    )
    card_id = str(card["id"])

    logger.info(
        "create_reminder: carte %s créée — %r (%d car. de détail) à %s",
        card_id, title, len(details), due_at.isoformat(),
    )

    return ToolResult(
        payload={
            "status": "créé",
            "card_id": card_id,
            "title": title,
            "details": details,
            "due_at_local": format_local(due_at),
            "note": "Le rappel est programmé et confirmé à l'utilisateur dans le fil, "
                    "avec un bouton pour l'annuler ou l'éditer. Ne répète pas la date, "
                    "contente-toi d'un acquittement bref.",
        },
        slack_blocks=build_posterior_blocks(card_id, title, due_at, details),
        slack_text=f"Rappel programmé : {title} — {format_local(due_at)}",
    )


SPEC = ToolSpec(manifest=MANIFEST, execute=_execute, resolve=_resolve)
