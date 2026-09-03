import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import {
  Card, CardHeader, CardBody,
  Badge, KeyValue, Section, Dl,
  EmptyState, ErrorState,
} from '../../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

// ── Utilitaires ───────────────────────────────────────────────────────────────

function fmtDatetime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function fmtCost(val) {
  if (val == null) return '— champ absent'
  return `${Number(val).toFixed(4)} $`
}

function fmtPct(val) {
  if (val == null) return '—'
  return `${(Number(val) * 100).toFixed(1)} %`
}

// ── Statut d'une analyse ──────────────────────────────────────────────────────

const STATUS_VARIANT = {
  draft:      'draft',
  final:      'emerald',
  superseded: 'superseded',
}

function StatusBadge({ status }) {
  const labels = { draft: 'Brouillon', final: 'Final', superseded: 'Remplacé' }
  return (
    <Badge variant={STATUS_VARIANT[status] || 'gray'}>
      {labels[status] || status || '—'}
    </Badge>
  )
}

function TypeBadge({ type }) {
  const cfg = {
    bull:      { label: 'Bull', variant: 'emerald' },
    bear:      { label: 'Bear', variant: 'red' },
    synthesis: { label: 'Synthèse', variant: 'sky' },
  }
  const c = cfg[type] || { label: type || '—', variant: 'gray' }
  return <Badge variant={c.variant}>{c.label}</Badge>
}

// ── Colonnes tour ─────────────────────────────────────────────────────────────

/**
 * Une colonne pour bull | bear | synthèse dans la vue 3-colonnes.
 * `analysis` peut être null (colonne manquante pour ce tour).
 */
function AnalysisColumn({ type, analysis, isLinked }) {
  const labels = { bull: 'Bull', bear: 'Bear', synthesis: 'Synthèse' }
  const borders = {
    bull:      'border-emerald-800',
    bear:      'border-red-900',
    synthesis: 'border-sky-900',
  }
  const bg = {
    bull:      'bg-emerald-950/10',
    bear:      'bg-red-950/10',
    synthesis: 'bg-sky-950/10',
  }

  if (!analysis) {
    return (
      <div className={`rounded-xl border border-gray-800 bg-gray-900/30 p-4 flex flex-col gap-2`}>
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          {labels[type] || type}
        </div>
        <p className="text-xs text-gray-600 italic mt-2">
          — Aucune analyse {labels[type]} pour ce tour
        </p>
      </div>
    )
  }

  const superseded = analysis.status === 'superseded'

  return (
    <div className={`rounded-xl border ${borders[type]} ${bg[type]} p-4 flex flex-col gap-3 ${superseded ? 'opacity-60' : ''}`}>
      {/* En-tête colonne */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <TypeBadge type={type} />
          {isLinked && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded bg-sky-900/40 text-sky-400 border border-sky-800"
              title="Cette analyse a alimenté la synthèse (bull_analysis_id / bear_analysis_id)"
            >
              nourrit synthèse
            </span>
          )}
        </div>
        <StatusBadge status={analysis.status} />
      </div>

      {superseded && (
        <div className="rounded-md bg-gray-800/60 border border-gray-700 px-3 py-2">
          <p className="text-xs text-amber-400 font-medium">
            Cette analyse est remplacée (superseded).
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            Elle a été produite puis invalidée lors d'un tour de réfutation.
            L'opinion ci-dessous est périmée — ne pas la lire comme courante.
          </p>
        </div>
      )}

      {/* Méta */}
      <Dl cols={2}>
        <KeyValue label="ID" value={<span className="font-mono">#{analysis.id}</span>} />
        <KeyValue label="Round" value={analysis.round ?? <span className="text-amber-600 italic">— champ absent</span>} />
        <KeyValue label="Coût" value={fmtCost(analysis.cost_usd)} />
        <KeyValue label="Créé le" value={fmtDatetime(analysis.created_at)} />
      </Dl>

      {/* Lien vers le détail */}
      <Link
        href={`/v2/analyses/${analysis.id}`}
        className="mt-auto inline-flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200 transition-colors border border-gray-700 hover:border-gray-500 rounded-md px-3 py-1.5 self-start"
      >
        Voir le détail complet →
      </Link>
    </div>
  )
}

// ── Vue 3 colonnes par tour ───────────────────────────────────────────────────

function RoundView({ round, analyses, syntheses }) {
  // Trouver la synthèse de ce tour (la plus récente si plusieurs)
  const synth = syntheses
    .filter(a => a.round === round)
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0] || null

  // Les ids bull et bear que la synthèse déclare avoir utilisés
  // Ces ids viennent du payload détail de la synthèse — ici on est dans la liste,
  // qui ne les porte pas. On indique donc la liaison via le round et les statuts.
  // Le détail de synthèse porte bull_analysis_id / bear_analysis_id explicitement.

  // bull : préférer draft/final non superseded pour le tour courant, sinon l'unique disponible
  const bullsOfRound = analyses.filter(a => a.analysis_type === 'bull' && a.round === round)
  const bearsOfRound = analyses.filter(a => a.analysis_type === 'bear' && a.round === round)

  // Pour bull, pas de superseded attendu (les superseded sont tous bear dans les données observées)
  const bull = bullsOfRound[0] || null
  const bear = bearsOfRound.find(a => a.status !== 'superseded') || bearsOfRound[0] || null
  const supersededBears = bearsOfRound.filter(a => a.status === 'superseded')

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide flex items-center gap-2">
        Tour {round}
        {synth && synth.status === 'final' && (
          <span className="text-[10px] font-medium text-emerald-400 border border-emerald-800 bg-emerald-950/20 px-1.5 py-0.5 rounded normal-case tracking-normal">
            Synthèse finale
          </span>
        )}
      </h3>

      {/* Explication du câblage */}
      {synth && (synth.bull_analysis_id || synth.bear_analysis_id) && (
        <p className="text-xs text-gray-500 bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2">
          La synthèse #{synth.id} déclare avoir utilisé :{' '}
          {synth.bull_analysis_id ? (
            <span className="text-emerald-400 font-mono">bull #{synth.bull_analysis_id}</span>
          ) : (
            <span className="text-amber-600 italic">aucun bull explicite</span>
          )}
          {' '} et {' '}
          {synth.bear_analysis_id ? (
            <span className="text-red-400 font-mono">bear #{synth.bear_analysis_id}</span>
          ) : (
            <span className="text-amber-600 italic">aucun bear explicite</span>
          )}
          .
          Ces ids sont ceux stockés dans le payload de la synthèse — pas déduits par la date.
        </p>
      )}

      {/* Bears superseded du tour */}
      {supersededBears.length > 0 && (
        <div className="rounded-lg border border-gray-800 bg-gray-900/20 px-4 py-3 space-y-1">
          <p className="text-xs text-gray-500 font-medium">Bears remplacés ce tour</p>
          <div className="flex flex-wrap gap-2">
            {supersededBears.map(b => (
              <Link
                key={b.id}
                href={`/v2/analyses/${b.id}`}
                className="text-xs text-gray-500 hover:text-gray-300 font-mono"
              >
                #{b.id} (superseded)
              </Link>
            ))}
          </div>
          <p className="text-xs text-gray-600">
            Un tour de réfutation a produit un nouveau bear qui supersede le précédent.
          </p>
        </div>
      )}

      {/* 3 colonnes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <AnalysisColumn
          type="bull"
          analysis={bull}
          isLinked={synth ? synth.bull_analysis_id === bull?.id : false}
        />
        <AnalysisColumn
          type="bear"
          analysis={bear}
          isLinked={synth ? synth.bear_analysis_id === bear?.id : false}
        />
        <AnalysisColumn
          type="synthesis"
          analysis={synth}
          isLinked={false}
        />
      </div>
    </div>
  )
}

// ── Tableau historique ────────────────────────────────────────────────────────

function HistoryRow({ a }) {
  return (
    <tr className="border-t border-gray-800 hover:bg-gray-900/30 transition-colors">
      <td className="py-2 px-3 text-xs text-gray-400 font-mono">
        <Link href={`/v2/analyses/${a.id}`} className="hover:text-gray-200">
          #{a.id}
        </Link>
      </td>
      <td className="py-2 px-3 text-xs">
        <TypeBadge type={a.analysis_type} />
      </td>
      <td className="py-2 px-3 text-xs text-gray-400">{a.round ?? '—'}</td>
      <td className="py-2 px-3 text-xs">
        <StatusBadge status={a.status} />
      </td>
      <td className="py-2 px-3 text-xs text-gray-400">{fmtCost(a.cost_usd)}</td>
      <td className="py-2 px-3 text-xs text-gray-500">{fmtDatetime(a.created_at)}</td>
    </tr>
  )
}

// ── Sélecteur de tour ─────────────────────────────────────────────────────────

function RoundSelector({ rounds, current, onChange }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs text-gray-500">Tour :</span>
      {rounds.map(r => (
        <button
          key={r}
          onClick={() => onChange(r)}
          className={`text-xs px-3 py-1 rounded-md border transition-colors ${
            r === current
              ? 'border-sky-700 bg-sky-950/30 text-sky-300'
              : 'border-gray-700 bg-gray-900/50 text-gray-400 hover:border-gray-500 hover:text-gray-300'
          }`}
        >
          Tour {r}
        </button>
      ))}
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function TickerAnalyses() {
  const router = useRouter()
  const { ticker_id } = router.query

  const [analyses, setAnalyses] = useState(null)
  // syntheses: detail enrichi pour chaque synthèse (bull_analysis_id / bear_analysis_id)
  const [synthDetails, setSynthDetails] = useState({})
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedRound, setSelectedRound] = useState(null)

  // Chargement de la liste
  useEffect(() => {
    if (!ticker_id) return
    setLoading(true)
    fetch(`${API}/tickers/${ticker_id}/analyses`)
      .then(r => r.ok ? r.json() : r.json().then(d => Promise.reject(d.detail || `Erreur ${r.status}`)))
      .then(data => {
        const sorted = Array.isArray(data)
          ? [...data].sort((a, b) => b.round - a.round || new Date(b.created_at) - new Date(a.created_at))
          : []
        setAnalyses(sorted)
        // Tour affiché par défaut : celui qui porte la synthèse « final ».
        // Prendre bêtement le tour le plus récent ouvre l'écran sur un tour de
        // réfutation partiel (souvent un seul bear), soit 2 colonnes vides sur 3 —
        // la vue la moins informative. À défaut de synthèse final, on retombe sur
        // le tour le plus complet, puis sur le plus récent.
        const rounds = [...new Set(sorted.map(a => a.round))].sort((a, b) => b - a)
        if (rounds.length > 0) {
          const tourFinal = sorted.find(a => a.analysis_type === 'synthesis' && a.status === 'final')
          if (tourFinal) {
            setSelectedRound(tourFinal.round)
          } else {
            const complet = [...rounds].sort((x, y) => {
              const n = r => new Set(sorted.filter(a => a.round === r).map(a => a.analysis_type)).size
              return n(y) - n(x) || y - x
            })[0]
            setSelectedRound(complet)
          }
        }
        setLoading(false)
      })
      .catch(e => { setErr(String(e)); setLoading(false) })
  }, [ticker_id])

  // Chargement des détails des synthèses (pour bull_analysis_id / bear_analysis_id)
  useEffect(() => {
    if (!analyses) return
    const synths = analyses.filter(a => a.analysis_type === 'synthesis')
    synths.forEach(s => {
      if (synthDetails[s.id]) return // déjà chargé
      fetch(`${API}/analyses/${s.id}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (!data) return
          setSynthDetails(prev => ({ ...prev, [s.id]: data }))
        })
        .catch(() => {})
    })
  }, [analyses])

  // ── Loading / erreur ──────────────────────────────────────────────────────
  if (loading) return (
    <div className="py-12 text-center text-sm text-gray-500">Chargement…</div>
  )
  if (err) return (
    <div>
      <Link href={`/v2/tickers/${ticker_id}`} className="text-xs text-gray-500 hover:text-gray-300 mb-4 inline-block">
        ← Retour au ticker
      </Link>
      <ErrorState detail={err} />
    </div>
  )
  if (!analyses) return null

  const rounds = [...new Set(analyses.map(a => a.round))].sort((a, b) => b - a)

  // Pour la vue 3 colonnes, enrichir les synthèses avec les détails chargés
  const analysesWithSynthDetail = analyses.map(a => {
    if (a.analysis_type !== 'synthesis') return a
    const detail = synthDetails[a.id]
    if (!detail) return a
    return { ...a, bull_analysis_id: detail.bull_analysis_id, bear_analysis_id: detail.bear_analysis_id }
  })

  const syntheses = analysesWithSynthDetail.filter(a => a.analysis_type === 'synthesis')

  const totalCost = analyses.reduce((sum, a) => sum + (a.cost_usd || 0), 0)

  return (
    <div className="space-y-8">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link href="/v2" className="hover:text-gray-300">V2</Link>
        <span>›</span>
        <Link href={`/v2/tickers/${ticker_id}`} className="hover:text-gray-300">{ticker_id}</Link>
        <span>›</span>
        <span className="text-gray-300">Analyses</span>
      </div>

      {/* Titre */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-white">Analyses — {ticker_id}</h1>
        <Badge variant="gray">{analyses.length} analyse{analyses.length !== 1 ? 's' : ''}</Badge>
        <Badge variant="gray">{rounds.length} tour{rounds.length !== 1 ? 's' : ''}</Badge>
      </div>

      {/* Coût total */}
      <Card>
        <CardBody>
          <Dl cols={3}>
            <KeyValue label="Analyses totales" value={analyses.length} />
            <KeyValue label="Tours" value={rounds.length} />
            <KeyValue label="Coût total" value={`${totalCost.toFixed(4)} $`} />
          </Dl>
        </CardBody>
      </Card>

      {analyses.length === 0 ? (
        <EmptyState
          title="Aucune analyse"
          description="Les analyses apparaissent après le premier lancement du flux V2."
        />
      ) : (
        <>
          {/* ── Section 1 : Vue 3 colonnes ────────────────────────────────────── */}
          <Section title="Confrontation bull / bear / synthèse">
            <p className="text-xs text-gray-600 bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2 -mt-1">
              Chaîne Option C : base neutre → bull et bear produits isolément (aucun ne voit l'autre) → réfutation bear→bull → synthèse.
              Les 3 colonnes montrent une confrontation organisée. Un «&nbsp;nourrit synthèse&nbsp;» indique quelle version a effectivement alimenté la synthèse
              (lu depuis <code className="text-gray-400">bull_analysis_id</code> / <code className="text-gray-400">bear_analysis_id</code> du payload synthèse, pas déduit par la date).
            </p>

            {rounds.length > 1 && (
              <RoundSelector
                rounds={rounds}
                current={selectedRound}
                onChange={setSelectedRound}
              />
            )}

            {selectedRound !== null && (
              <RoundView
                round={selectedRound}
                analyses={analysesWithSynthDetail}
                syntheses={syntheses}
              />
            )}
          </Section>

          {/* ── Section 2 : Historique complet ───────────────────────────────── */}
          <Section title="Historique de toutes les analyses">
            <Card>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-[11px] text-gray-600 uppercase tracking-wide">
                      <th className="py-2 px-3 font-medium">ID</th>
                      <th className="py-2 px-3 font-medium">Type</th>
                      <th className="py-2 px-3 font-medium">Tour</th>
                      <th className="py-2 px-3 font-medium">Statut</th>
                      <th className="py-2 px-3 font-medium">Coût</th>
                      <th className="py-2 px-3 font-medium">Créé le</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyses.map(a => <HistoryRow key={a.id} a={a} />)}
                  </tbody>
                </table>
              </div>
            </Card>
          </Section>
        </>
      )}
    </div>
  )
}
