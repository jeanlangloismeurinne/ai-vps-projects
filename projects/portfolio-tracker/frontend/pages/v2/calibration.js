import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Card, CardHeader, CardBody,
  Badge, KeyValue, Section, Dl,
  EmptyState, ErrorState,
} from '../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

// ── Utilitaires ───────────────────────────────────────────────────────────────

function fmtPct(val) {
  if (val == null) return '—'
  return `${Number(val).toFixed(2)} %`
}

function fmtNum(val, decimals = 2) {
  if (val == null) return '—'
  const sign = val > 0 ? '+' : ''
  return `${sign}${Number(val).toFixed(decimals)}`
}

// ── Dérivation de la famille d'une métrique ───────────────────────────────────
// Règle : préfixe avant ":" quand il y en a un, sinon nom entier.
// Familles connues à titre d'exemple : iv, kpi, risque. On ne code pas en dur la liste.
function getFamille(metric) {
  if (!metric) return 'autre'
  const colonIdx = metric.indexOf(':')
  if (colonIdx !== -1) return metric.substring(0, colonIdx)
  // Pas de colon : on regroupe par préfixe commun (iv_low/iv_base/iv_high → iv)
  const underscore = metric.indexOf('_')
  if (underscore !== -1) return metric.substring(0, underscore)
  return metric
}

function getFamilleLabel(famille) {
  const labels = {
    iv:        'Valeur intrinsèque (fourchette IV)',
    kpi:       "KPI d'hypothèse",
    risque:    'Probabilité de risque (hypothèse)',
    rendement: 'Rendement',
  }
  return labels[famille] || famille
}

// ── Ligne métrique ────────────────────────────────────────────────────────────
function MetriqueRow({ m, attenuer }) {
  const attenueClass = attenuer ? 'opacity-50' : ''

  // Couleur de l'écart moyen (signé) : positif = surestimation, négatif = sous-estimation
  // Le signe dit le SENS du biais ; l'absolu dit l'amplitude.
  const biaisSign = m.ecart_moyen > 0 ? 'text-amber-400' : m.ecart_moyen < 0 ? 'text-sky-400' : 'text-gray-400'
  const biaisRelSign = m.biais_relatif_pct > 0 ? 'text-amber-400' : m.biais_relatif_pct < 0 ? 'text-sky-400' : 'text-gray-400'

  return (
    <tr className={`border-t border-gray-800 ${attenueClass}`}>
      <td className="py-2 px-3 text-xs font-mono text-gray-300">{m.metric ?? '—'}</td>
      <td className="py-2 px-3 text-xs text-gray-400 text-center">{m.n ?? '—'}</td>
      <td className={`py-2 px-3 text-xs text-center ${biaisSign}`}>
        {m.ecart_moyen != null ? fmtNum(m.ecart_moyen) : '—'}
      </td>
      <td className="py-2 px-3 text-xs text-gray-400 text-center">
        {m.ecart_absolu_moyen != null ? fmtNum(m.ecart_absolu_moyen) : '—'}
      </td>
      <td className={`py-2 px-3 text-xs text-center ${biaisRelSign}`}>
        {m.biais_relatif_pct != null ? fmtPct(m.biais_relatif_pct) : '—'}
      </td>
    </tr>
  )
}

// ── Groupe de métriques par famille ──────────────────────────────────────────
function FamilleGroup({ famille, metriques, attenuer }) {
  return (
    <div className="space-y-1">
      <h4 className={`text-xs font-semibold uppercase tracking-wide mb-1 ${attenuer ? 'text-gray-600 opacity-50' : 'text-gray-400'}`}>
        {getFamilleLabel(famille)}
      </h4>
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] text-gray-600 uppercase tracking-wide">
              <th className="py-2 px-3 font-medium">Métrique</th>
              <th className="py-2 px-3 font-medium text-center">n</th>
              <th className="py-2 px-3 font-medium text-center">
                Écart moyen
                <span className="block font-normal normal-case tracking-normal text-gray-700">
                  (signé — sens du biais)
                </span>
              </th>
              <th className="py-2 px-3 font-medium text-center">
                Écart absolu moyen
                <span className="block font-normal normal-case tracking-normal text-gray-700">
                  (amplitude — sans annulation)
                </span>
              </th>
              <th className="py-2 px-3 font-medium text-center">Biais relatif %</th>
            </tr>
          </thead>
          <tbody>
            {metriques.map((m, i) => (
              <MetriqueRow key={m.metric || i} m={m} attenuer={attenuer} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────
export default function CalibrationPage() {
  const [summary, setSummary] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/v2/calibration/summary`)
      .then(r => {
        if (r.status === 404) return null
        if (!r.ok) return r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`))
        return r.json()
      })
      .then(d => { setSummary(d); setLoading(false) })
      .catch(e => { setErr(String(e)); setLoading(false) })
  }, [])

  // ── Chargement / erreur ───────────────────────────────────────────────────
  if (loading) return (
    <div className="py-12 text-center text-sm text-gray-500">Chargement…</div>
  )

  if (err) return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link href="/v2/theses" className="hover:text-gray-300">Thèses V2</Link>
        <span>›</span>
        <span className="text-gray-300">Calibration</span>
      </div>
      <ErrorState detail={err} />
    </div>
  )

  // 404 ou summary null → EmptyState
  if (!summary || summary.theses_calibrees === 0 || !Array.isArray(summary.metriques) || summary.metriques.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Link href="/v2/theses" className="hover:text-gray-300">Thèses V2</Link>
          <span>›</span>
          <span className="text-gray-300">Registre de calibration</span>
        </div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Registre de calibration</h1>
          <Badge variant="gray">A5</Badge>
        </div>
        <EmptyState
          title="Aucune thèse calibrée"
          description="Le registre se remplit au post-mortem de chaque thèse soldée. Il n'y a rien à afficher tant qu'aucune position n'a été intégralement clôturée et analysée."
        />
      </div>
    )
  }

  // ── Données disponibles ───────────────────────────────────────────────────
  const lisible = summary.lisible
  const thesesCalibrees = summary.theses_calibrees
  const metriques = summary.metriques

  // Trouver le n minimum parmi toutes les métriques (pour le bandeau)
  const nMin = metriques.reduce((min, m) => (m.n != null && m.n < min ? m.n : min), Infinity)
  const nMinDisplay = isFinite(nMin) ? nMin : '—'

  // Regrouper les métriques par famille
  const groupes = {}
  for (const m of metriques) {
    const f = getFamille(m.metric)
    if (!groupes[f]) groupes[f] = []
    groupes[f].push(m)
  }
  const familleKeys = Object.keys(groupes)

  return (
    <div className="space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link href="/v2/theses" className="hover:text-gray-300">Thèses V2</Link>
        <span>›</span>
        <span className="text-gray-300">Registre de calibration</span>
      </div>

      {/* Titre */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-white">Registre de calibration</h1>
        <Badge variant="gray">A5</Badge>
        <Badge variant={lisible ? 'emerald' : 'amber'}>
          {lisible ? 'Lisible' : 'Recul insuffisant'}
        </Badge>
      </div>

      {/* Bandeau de lisibilité — arbitrage 6 */}
      {!lisible ? (
        <div className="rounded-xl border border-amber-700/50 bg-amber-950/20 px-4 py-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-amber-400 text-base">⚠</span>
            <p className="text-sm font-semibold text-amber-300">Recul insuffisant pour conclure</p>
          </div>
          <p className="text-xs text-amber-200/70">
            Le registre ne couvre que{' '}
            <span className="font-semibold text-amber-300">{thesesCalibrees}</span>{' '}
            thèse{thesesCalibrees > 1 ? 's' : ''} calibrée{thesesCalibrees > 1 ? 's' : ''}, avec
            un n minimum de{' '}
            <span className="font-semibold text-amber-300">{nMinDisplay}</span>{' '}
            observations par métrique.
            Les chiffres ci-dessous sont affichés à titre indicatif uniquement.
          </p>
          <p className="text-xs text-amber-600 border-t border-amber-800/40 pt-2">
            Un <code className="text-[10px] bg-amber-950/40 px-1 rounded">biais_relatif_pct</code> à
            n=1 n'est pas un biais établi — c'est un écart sur un seul cas.
            Toute conclusion tirée de ces données serait prématurée.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-800 bg-gray-900/30 px-4 py-3">
          <p className="text-xs text-gray-400">
            Registre lisible —{' '}
            <span className="font-medium text-gray-200">{thesesCalibrees}</span>{' '}
            thèse{thesesCalibrees > 1 ? 's' : ''} calibrée{thesesCalibrees > 1 ? 's' : ''}.
          </p>
        </div>
      )}

      {/* Rappel important */}
      <div className="rounded-lg border border-gray-800 bg-gray-900/30 px-4 py-3">
        <p className="text-xs text-gray-500">
          <span className="font-medium text-gray-400">Registre fait foi.</span>{' '}
          Les valeurs <code className="text-[10px] bg-gray-800 px-1 rounded">predite</code> du
          registre sont celles <strong className="text-gray-400">figées au validate</strong> — elles
          représentent la conviction initiale, non l'opinion réactualisée par les revues de suivi.
          C'est contre ces prévisions figées que les réalisations sont mesurées.
        </p>
      </div>

      {/* Explication des deux colonnes d'écart */}
      <Card>
        <CardHeader title="Lire les colonnes d'écart" subtitle="Deux mesures complémentaires, jamais fusionnées" />
        <CardBody className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-3 space-y-1">
              <div className="text-xs font-semibold text-gray-300">Écart moyen (signé)</div>
              <p className="text-xs text-gray-500">
                Indique le <strong className="text-gray-400">sens du biais</strong> : une valeur positive
                signifie que les prévisions ont en moyenne <em>surestimé</em> la réalité ; une valeur
                négative qu'elles l'ont <em>sous-estimée</em>. Les erreurs opposées s'annulent — ce
                chiffre mesure la <em>direction</em> systématique.
              </p>
            </div>
            <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-3 space-y-1">
              <div className="text-xs font-semibold text-gray-300">Écart absolu moyen</div>
              <p className="text-xs text-gray-500">
                Indique l'<strong className="text-gray-400">amplitude de l'erreur</strong> sans tenir
                compte du sens : une surestimation de 5 et une sous-estimation de 5 donnent un écart
                moyen de 0 mais un écart absolu moyen de 5. C'est la mesure de la <em>précision</em>
                brute, quelle que soit la direction.
              </p>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Tableau des métriques regroupées */}
      <Section title={`Métriques (${metriques.length})`}>
        <div className={`space-y-6 ${!lisible ? 'opacity-70' : ''}`}>
          {familleKeys.map(famille => (
            <FamilleGroup
              key={famille}
              famille={famille}
              metriques={groupes[famille]}
              attenuer={!lisible}
            />
          ))}
        </div>
      </Section>
    </div>
  )
}
