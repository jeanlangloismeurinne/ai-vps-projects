/**
 * LA DÉCISION DU COMITÉ sur une question — niveau 3 du parcours (chantier V3, lot 6 maillon 3,
 * spec §8.2). Deux gestes, tracés au procès-verbal :
 *   · ACCEPTER une réponse telle qu'elle est, avec sa faiblesse — signé et motivé (arbitrage n°1) ;
 *   · RENVOYER la question en recherche, avec une consigne — le même canal que le contrôle qualité.
 *
 * ⚠️ CHAQUE CHAMP DU PROCÈS-VERBAL A SON PIXEL : tout champ terminal de `DecisionComite` est rendu
 * dans un élément `data-pv="<chemin>"`, et l'état servi d'une acceptation dans `data-pv="acceptation.*"`.
 * `checks/check_comite.py` §6 exige la bijection. Un PV dont une colonne n'est jamais affichée ne se
 * relit pas six mois plus tard.
 *
 * Aucune règle ici : l'état d'une acceptation (en vigueur / tombée) est calculé par le serveur à
 * chaque lecture. Le POST rend le niveau 3 RECALCULÉ, que la page affiche tel quel.
 */
import { useEffect, useState } from 'react'
import { Card, CardHeader, CardBody, Badge } from './index'
import { API, ETATS_ACCEPTATION } from './parcours'

const CLE_AUTEUR = 'comite.auteur'

function lireAuteur() {
  try { return window.localStorage.getItem(CLE_AUTEUR) || '' } catch { return '' }
}
function retenirAuteur(v) {
  try { window.localStorage.setItem(CLE_AUTEUR, v) } catch { /* navigation privée */ }
}

function date(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })
}

const ACTIONS = {
  acquitter: { label: 'Acceptée telle quelle', variant: 'emerald' },
  renvoyer: { label: 'Renvoyée en recherche', variant: 'sky' },
}

// Une ligne du procès-verbal — tous ses champs, toujours rendus (un « — » dit l'absence).
function LignePV({ dcs }) {
  const act = ACTIONS[dcs.action] || { label: dcs.action, variant: 'gray' }
  return (
    <li className="rounded-lg border border-gray-800 px-3 py-2 space-y-1 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span data-pv="action"><Badge variant={act.variant}>{act.label}</Badge></span>
        <span className="text-gray-300">par <span data-pv="auteur">{dcs.auteur}</span></span>
        <span className="text-gray-500">le <span data-pv="decide_le">{date(dcs.decide_le)}</span></span>
        <span className="text-gray-600 font-mono">PV #<span data-pv="id">{dcs.id}</span></span>
      </div>
      <p className="text-gray-200 whitespace-pre-wrap" data-pv="motif">{dcs.motif}</p>
      <p className="text-gray-500">
        Dossier lu : <span data-pv="ticker_id">{dcs.ticker_id}</span> ·{' '}
        <span data-pv="framework_id">{dcs.framework_id}</span>{' '}
        <span data-pv="framework_version">{dcs.framework_version}</span> ·{' '}
        <span data-pv="question_id">{dcs.question_id}</span> · réponse{' '}
        <span data-pv="answer_id">{dcs.answer_id ? `#${dcs.answer_id}` : '— (aucune réponse au dossier)'}</span>
      </p>
      <p className="text-gray-500">
        Recherche ouverte : <span data-pv="mandat_id">{dcs.mandat_id ? `mandat #${dcs.mandat_id}` : '—'}</span>
        {' '}· recherche arrêtée : <span data-pv="mandat_remplace_id">{dcs.mandat_remplace_id ? `mandat #${dcs.mandat_remplace_id}` : '—'}</span>
      </p>
      <p className="text-gray-500">
        Dernier fait important connu :{' '}
        <span data-pv="ancre_etat" className="hidden">{dcs.ancre_etat}</span>
        {dcs.ancre_etat === 'none' && 'aucun'}
        {dcs.ancre_etat === 'unavailable' && 'non vérifiable (EDGAR injoignable)'}
        <span data-pv="fait_connu.resume">{dcs.fait_connu?.resume || ''}</span>
        <span className="hidden" data-pv="fait_connu.publie_le">{dcs.fait_connu?.publie_le || ''}</span>
        <span className="hidden" data-pv="fait_connu.accession">{dcs.fait_connu?.accession || ''}</span>
      </p>
    </li>
  )
}

// La position du jour — calculée par le serveur (en vigueur / tombée, et pourquoi).
function Position({ pos }) {
  if (!pos) return <p className="text-sm text-gray-500">Le comité ne s'est pas encore prononcé sur cette question.</p>
  const acc = pos.acceptation
  if (!acc) {
    return (
      <p className="text-sm text-sky-300">
        Renvoyée en recherche par {pos.derniere.auteur} le {date(pos.derniere.decide_le)}.
      </p>
    )
  }
  const e = ETATS_ACCEPTATION[acc.etat] || { label: acc.etat, variant: 'gray' }
  return (
    <div className="space-y-1">
      <span data-pv="acceptation.etat"><Badge variant={e.variant}>{e.label}</Badge></span>
      <p className="text-xs text-gray-400" data-pv="acceptation.motif_etat">{acc.motif_etat}</p>
      <p className="text-xs text-amber-300" data-pv="acceptation.fait_nouveau.resume">{acc.fait_nouveau?.resume || ''}</p>
      <span className="hidden" data-pv="acceptation.fait_nouveau.publie_le">{acc.fait_nouveau?.publie_le || ''}</span>
      <span className="hidden" data-pv="acceptation.fait_nouveau.accession">{acc.fait_nouveau?.accession || ''}</span>
    </div>
  )
}

const champ = 'w-full rounded-md bg-gray-950 border border-gray-700 px-2.5 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:border-emerald-500 focus:outline-none'

export default function RegistreComite({ d, onRecalcule }) {
  const [geste, setGeste] = useState(null)          // 'acquitter' | 'renvoyer' | null
  const [auteur, setAuteur] = useState('')
  const [answerId, setAnswerId] = useState(d.preuves[0]?.answer_id ?? null)
  const [motif, setMotif] = useState('')
  const [mandat, setMandat] = useState('')
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)

  useEffect(() => { setAuteur(lireAuteur()) }, [])

  const pret = auteur.trim() && motif.trim() && (geste === 'acquitter' ? answerId : mandat.trim())

  async function envoyer(e) {
    e.preventDefault()
    if (!pret) return
    setEnvoi(true); setErreur(null)
    const corps = geste === 'acquitter'
      ? { answer_id: answerId, auteur, motif }
      : { auteur, motif, mandat, answer_id: answerId }
    try {
      const r = await fetch(`${API}/v2/tickers/${d.ticker_id}/frameworks/${d.framework_id}/q/${d.question_id}/${geste}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps),
      })
      const j = await r.json()
      if (!r.ok) throw new Error(typeof j.detail === 'string' ? j.detail : `HTTP ${r.status}`)
      retenirAuteur(auteur)
      setGeste(null); setMotif(''); setMandat('')
      onRecalcule(j)
    } catch (e2) {
      setErreur(String(e2.message || e2))
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <div data-testid="decision-comite">
    <Card>
      <CardHeader
        title="Décision du comité"
        subtitle="Chaque décision est inscrite au procès-verbal : qui, quand, sur quelle réponse, et pourquoi."
      />
      <CardBody className="space-y-4">
        <Position pos={d.comite} />

        {!geste && (
          <div className="flex flex-wrap gap-2">
            {d.preuves.length > 0 && (
              <button type="button" onClick={() => setGeste('acquitter')}
                      className="rounded-md border border-emerald-700 px-3 py-1.5 text-sm text-emerald-200 hover:bg-emerald-900/40">
                Accepter la réponse telle quelle
              </button>
            )}
            <button type="button" onClick={() => setGeste('renvoyer')}
                    className="rounded-md border border-sky-700 px-3 py-1.5 text-sm text-sky-200 hover:bg-sky-900/40">
              Renvoyer en recherche
            </button>
          </div>
        )}

        {geste && (
          <form onSubmit={envoyer} className="space-y-3 rounded-lg border border-gray-800 p-3">
            <p className="text-sm text-gray-200">
              {geste === 'acquitter'
                ? "Accepter : le comité prend la réponse avec sa faiblesse. L'acceptation tombera d'elle-même si un fait important est publié ou si l'analyse est refaite."
                : 'Renvoyer : la question repart en recherche avec votre consigne ; elle remplace la recherche en cours.'}
            </p>
            {d.preuves.length > 0 && (
              <label className="block space-y-1">
                <span className="text-xs text-gray-400">{geste === 'acquitter' ? 'Réponse acceptée' : 'Réponse concernée (facultatif)'}</span>
                <select className={champ} value={answerId ?? ''} onChange={e => setAnswerId(e.target.value ? Number(e.target.value) : null)}>
                  {geste === 'renvoyer' && <option value="">— aucune en particulier</option>}
                  {d.preuves.map(pr => (
                    <option key={pr.answer_id} value={pr.answer_id}>
                      #{pr.answer_id} · {pr.answer.analyste} · {pr.answer.statut}{pr.answer.fondation ? ` · rang ${pr.answer.fondation.rang_derive}` : ''}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="block space-y-1">
              <span className="text-xs text-gray-400">Membre du comité</span>
              <input className={champ} value={auteur} onChange={e => setAuteur(e.target.value)} placeholder="Nom de la personne qui décide" maxLength={120} />
            </label>
            <label className="block space-y-1">
              <span className="text-xs text-gray-400">{geste === 'acquitter' ? 'Pourquoi le comité passe outre (obligatoire)' : 'Ce qui ne va pas (obligatoire)'}</span>
              <textarea className={champ} rows={3} value={motif} onChange={e => setMotif(e.target.value)}
                        placeholder={geste === 'acquitter' ? 'Ex. : la marge des pairs manque, mais la thèse repose sur la trésorerie, pas sur la rentabilité.' : 'Ex. : la marge citée date de 2024.'} />
            </label>
            {geste === 'renvoyer' && (
              <label className="block space-y-1">
                <span className="text-xs text-gray-400">Consigne de recherche (obligatoire)</span>
                <textarea className={champ} rows={2} value={mandat} onChange={e => setMandat(e.target.value)}
                          placeholder="Ex. : retrouver la marge brute publiée au 10-Q du T2 2026." />
              </label>
            )}
            {erreur && <p className="text-sm text-red-300">{erreur}</p>}
            <div className="flex gap-2">
              <button type="submit" disabled={!pret || envoi}
                      className="rounded-md bg-emerald-700 px-3 py-1.5 text-sm text-white disabled:opacity-40">
                {envoi ? 'Inscription…' : 'Inscrire au procès-verbal'}
              </button>
              <button type="button" onClick={() => { setGeste(null); setErreur(null) }}
                      className="rounded-md px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200">Annuler</button>
            </div>
          </form>
        )}

        <div className="space-y-2">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Procès-verbal de la question</p>
          {d.registre.length === 0
            ? <p className="text-xs text-gray-600">Aucune décision inscrite.</p>
            : <ul className="space-y-2">{d.registre.map(dcs => <LignePV key={dcs.id} dcs={dcs} />)}</ul>}
        </div>
      </CardBody>
    </Card>
    </div>
  )
}
