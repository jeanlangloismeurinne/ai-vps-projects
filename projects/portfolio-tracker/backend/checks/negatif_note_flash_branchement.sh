#!/usr/bin/env bash
# TEST NÉGATIF de `check_note_flash_branchement.py` — une mutation par DÉCISION du branchement de la note
# flash au flux (arbitrage 2026-09-26, option c), chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ +
# bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_note_flash_branchement.sh
#
# Ce que la note elle-même décide (pont, types, relecture) est éprouvé par `negatif_note_flash.sh`.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_note_flash_branchement.py"
NF="app/agents/v2/note_flash.py"
mutations=(
# §1 — recenser ne coûte rien, la limite, l'arriéré
"$NF¦    if not ecrire and not apercu:¦    if False:¦recensement : 0 téléchargement"
"$NF¦    a_lire = tous[:max(limite, 0)]¦    a_lire = tous¦la limite du passage s'applique"
"$NF¦        return max(self.en_attente - len(self.depots), 0)¦        return 0¦l'arriéré au-delà de la limite est COMPTÉ"
# §2 — un dépôt ne tait pas les suivants
"$NF¦        except Exception as ex:  # noqa: BLE001 — une panne d'un dépôt ne tait jamais les suivants¦        except KeyError as ex:  # noqa¦le passage a laissé s'échapper RuntimeError"
"$NF¦            red = await asyncio.wait_for(¦            red = await (lambda coro, _borne: coro)(¦une lecture qui ne rend pas la main est bornée"
"$NF¦        except asyncpg.UniqueViolationError:¦        except KeyError:¦doublon concurrent"
"$NF¦            lecture.cout_usd += sum(r.cost_usd for r in red.runs)¦            pass¦le coût des lectures abouties est compté"
# §4 — le matin, réglage coupé
"$NF¦                    conn, t, ecrire=auto, depuis=today - FENETRE, fichier=fichier)¦                    conn, t, ecrire=True, depuis=today - FENETRE, fichier=fichier)¦réglage coupé : AUCUN appel modèle"
"$NF¦             if d.note_id is None and d.event.filing_date and d.event.filing_date >= hier]¦             if d.note_id is None]¦arriéré seul (rien de neuf depuis la veille)"
"$NF¦        except Exception as ex:  # noqa: BLE001 — un titre en panne n'arrête pas les suivants¦        except KeyError as ex:  # noqa¦le passage du matin a laissé s'échapper"
"$NF¦        \"SELECT id FROM tickers WHERE status IN ('portfolio', 'watchlist') ORDER BY id\")¦        \"SELECT id FROM tickers WHERE status IN ('portfolio') ORDER BY id\")¦détenus ET sous surveillance"
# §5 — le matin, réglage ouvert
"$NF¦        refus = [(l, d) for l in lectures for d in l.refus]¦        refus = []¦le gérant reçoit types, passage et refus"
# §6 — les appelants
"tools/executer_chaine.py¦            lecture = await lire_les_depots_en_attente(conn, ticker_id, ecrire=True, fichier=fichier)¦            lecture = None¦la chaîne lit les dépôts AVANT"
"app/agents/v2/bouclage.py¦            sur_lecture(await lire_les_depots_en_attente(conn, ticker_id, ecrire=True, fichier=fichier))¦            pass¦le bouclage lit AVANT le dossier"
"app/main.py¦        _notes_flash_matin,¦        _daily_check_v2,¦le job du matin est planifié"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
