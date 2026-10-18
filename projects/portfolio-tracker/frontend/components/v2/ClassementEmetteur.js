/**
 * LE CLASSEMENT DE LA SOCIÉTÉ, en tête du dossier (#139). Il décide de la grille de questions de chaque
 * chapitre. Le système RECOMMANDE de le revoir quand un dépôt annonce un changement de stade (premier
 * produit autorisé, premières ventes) ; le comité RECLASSE ou MAINTIENT — signé, motivé, adossé au dépôt.
 * La recommandation est recalculée à chaque lecture et reste affichée tant que le comité n'a pas tranché.
 * Le POST rend le niveau 1 RECALCULÉ, que la page affiche tel quel.
 */
import { useEffect, useState } from 'react'
import { API } from './parcours'

const CLE_AUTEUR = 'comite.auteur'
const LIBELLES = {
  pre_revenus: 'sans revenus (pré-commerciale)',
  rentable: 'commerciale (vend ses produits)',
  financiere: 'financière (banque, assurance)',
}
const libelle = a => LIBELLES[a] || a.replaceAll('_', ' ')
const jour = iso => new Date(`${iso}T00:00:00`).toLocaleDateString('fr-FR', { dateStyle: 'long' })
const champ = 'w-full rounded-md bg-gray-950 border border-gray-700 px-2.5 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:border-emerald-500 focus:outline-none'

function lireAuteur() {
  try { return window.localStorage.getItem(CLE_AUTEUR) || '' } catch { return '' }
}
function retenirAuteur(v) {
  try { window.localStorage.setItem(CLE_AUTEUR, v) } catch { /* navigation privée */ }
}

export default function ClassementEmetteur({ d, onRecalcule }) {
  const c = d.classement
  const r = d.reclassement_recommande
  const [geste, setGeste] = useState(null)          // 'reclasser' | 'maintenir' | null
  const [auteur, setAuteur] = useState('')
  const [motif, setMotif] = useState('')
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)
  useEffect(() => { setAuteur(lireAuteur()) }, [])

  if (!c) return null
  const pret = auteur.trim() && motif.trim()

  async function envoyer(e) {
    e.preventDefault()
    if (!pret || !r) return
    setEnvoi(true); setErreur(null)
    const corps = { archetype: geste === 'reclasser' ? r.vers : r.de, accession: r.accession, auteur, motif }
    try {
      const rep = await fetch(`${API}/v2/tickers/${d.ticker_id}/classement`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps),
      })
      const j = await rep.json()
      if (!rep.ok) throw new Error(typeof j.detail === 'string' ? j.detail : `HTTP ${rep.status}`)
      retenirAuteur(auteur)
      setGeste(null); setMotif('')
      onRecalcule(j)
    } catch (e2) {
      setErreur(String(e2.message || e2))
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/40 px-4 py-3 space-y-2" data-testid="classement-emetteur">
      <p className="text-sm text-gray-200">
        Classement de la société : <span className="font-semibold">{libelle(c.archetype)}</span>
        <span className="text-gray-500"> · depuis le {jour(c.depuis)}</span>
      </p>
      <p className="text-xs text-gray-400">{c.motif}</p>
      {c.auteur && (
        <p className="text-xs text-gray-500">
          Décidé par {c.auteur} au vu du dépôt {c.declencheur_accession} — pièce #{c.piece_id}, jointe à tous les chapitres.
        </p>
      )}

      {r && (
        <div className="rounded-lg border border-sky-800 bg-sky-950/30 px-3 py-2.5 space-y-2" data-testid="reclassement-recommande">
          <p className="text-sm font-semibold text-sky-200">
            Recommandation : reclasser la société « {libelle(r.vers)} »
          </p>
          <p className="text-xs text-sky-300/80">
            Le dépôt du {jour(r.fait_du)} ({r.accession}) annonce un changement de stade
            {r.type_id !== 'changement_de_stade' && <> ({r.type_id.replaceAll('_', ' ')})</>} ; la grille
            « {libelle(r.de)} » laisse alors sans objet des questions qui en ont un. Le comité reclasse ou
            maintient ; tant qu'il n'a pas tranché, le dossier ne peut pas être déclaré complet.
          </p>
          <p className="text-xs text-gray-400 italic">{r.resume}</p>

          {!geste && (
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => setGeste('reclasser')}
                      className="rounded-md border border-sky-600 px-3 py-1.5 text-sm text-sky-100 hover:bg-sky-900/40">
                Reclasser « {libelle(r.vers)} »
              </button>
              <button type="button" onClick={() => setGeste('maintenir')}
                      className="rounded-md border border-gray-600 px-3 py-1.5 text-sm text-gray-200 hover:bg-gray-800/60">
                Maintenir « {libelle(r.de)} »
              </button>
            </div>
          )}

          {geste && (
            <form onSubmit={envoyer} className="space-y-3 rounded-lg border border-gray-800 p-3">
              <p className="text-sm text-gray-200">
                {geste === 'reclasser'
                  ? `Reclasser : la grille « ${libelle(r.vers)} » s'applique dès aujourd'hui à tous les chapitres. La lecture du dépôt devient la pièce du classement et rejoint chaque dossier : l'analyste pourra s'y appuyer pour dire qu'une information n'existe pas encore.`
                  : `Maintenir : la grille reste « ${libelle(r.de)} ». La recommandation se ferme pour ce dépôt ; un dépôt ultérieur du même ordre la rouvrira.`}
              </p>
              <label className="block space-y-1">
                <span className="text-xs text-gray-400">Membre du comité</span>
                <input className={champ} value={auteur} onChange={e => setAuteur(e.target.value)} placeholder="Nom de la personne qui décide" maxLength={120} />
              </label>
              <label className="block space-y-1">
                <span className="text-xs text-gray-400">Pourquoi (obligatoire)</span>
                <textarea className={champ} rows={3} value={motif} onChange={e => setMotif(e.target.value)}
                          placeholder={geste === 'reclasser' ? 'Ex. : premier produit approuvé le 26/08, lancement en cours — les ventes vont structurer le dossier.' : 'Ex. : approbation conditionnelle, aucune vente attendue avant deux ans.'} />
              </label>
              {erreur && <p className="text-sm text-red-300">{erreur}</p>}
              <div className="flex gap-2">
                <button type="submit" disabled={!pret || envoi}
                        className="rounded-md bg-emerald-700 px-3 py-1.5 text-sm text-white disabled:opacity-40">
                  {envoi ? 'Inscription…' : 'Inscrire la décision'}
                </button>
                <button type="button" onClick={() => { setGeste(null); setErreur(null) }}
                        className="rounded-md px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200">Annuler</button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  )
}
