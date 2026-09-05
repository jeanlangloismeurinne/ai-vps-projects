# DECISIONS.md — faits durables, réutilisables d'un projet à l'autre

> Gotchas vérifiés, chacun avec **une** mesure en preuve. Versionné, greppable, jamais
> auto-chargé. Le récit reste dans les `00-REPRISE-ARCHIVE.md` ; ici, seulement ce qui
> changerait ce qu'un agent fait sur un autre fichier ou un autre projet.
> Conventions (ce qu'on fait) → `CLAUDE.md`. Gotchas (ce qui pique) → ici.

---

## #1 — FastAPI : une valeur de `Form` vide est traitée comme un champ ABSENT (422)

Un `<option value="">` dans un formulaire posté vers une route déclarant `champ: str = Form(...)`
renvoie **422**, pas une chaîne vide : FastAPI assimile la valeur vide à un champ manquant.

**Mesuré** (Hub, `app/roadmap.py`, 2026-09-05) : la même requête de sauvegarde renvoie **422 avec
`status=`** et **303 avec `status=__inchange__`**, corps identique par ailleurs. L'utilisateur
aurait perdu la sauvegarde entière en choisissant l'option « inchangé » du sélecteur.

**Conséquence** : pour une option « ne rien changer », utiliser un **sentinel non vide**
(`__inchange__`) — et non `value=""` — ou déclarer le champ `Form(default=…)`. Vaut pour toutes
les apps FastAPI du repo qui ont des formulaires (hub, assistant-ia, bank-review, ev-prices).

⚠️ Ce défaut est **invisible au check statique** : il ne se voit qu'en postant réellement le
formulaire. Un test qui n'observe que l'état du fichier après coup le lit comme un succès — le
fichier est bien intact, mais parce que la requête a été rejetée en entier.
