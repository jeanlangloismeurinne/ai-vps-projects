import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Card, CardHeader, CardBody, Badge, EmptyState, ErrorState } from '../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

// Les 7 tiers TELS QU'ILS SONT STOCKÉS. Le regroupement grossier (A / B / C) affiché
// sur l'écran readiness s'en déduit — voir la note de réconciliation plus bas.
const TIERS = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']

// Les 5 étapes de la chaîne amont V2, dans l'ordre où elles doivent être franchies.
// `done` répond à « cette étape a-t-elle produit quelque chose ? », pas à « est-elle bonne ? ».
function etapes(t) {
  return [
    {
      cle: 'knowledge',
      label: 'Connaissance',
      done: t.nb_entries_vivantes > 0,
      detail: t.nb_entries_vivantes > 0 ? `${t.nb_entries_vivantes} entrées vivantes` : 'aucune entrée',
      href: `/v2/tickers/${t.ticker_id}/knowledge`,
    },
    {
      cle: 'readiness',
      label: 'Readiness',
      done: t.readiness !== null,
      detail: t.readiness ? t.readiness.verdict : 'pas de rapport',
      href: `/v2/tickers/${t.ticker_id}/readiness`,
    },
    {
      cle: 'research',
      label: 'Research',
      done: t.nb_research_memos > 0,
      detail: t.nb_research_memos > 0 ? `${t.nb_research_memos} memo(s)` : 'aucun memo',
      href: `/v2/tickers/${t.ticker_id}/research`,
    },
    {
      cle: 'analyses',
      label: 'Analyses',
      done: t.id_synthese_final !== null,
      detail: t.id_synthese_final !== null
        ? `synthèse #${t.id_synthese_final} final`
        : `bull ${t.nb_analyses_par_type.bull} · bear ${t.nb_analyses_par_type.bear} · synth ${t.nb_analyses_par_type.synthesis}`,
      href: `/v2/tickers/${t.ticker_id}/analyses`,
    },
    {
      cle: 'decision',
      label: 'Décision',
      done: t.these_v2 !== null,
      detail: t.these_v2 ? `thèse #${t.these_v2.id} · ${t.these_v2.status}` : 'pas de thèse V2',
      href: `/v2/tickers/${t.ticker_id}/decision`,
    },
  ]
}

// Pastille d'étape : verte si franchie, grise sinon. Une étape non franchie reste
// cliquable — l'écran cible explique alors POURQUOI il n'y a rien, ce qui est
// l'information utile.
function Etape({ e }) {
  return (
    <Link
      href={e.href}
      className={`flex-1 min-w-[8rem] rounded-lg border px-3 py-2 transition-colors ${
        e.done
          ? 'border-emerald-800/70 bg-emerald-950/30 hover:border-emerald-600'
          : 'border-gray-800 bg-gray-900/40 hover:border-gray-600'
      }`}
    >
      <div className="flex items-center gap-1.5">
        <span className={e.done ? 'text-emerald-400' : 'text-gray-700'}>{e.done ? '●' : '○'}</span>
        <span className={`text-xs font-medium ${e.done ? 'text-emerald-200' : 'text-gray-500'}`}>
          {e.label}
        </span>
      </div>
      <p className={`text-[11px] mt-0.5 ${e.done ? 'text-gray-400' : 'text-gray-600'}`}>{e.detail}</p>
    </Link>
  )
}

function TierBar({ parTier }) {
  const total = TIERS.reduce((s, t) => s + (parTier[t] || 0), 0)
  if (total === 0) return <span className="text-xs text-gray-600">aucune entrée</span>
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {TIERS.map(t => {
        const n = parTier[t] || 0
        if (n === 0) return null
        const variant = t.startsWith('A') ? 'emerald' : t.startsWith('B') ? 'sky' : 'amber'
        return <Badge key={t} variant={variant}>{t} : {n}</Badge>
      })}
      <span className="text-[11px] text-gray-600">
        tiers stockés (7 niveaux) — l&apos;écran readiness les regroupe en A / B / C
      </span>
    </div>
  )
}

function TickerCard({ t }) {
  const franchies = etapes(t).filter(e => e.done).length
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <Link href={`/v2/tickers/${t.ticker_id}`} className="text-white hover:text-emerald-300">
              {t.ticker_symbol || t.ticker_id}
            </Link>
            <span className="text-gray-500 font-normal">{t.name}</span>
          </span>
        }
        subtitle={`${t.status} · ${t.company_type}${t.sector ? ` · ${t.sector}` : ''}`}
        action={
          <Badge variant={franchies === 5 ? 'emerald' : franchies > 0 ? 'sky' : 'gray'}>
            {franchies}/5 étapes
          </Badge>
        }
      />
      <CardBody className="space-y-3">
        <div className="flex gap-2 flex-wrap">
          {etapes(t).map(e => <Etape key={e.cle} e={e} />)}
        </div>
        <TierBar parTier={t.par_tier} />
      </CardBody>
    </Card>
  )
}

export default function TickersV2() {
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState(null)
  const [includeAll, setIncludeAll] = useState(false)

  useEffect(() => {
    setRows(null)
    setErr(null)
    fetch(`${API}/v2/tickers?include_all=${includeAll}`)
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => setRows(Array.isArray(d) ? d : []))
      .catch(e => setErr(String(e)))
  }, [includeAll])

  const avecMatiere = rows ? rows.filter(t => t.nb_entries_vivantes > 0).length : 0

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-white">Tickers — chaîne V2 amont</h1>
          <p className="text-sm text-gray-500 mt-1">
            Point d&apos;entrée du parcours amont : connaissance → readiness → research → analyses → décision.
            Chaque pastille mène à l&apos;écran correspondant.
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer shrink-0">
          <input
            type="checkbox"
            checked={includeAll}
            onChange={e => setIncludeAll(e.target.checked)}
            className="accent-emerald-600"
          />
          Afficher aussi les tickers sans matière V2
        </label>
      </div>

      {err && <ErrorState detail={`Chargement des tickers impossible (${err}).`} />}
      {!err && !rows && <p className="text-sm text-gray-500">Chargement…</p>}

      {rows && rows.length === 0 && (
        <EmptyState
          title="Aucun ticker avec de la matière V2"
          description="Coche « afficher aussi les tickers sans matière » pour démarrer un nouveau ticker."
        />
      )}

      {rows && rows.length > 0 && (
        <>
          <p className="text-xs text-gray-600">
            {rows.length} ticker(s) affiché(s) · {avecMatiere} avec au moins une entrée de connaissance vivante
            {includeAll && rows.length > avecMatiere && ` · ${rows.length - avecMatiere} sans matière`}
          </p>
          <div className="space-y-3">
            {rows.map(t => <TickerCard key={t.ticker_id} t={t} />)}
          </div>
        </>
      )}
    </div>
  )
}
