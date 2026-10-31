import { useEffect, useMemo, useState } from 'react'
import ProbaChart, { Legend } from './ProbaChart'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'
const HORIZONS = [{ v: 5, l: '5 ans' }, { v: 10, l: '10 ans' }, { v: 40, l: 'Max' }]
const pc = (v) => (v === null || v === undefined ? '—' : `${Math.round(v * 100)} %`)

export function useProba(ticker, years) {
  const [res, setRes] = useState({ key: null, data: null, err: null })
  const key = `${ticker}:${years}`
  useEffect(() => {
    let live = true
    fetch(`${API}/nasdaq/proba/${encodeURIComponent(ticker)}?years=${years}`)
      .then(r => (r.ok ? r.json() : r.json().then(j => Promise.reject(new Error(j.detail || `HTTP ${r.status}`)))))
      .then(j => live && setRes({ key, data: j, err: null }))
      .catch(e => live && setRes({ key, data: null, err: String(e.message || e) }))
    return () => { live = false }
  }, [key]) // eslint-disable-line
  return res.key === key ? res : { key, data: null, err: null }
}

export function Explain({ calib, short = false }) {
  const c = calib?.calib
  return (
    <div className="text-xs text-gray-400 space-y-2 leading-relaxed">
      <p>
        <b className="text-gray-200">Comment lire cette courbe.</b> À chaque fin de mois, on estime la chance que le cours dépasse son plus haut historique
        dans les 12 mois qui suivent. L'aire sous la courbe est <span className="text-green-400">verte</span> si, 12 mois plus tard, un nouveau plus haut a bien été atteint,
        <span className="text-red-400"> rouge</span> sinon, <span className="text-gray-300">grise</span> tant que les 12 mois ne sont pas écoulés.
        « La prédiction s'est réalisée » signifie donc : le titre a effectivement atteint un nouveau plus haut, pas que la barre des X % a été franchie.
      </p>
      {!short && (
        <>
          <p>
            <b className="text-gray-200">Comment c'est calculé.</b> Une régression logistique unique pour tous les titres, avec six informations connues à la date :
            distance au plus haut, temps écoulé depuis ce plus haut, évolution sur 6 et 12 mois, volatilité, ancienneté de la cotation.
            La distance au plus haut pèse de loin le plus ; l'ancienneté du cours n'ajoute presque rien une fois la distance connue.
          </p>
          <p>
            <b className="text-gray-200">Uniquement le passé.</b> Le modèle utilisé pour l'année Y est appris sur des observations dont les 12 mois de résultat étaient
            déjà écoulés au 1ᵉʳ janvier de Y : il ne « voit » jamais l'avenir de la date qu'il note. Les années avant le premier modèle n'ont pas de courbe.
            Réserves : seules les entreprises encore cotées et de plus de 50 Md$ sont suivies (biais du survivant : les chiffres sont flatteurs) ;
            le nettoyage des cotations aberrantes regarde la séance suivante (fuite négligeable).
          </p>
          {c && (
            <p>
              <b className="text-gray-200">Fiabilité mesurée hors échantillon</b> ({c.n.toLocaleString('fr-FR')} observations, {c.n_tickers} titres) : taux de base {pc(c.base_rate)},
              pouvoir de classement (AUC) {c.auc}.{' '}
              {c.thresholds?.length ? 'Quand p ≥ ' + c.thresholds.map(t => `${Math.round(t.s * 100)} % → ${pc(t.hit)} de réussite`).filter((_, i) => i % 2 === 1).join(' ; ') + '.' : ''}
            </p>
          )}
        </>
      )}
    </div>
  )
}

export default function ProbaPanel({ ticker }) {
  const [years, setYears] = useState(10)
  const [thr, setThr] = useState(0.5)
  const [calib, setCalib] = useState(null)
  const { data, err } = useProba(ticker, years)
  useEffect(() => { fetch(`${API}/nasdaq/proba-calib`).then(r => r.json()).then(setCalib).catch(() => {}) }, [])
  const stats = useMemo(() => {
    if (!data) return null
    let n = 0, hit = 0, all = 0, allHit = 0
    data.p.forEach((p, i) => {
      if (data.o[i] === null) return
      all++; allHit += data.o[i]
      if (p >= thr) { n++; hit += data.o[i] }
    })
    return { n, hit, all, allHit }
  }, [data, thr])
  const last = data ? data.p[data.p.length - 1] : null
  return (
    <div className="mt-5 pt-4 border-t border-gray-800">
      <div className="flex items-center gap-3 flex-wrap mb-2">
        <h4 className="text-sm font-semibold text-white">Probabilité de nouveau plus haut à 12 mois</h4>
        {last !== null && <span className="text-sm text-sky-300">aujourd'hui : {pc(last)}</span>}
        <div className="flex rounded border border-gray-700 overflow-hidden ml-auto">
          {HORIZONS.map(o => (
            <button key={o.v} onClick={() => setYears(o.v)}
              className={`px-2.5 py-1 text-xs ${years === o.v ? 'bg-sky-900 text-white' : 'text-gray-400 hover:text-white'}`}>{o.l}</button>
          ))}
        </div>
      </div>
      {err && <p className="text-sm text-gray-500">Courbe indisponible ({err}).</p>}
      {!data && !err && <p className="text-sm text-gray-500">Chargement…</p>}
      {data && (
        <>
          <ProbaChart curve={data} thr={thr} />
          <div className="mt-1"><Legend /></div>
          <div className="mt-3 rounded border border-gray-800 bg-gray-950/40 p-3 text-xs text-gray-300">
            <label className="flex items-center gap-3 flex-wrap">
              Seuil d'investissement
              <input type="range" min="10" max="90" step="5" value={Math.round(thr * 100)} onChange={e => setThr(+e.target.value / 100)} />
              <b className="text-sky-300">{Math.round(thr * 100)} %</b>
            </label>
            <p className="mt-1.5">
              Sur cet historique, quand la probabilité était ≥ {Math.round(thr * 100)} % : <b>{stats.n}</b> fins de mois dont les 12 mois sont écoulés,
              nouveau plus haut atteint dans <b className={stats.n && stats.hit / stats.n >= 0.5 ? 'text-green-400' : 'text-red-400'}>{stats.n ? pc(stats.hit / stats.n) : '—'}</b> des cas
              {' '}(tous mois confondus : {stats.all ? pc(stats.allHit / stats.all) : '—'}).
              {stats.n < 12 && stats.n > 0 && ' Échantillon mince : les mois consécutifs se ressemblent, ce n\'est pas un chiffre solide.'}
            </p>
          </div>
        </>
      )}
      <div className="mt-3"><Explain calib={calib} /></div>
    </div>
  )
}
