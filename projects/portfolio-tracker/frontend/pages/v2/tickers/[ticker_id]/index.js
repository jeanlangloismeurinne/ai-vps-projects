import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import { Card, CardHeader, CardBody, Badge, KeyValue, Dl, EmptyState, ErrorState } from '../../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const TIERS = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']

// Une étape de la chaîne : ce qu'elle a produit, et pourquoi elle est franchie ou non.
// `bloquant` distingue « pas encore fait » de « fait mais insuffisant ».
function etapes(t) {
  return [
    {
      cle: 'knowledge',
      num: 1,
      label: 'Connaissance',
      done: t.nb_entries_vivantes > 0,
      resume: t.nb_entries_vivantes > 0
        ? `${t.nb_entries_vivantes} entrées vivantes (non supprimées, non remplacées)`
        : 'Aucune entrée de connaissance vivante — la chaîne ne peut pas démarrer.',
      href: `/v2/tickers/${t.ticker_id}/knowledge`,
    },
    {
      cle: 'readiness',
      num: 2,
      label: 'Readiness',
      done: t.readiness !== null,
      resume: t.readiness
        ? `Rapport #${t.readiness.id} — verdict ${t.readiness.verdict}`
        : 'Aucun rapport de readiness. Le curator n’a pas encore statué sur la suffisance de la connaissance.',
      href: `/v2/tickers/${t.ticker_id}/readiness`,
    },
    {
      cle: 'research',
      num: 3,
      label: 'Research memo',
      done: t.nb_research_memos > 0,
      resume: t.nb_research_memos > 0
        ? `${t.nb_research_memos} memo(s) — le plus récent : #${t.dernier_research_memo_id}`
        : 'Aucun memo de recherche.',
      href: `/v2/tickers/${t.ticker_id}/research`,
    },
    {
      cle: 'analyses',
      num: 4,
      label: 'Analyses bull / bear / synthèse',
      done: t.id_synthese_final !== null,
      resume: t.id_synthese_final !== null
        ? `Synthèse #${t.id_synthese_final} en statut final · bull ${t.nb_analyses_par_type.bull} · bear ${t.nb_analyses_par_type.bear} · synthèse ${t.nb_analyses_par_type.synthesis}`
        : (t.nb_analyses_par_type.bull + t.nb_analyses_par_type.bear + t.nb_analyses_par_type.synthesis) > 0
          ? `Analyses en cours, aucune synthèse « final » — bull ${t.nb_analyses_par_type.bull} · bear ${t.nb_analyses_par_type.bear} · synthèse ${t.nb_analyses_par_type.synthesis}`
          : 'Aucune analyse.',
      href: `/v2/tickers/${t.ticker_id}/analyses`,
    },
    {
      cle: 'decision',
      num: 5,
      label: 'Décision',
      done: t.these_v2 !== null,
      resume: t.these_v2
        ? `Thèse V2 #${t.these_v2.id} — statut ${t.these_v2.status}`
        : 'Aucune thèse V2. La décision n’a pas été prise.',
      href: `/v2/tickers/${t.ticker_id}/decision`,
    },
  ]
}

function EtapeRow({ e }) {
  return (
    <Link
      href={e.href}
      className={`flex items-start gap-3 rounded-lg border px-4 py-3 transition-colors ${
        e.done
          ? 'border-emerald-900/70 bg-emerald-950/20 hover:border-emerald-600'
          : 'border-gray-800 bg-gray-900/30 hover:border-gray-600'
      }`}
    >
      <span
        className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
          e.done ? 'bg-emerald-800 text-emerald-100' : 'bg-gray-800 text-gray-500'
        }`}
      >
        {e.done ? '✓' : e.num}
      </span>
      <div className="min-w-0">
        <p className={`text-sm font-medium ${e.done ? 'text-emerald-200' : 'text-gray-400'}`}>{e.label}</p>
        <p className="text-xs text-gray-500 mt-0.5">{e.resume}</p>
      </div>
    </Link>
  )
}

// Réconciliation explicite des deux granularités de tier. Sans ce bloc, l'écran
// knowledge (7 tiers) et l'écran readiness (3 groupes) se lisent comme une contradiction.
function TierReconciliation({ parTier }) {
  const n = t => parTier[t] || 0
  const groupes = [
    { label: 'tier_A', membres: ['A', 'A-'], variant: 'emerald' },
    { label: 'tier_B', membres: ['B+', 'B', 'B-'], variant: 'sky' },
    { label: 'tier_C', membres: ['C+', 'C'], variant: 'amber' },
  ]
  const total = TIERS.reduce((s, t) => s + n(t), 0)
  if (total === 0) return <p className="text-sm text-gray-600">Aucune entrée vivante à ventiler.</p>
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {TIERS.map(t => (
          <Badge key={t} variant={n(t) === 0 ? 'gray' : t.startsWith('A') ? 'emerald' : t.startsWith('B') ? 'sky' : 'amber'}>
            {t} : {n(t)}
          </Badge>
        ))}
      </div>
      <div className="rounded-lg border border-gray-800 bg-gray-950/40 px-3 py-2 space-y-1">
        <p className="text-[11px] text-gray-500 uppercase tracking-wide">
          Regroupement utilisé par l&apos;écran readiness
        </p>
        {groupes.map(g => (
          <p key={g.label} className="text-xs text-gray-400 font-mono">
            {g.label} = {g.membres.map(m => `${m}(${n(m)})`).join(' + ')} = {g.membres.reduce((s, m) => s + n(m), 0)}
          </p>
        ))}
        <p className="text-[11px] text-gray-600 pt-1">
          Les deux écrans comptent les mêmes entrées : readiness agrège les 7 tiers stockés en 3 groupes.
        </p>
      </div>
    </div>
  )
}

export default function TickerPivot() {
  const router = useRouter()
  const { ticker_id } = router.query
  const [t, setT] = useState(null)
  const [err, setErr] = useState(null)
  const [absent, setAbsent] = useState(false)

  useEffect(() => {
    if (!ticker_id) return
    setT(null); setErr(null); setAbsent(false)
    // Pas de route de détail par ticker : on lit l'agrégat et on filtre.
    // include_all=true pour afficher aussi un ticker sans aucune matière V2.
    fetch(`${API}/v2/tickers?include_all=true`)
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(rows => {
        const found = (Array.isArray(rows) ? rows : []).find(x => x.ticker_id === ticker_id)
        if (!found) setAbsent(true)
        else setT(found)
      })
      .catch(e => setErr(String(e)))
  }, [ticker_id])

  if (err) return <ErrorState detail={`Chargement impossible (${err}).`} />
  if (absent) {
    return (
      <EmptyState
        title={`Ticker « ${ticker_id} » introuvable`}
        description="Aucun ticker de ce nom en base. Vérifie l'identifiant depuis la liste des tickers."
      />
    )
  }
  if (!t) return <p className="text-sm text-gray-500">Chargement…</p>

  const franchies = etapes(t).filter(e => e.done).length

  return (
    <div className="space-y-5">
      <div>
        <Link href="/v2/tickers" className="text-xs text-gray-500 hover:text-emerald-300">
          ← Tous les tickers
        </Link>
        <h1 className="text-xl font-bold text-white mt-1 flex items-center gap-3 flex-wrap">
          {t.ticker_symbol || t.ticker_id}
          <span className="text-sm font-normal text-gray-500">{t.name}</span>
          <Badge variant={franchies === 5 ? 'emerald' : franchies > 0 ? 'sky' : 'gray'}>
            {franchies}/5 étapes franchies
          </Badge>
        </h1>
      </div>

      <Card>
        <CardHeader title="Identité" />
        <CardBody>
          <Dl cols={4}>
            <KeyValue label="ticker_id" value={<span className="font-mono text-xs">{t.ticker_id}</span>} />
            <KeyValue
              label="ticker_symbol"
              value={t.ticker_symbol === null
                ? <span className="text-gray-600">non renseigné (null)</span>
                : t.ticker_symbol}
            />
            <KeyValue label="status" value={t.status} />
            <KeyValue label="company_type" value={t.company_type} />
            <KeyValue
              label="sector"
              value={t.sector === null
                ? <span className="text-gray-600">non renseigné (null)</span>
                : t.sector}
            />
          </Dl>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Chaîne amont V2"
          subtitle="Chaque étape mène à son écran. Une étape non franchie reste consultable — l'écran explique alors ce qui manque."
        />
        <CardBody className="space-y-2">
          {etapes(t).map(e => <EtapeRow key={e.cle} e={e} />)}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Connaissance — ventilation par tier"
          subtitle="Entrées vivantes uniquement (is_deleted = false, superseded_by IS NULL)"
          action={<Badge variant="gray">{t.nb_entries_vivantes} vivantes</Badge>}
        />
        <CardBody>
          <TierReconciliation parTier={t.par_tier} />
        </CardBody>
      </Card>
    </div>
  )
}
