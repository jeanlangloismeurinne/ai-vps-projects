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

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function fmtDatetime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function fmtEur(val) {
  if (val == null) return '—'
  return `${Number(val).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`
}

function fmtPct(val) {
  if (val == null) return '—'
  return `${Number(val).toFixed(1)} %`
}

function fmtCost(val) {
  if (val == null) return '—'
  return `${Number(val).toFixed(4)} $`
}

// ── Statuts d'alerte ─────────────────────────────────────────────────────────

function AlertStatusBadge({ active, triggered_at }) {
  // Trois états distincts :
  // - active=true, triggered_at=null → armée
  // - active=false, triggered_at non null → déclenchée (puis désarmée)
  // - active=false, triggered_at=null → désarmée (tranche exécutée avant déclenchement)
  if (active === true && triggered_at == null) {
    return <Badge variant="emerald">Armée</Badge>
  }
  if (active === false && triggered_at != null) {
    return <Badge variant="amber">Déclenchée</Badge>
  }
  // active=false, triggered_at=null — désarmée parce que la tranche a été exécutée
  return <Badge variant="gray">Désarmée (tranche exécutée)</Badge>
}

// ── Bloc : En-tête du plan ────────────────────────────────────────────────────

function PlanHeader({ plan }) {
  return (
    <Card>
      <CardHeader title="En-tête du plan" />
      <CardBody>
        <Dl cols={3}>
          <KeyValue label="ID du plan" value={plan.id} />
          <KeyValue label="Origine" value={plan.origine} />
          <KeyValue label="Statut" value={plan.exit_status} />
          <KeyValue
            label="Session monitoring liée"
            value={
              plan.monitoring_session_v2_id != null
                ? (
                  <Link
                    href={`/v2/monitoring/${plan.monitoring_session_v2_id}`}
                    className="text-emerald-400 hover:text-emerald-300 underline underline-offset-2"
                  >
                    Session #{plan.monitoring_session_v2_id}
                  </Link>
                )
                : <span className="text-gray-600">—</span>
            }
          />
          <KeyValue label="Modèle utilisé" value={plan.model_used ?? <span className="text-gray-600">—</span>} />
          <KeyValue label="Coût appel" value={fmtCost(plan.cost_usd)} />
          <KeyValue label="Tokens entrants" value={plan.tokens_in ?? <span className="text-gray-600">—</span>} />
          <KeyValue label="Tokens sortants" value={plan.tokens_out ?? <span className="text-gray-600">—</span>} />
          <KeyValue label="Créé le" value={fmtDatetime(plan.created_at)} />
          <KeyValue label="Mis à jour le" value={fmtDatetime(plan.updated_at)} />
          {plan.closed_at != null && (
            <KeyValue label="Clôturé le" value={fmtDatetime(plan.closed_at)} />
          )}
        </Dl>
      </CardBody>
    </Card>
  )
}

// ── Bloc : Formulaire d'exécution de tranche ──────────────────────────────────

function ExecuteTrancheForm({ planId, tranche, onSuccess }) {
  const [shares, setShares] = useState('')
  const [sellPriceEur, setSellPriceEur] = useState('')
  const [sellDate, setSellDate] = useState('')
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)
  const [errKind, setErrKind] = useState(null) // '409' | '422' | 'other'

  async function handleSubmit(e) {
    e.preventDefault()
    const confirmed = window.confirm(
      `Exécuter la tranche ${tranche.ordre} (${tranche.pct_a_vendre} %) ?\n` +
      `Déclencheur : ${tranche.declencheur}\n\n` +
      `Cela enregistre une vente réelle de trésorerie. Continuer ?`
    )
    if (!confirmed) return

    setLoading(true)
    setErr(null)
    setErrKind(null)

    const body = {
      ordre: tranche.ordre,
      shares: parseFloat(shares),
      sell_price_eur: parseFloat(sellPriceEur),
    }
    if (sellDate.trim()) body.sell_date = sellDate.trim()
    if (note.trim()) body.note = note.trim()

    try {
      const res = await fetch(`${API}/v2/exit-plans/${planId}/execute-tranche`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        onSuccess()
        return
      }
      const data = await res.json().catch(() => ({}))
      const detail = data.detail || `Erreur ${res.status}`
      if (res.status === 409) {
        setErr(detail)
        setErrKind('409')
      } else if (res.status === 422) {
        setErr(detail)
        setErrKind('422')
      } else {
        setErr(detail)
        setErrKind('other')
      }
    } catch (e) {
      setErr(String(e))
      setErrKind('other')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 pt-2">
      {/* Champs figés en lecture seule */}
      <div className="rounded-md bg-gray-900/60 border border-gray-800 px-3 py-2 space-y-1">
        <p className="text-[10px] text-gray-600 uppercase tracking-wide mb-1">Paramètres figés du plan · lecture seule</p>
        <div className="flex gap-4 flex-wrap text-xs text-gray-400">
          <span>Ordre : <span className="text-gray-200 font-mono">{tranche.ordre}</span></span>
          <span>Pct à vendre : <span className="text-gray-200 font-mono">{tranche.pct_a_vendre} %</span></span>
          <span>Déclencheur : <span className="text-gray-300">{tranche.declencheur}</span></span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Nombre d'actions vendues *</label>
          <input
            type="number"
            step="any"
            required
            value={shares}
            onChange={e => setShares(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:border-emerald-600 focus:outline-none"
            placeholder="ex. 5"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Prix de vente (EUR) *</label>
          <input
            type="number"
            step="any"
            required
            value={sellPriceEur}
            onChange={e => setSellPriceEur(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:border-emerald-600 focus:outline-none"
            placeholder="ex. 118.00"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Date de vente (optionnel)</label>
          <input
            type="date"
            value={sellDate}
            onChange={e => setSellDate(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:border-emerald-600 focus:outline-none"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Note (optionnel)</label>
          <input
            type="text"
            value={note}
            onChange={e => setNote(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:border-emerald-600 focus:outline-none"
            placeholder="contexte de l'exécution…"
          />
        </div>
      </div>

      {err && (
        <div className={`rounded-lg border px-3 py-2 text-sm ${
          errKind === '409'
            ? 'border-amber-800 bg-amber-950/20 text-amber-300'
            : errKind === '422'
              ? 'border-red-800 bg-red-950/20 text-red-400'
              : 'border-red-900/50 bg-red-950/20 text-red-400'
        }`}>
          {errKind === '409' && (
            <span className="text-[10px] font-medium uppercase tracking-wide text-amber-500 block mb-0.5">
              Pré-condition d'état non remplie (409)
            </span>
          )}
          {errKind === '422' && (
            <span className="text-[10px] font-medium uppercase tracking-wide text-red-500 block mb-0.5">
              Refus de l'agent — sortie incohérente (422)
            </span>
          )}
          {err}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium text-white transition-colors"
      >
        {loading ? 'Enregistrement…' : `Exécuter la tranche ${tranche.ordre}`}
      </button>
    </form>
  )
}

// ── Bloc : Formulaire d'armement d'alerte ─────────────────────────────────────

function ArmAlertForm({ planId, tranche, onSuccess }) {
  const [price, setPrice] = useState('')
  const [direction, setDirection] = useState('above')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)
  const [errKind, setErrKind] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setErr(null)
    setErrKind(null)

    try {
      const res = await fetch(`${API}/v2/exit-plans/${planId}/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          price: parseFloat(price),
          direction,
          ordre: tranche.ordre,
        }),
      })
      if (res.ok) {
        onSuccess()
        return
      }
      const data = await res.json().catch(() => ({}))
      const detail = data.detail || `Erreur ${res.status}`
      if (res.status === 409) {
        setErr(detail)
        setErrKind('409')
      } else if (res.status === 422) {
        setErr(detail)
        setErrKind('422')
      } else {
        setErr(detail)
        setErrKind('other')
      }
    } catch (e) {
      setErr(String(e))
      setErrKind('other')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 pt-1">
      <p className="text-xs text-gray-500">
        Le libellé de l'alerte est composé automatiquement côté serveur à partir du déclencheur figé — il n'est pas saisissable ici.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Prix de déclenchement *</label>
          <input
            type="number"
            step="any"
            required
            value={price}
            onChange={e => setPrice(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:border-emerald-600 focus:outline-none"
            placeholder="ex. 150.00"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Direction *</label>
          <select
            value={direction}
            onChange={e => setDirection(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:border-emerald-600 focus:outline-none"
          >
            <option value="above">Au-dessus (above)</option>
            <option value="below">En-dessous (below)</option>
          </select>
        </div>
      </div>

      {err && (
        <div className={`rounded-lg border px-3 py-2 text-sm ${
          errKind === '409'
            ? 'border-amber-800 bg-amber-950/20 text-amber-300'
            : errKind === '422'
              ? 'border-red-800 bg-red-950/20 text-red-400'
              : 'border-red-900/50 bg-red-950/20 text-red-400'
        }`}>
          {errKind === '409' && (
            <span className="text-[10px] font-medium uppercase tracking-wide text-amber-500 block mb-0.5">
              Pré-condition d'état non remplie (409)
            </span>
          )}
          {errKind === '422' && (
            <span className="text-[10px] font-medium uppercase tracking-wide text-red-500 block mb-0.5">
              Refus de l'agent — sortie incohérente (422)
            </span>
          )}
          {err}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="px-4 py-2 rounded-lg bg-sky-700 hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium text-white transition-colors"
      >
        {loading ? 'Armement…' : 'Armer l\'alerte'}
      </button>
    </form>
  )
}

// ── Bloc : Tranche individuelle ───────────────────────────────────────────────

function TrancheRow({ tranche, execution, planId, onReload }) {
  const [showExecForm, setShowExecForm] = useState(false)
  const [showAlertForm, setShowAlertForm] = useState(false)
  const isExecuted = execution != null

  return (
    <div className={`rounded-lg border p-4 space-y-3 ${
      isExecuted
        ? 'border-emerald-800 bg-emerald-950/10'
        : 'border-gray-800 bg-gray-900/30'
    }`}>
      {/* En-tête de la tranche */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs font-mono text-gray-500 shrink-0">Tranche {tranche.ordre}</span>
        <Badge variant={isExecuted ? 'emerald' : 'gray'}>
          {isExecuted ? 'Exécutée' : 'En attente'}
        </Badge>
        <span className="text-xs text-gray-500">
          <span className="text-gray-400 font-medium">{tranche.pct_a_vendre} %</span> à vendre
        </span>
      </div>

      {/* Déclencheur — figé */}
      <div className="text-xs text-gray-300 bg-gray-900/50 border border-gray-800 rounded px-3 py-2">
        <span className="text-[10px] text-gray-600 uppercase tracking-wide block mb-0.5">Déclencheur · figé</span>
        {tranche.declencheur}
      </div>

      {/* Exécution existante */}
      {isExecuted && (
        <div className="space-y-2">
          <p className="text-[10px] text-gray-600 uppercase tracking-wide">Détail de l'exécution</p>
          <Dl cols={3}>
            <KeyValue label="Actions vendues" value={execution.shares_sold} />
            <KeyValue label="Prix de vente (EUR)" value={fmtEur(execution.sell_price_eur)} />
            <KeyValue label="Produit (EUR)" value={fmtEur(execution.proceeds_eur)} />
            {/* Prix natif + devise + taux de change quand la devise n'est pas EUR */}
            {execution.sell_currency && execution.sell_currency !== 'EUR' && (
              <>
                <KeyValue
                  label={`Prix natif (${execution.sell_currency})`}
                  value={
                    execution.sell_price_native != null
                      ? `${Number(execution.sell_price_native).toLocaleString('fr-FR', { minimumFractionDigits: 4, maximumFractionDigits: 4 })} ${execution.sell_currency}`
                      : <span className="text-amber-600 italic">— champ absent</span>
                  }
                />
                <KeyValue
                  label="Taux de change"
                  value={
                    execution.fx_rate != null
                      ? Number(execution.fx_rate).toFixed(8)
                      : <span className="text-amber-600 italic">— champ absent</span>
                  }
                  note={`1 ${execution.sell_currency} = ${execution.fx_rate != null ? (1 / execution.fx_rate).toFixed(4) : '—'} EUR`}
                />
              </>
            )}
            <KeyValue label="Date d'exécution" value={fmtDate(execution.executed_at)} />
            <KeyValue label="Mouvement de trésorerie" value={
              execution.cash_movement_id != null
                ? <span className="font-mono text-gray-300">#{execution.cash_movement_id}</span>
                : <span className="text-gray-600">—</span>
            } />
          </Dl>
          {/* Note : affichée uniquement si non vide */}
          {execution.note != null && execution.note !== '' && (
            <div className="text-xs text-gray-400 bg-gray-900/50 border border-gray-800 rounded px-3 py-2">
              <span className="text-gray-600">Note : </span>{execution.note}
            </div>
          )}
        </div>
      )}

      {/* Tranche non exécutée → formulaires */}
      {!isExecuted && (
        <div className="space-y-3">
          <div className="flex gap-2">
            <button
              onClick={() => { setShowExecForm(v => !v); setShowAlertForm(false) }}
              className="text-xs px-3 py-1.5 rounded-md bg-emerald-900/40 border border-emerald-800 text-emerald-300 hover:bg-emerald-900/70 transition-colors"
            >
              {showExecForm ? 'Annuler' : 'Enregistrer l\'exécution'}
            </button>
            <button
              onClick={() => { setShowAlertForm(v => !v); setShowExecForm(false) }}
              className="text-xs px-3 py-1.5 rounded-md bg-sky-900/40 border border-sky-800 text-sky-300 hover:bg-sky-900/70 transition-colors"
            >
              {showAlertForm ? 'Annuler' : 'Armer une alerte'}
            </button>
          </div>

          {showExecForm && (
            <ExecuteTrancheForm
              planId={planId}
              tranche={tranche}
              onSuccess={() => { setShowExecForm(false); onReload() }}
            />
          )}
          {showAlertForm && (
            <ArmAlertForm
              planId={planId}
              tranche={tranche}
              onSuccess={() => { setShowAlertForm(false); onReload() }}
            />
          )}
        </div>
      )}
    </div>
  )
}

// ── Bloc : Conditions accélérées ─────────────────────────────────────────────

function ConditionsAccelereesBlock({ conditions }) {
  if (!Array.isArray(conditions) || conditions.length === 0) return null
  return (
    <Card>
      <CardHeader
        title="Conditions accélérées"
        subtitle="Ce ne sont pas des ordres de vente — ce sont des conditions qui déclenchent une accélération du plan."
      />
      <CardBody className="space-y-2">
        {conditions.map((c, i) => (
          <div key={i} className="flex items-start gap-3 rounded-md border border-amber-900/40 bg-amber-950/10 px-3 py-2">
            <span className="text-amber-600 text-xs font-mono shrink-0 pt-0.5">{c.type}</span>
            <span className="text-sm text-gray-300">{c.seuil}</span>
          </div>
        ))}
      </CardBody>
    </Card>
  )
}

// ── Bloc : Alertes armées ─────────────────────────────────────────────────────

function AlertsBlock({ alerts }) {
  if (!Array.isArray(alerts) || alerts.length === 0) {
    return (
      <Card>
        <CardHeader title="Alertes" />
        <CardBody>
          <p className="text-sm text-gray-500">Aucune alerte enregistrée sur ce plan.</p>
        </CardBody>
      </Card>
    )
  }
  return (
    <Card>
      <CardHeader title="Alertes" subtitle={`${alerts.length} alerte${alerts.length !== 1 ? 's' : ''}`} />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] text-gray-600 uppercase tracking-wide border-b border-gray-800">
              <th className="py-2 px-3 font-medium">ID</th>
              <th className="py-2 px-3 font-medium">Libellé</th>
              <th className="py-2 px-3 font-medium">Prix</th>
              <th className="py-2 px-3 font-medium">Direction</th>
              <th className="py-2 px-3 font-medium">Type</th>
              <th className="py-2 px-3 font-medium">État</th>
              <th className="py-2 px-3 font-medium">Déclenchée le</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map(a => (
              <tr key={a.id} className="border-t border-gray-800">
                <td className="py-2 px-3 text-xs font-mono text-gray-400">#{a.id}</td>
                <td className="py-2 px-3 text-xs text-gray-300 max-w-xs">{a.label ?? <span className="text-gray-600">—</span>}</td>
                <td className="py-2 px-3 text-xs text-gray-200 font-mono">{a.price != null ? a.price : '—'}</td>
                <td className="py-2 px-3 text-xs text-gray-400">{a.direction ?? '—'}</td>
                <td className="py-2 px-3 text-xs text-gray-400">{a.alert_type ?? '—'}</td>
                <td className="py-2 px-3 text-xs">
                  <AlertStatusBadge active={a.active} triggered_at={a.triggered_at} />
                </td>
                <td className="py-2 px-3 text-xs text-gray-500">
                  {a.triggered_at != null ? fmtDatetime(a.triggered_at) : <span className="text-gray-600">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

// ── Bouton de génération du plan (appel modèle facturé) ───────────────────────

function GeneratePlanButton({ thesisId, onSuccess }) {
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)
  const [errKind, setErrKind] = useState(null)

  async function handleClick() {
    const confirmed = window.confirm(
      'Générer le plan de sortie ?\n\n' +
      'Cet appel sollicite un modèle IA — il est facturé. Continuer ?'
    )
    if (!confirmed) return

    setLoading(true)
    setErr(null)
    setErrKind(null)
    try {
      const res = await fetch(`${API}/v2/theses/${thesisId}/exit-plan`, {
        method: 'POST',
      })
      if (res.ok) {
        onSuccess()
        return
      }
      const data = await res.json().catch(() => ({}))
      const detail = data.detail || `Erreur ${res.status}`
      if (res.status === 409) {
        setErr(detail)
        setErrKind('409')
      } else if (res.status === 422) {
        setErr(detail)
        setErrKind('422')
      } else {
        setErr(detail)
        setErrKind('other')
      }
    } catch (e) {
      setErr(String(e))
      setErrKind('other')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <button
        onClick={handleClick}
        disabled={loading}
        className="px-5 py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium text-white transition-colors"
      >
        {loading ? 'Génération en cours…' : 'Générer le plan de sortie — appel modèle facturé'}
      </button>
      {err && (
        <div className={`rounded-lg border px-3 py-2 text-sm ${
          errKind === '409'
            ? 'border-amber-800 bg-amber-950/20 text-amber-300'
            : 'border-red-900/50 bg-red-950/20 text-red-400'
        }`}>
          {errKind === '409' && (
            <span className="text-[10px] font-medium uppercase tracking-wide text-amber-500 block mb-0.5">
              Pré-condition d'état non remplie (409)
            </span>
          )}
          {errKind === '422' && (
            <span className="text-[10px] font-medium uppercase tracking-wide text-red-500 block mb-0.5">
              Refus de l'agent — sortie incohérente (422)
            </span>
          )}
          {err}
        </div>
      )}
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function SortiePage() {
  const router = useRouter()
  const { id } = router.query

  const [thesis, setThesis] = useState(null)
  const [plan, setPlan] = useState(null)
  const [planNotFound, setPlanNotFound] = useState(false)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)

  async function loadData() {
    if (!id) return
    setLoading(true)
    setErr(null)
    setPlanNotFound(false)

    try {
      // Chargement parallèle de la thèse et du plan de sortie
      const [thesisRes, planRes] = await Promise.all([
        fetch(`${API}/v2/theses/${id}`),
        fetch(`${API}/v2/theses/${id}/exit-plan`),
      ])

      if (!thesisRes.ok) {
        const d = await thesisRes.json().catch(() => ({}))
        throw new Error(d.detail || `Erreur ${thesisRes.status} sur la thèse`)
      }
      const thesisData = await thesisRes.json()
      setThesis(thesisData)

      if (planRes.status === 404) {
        setPlanNotFound(true)
        setPlan(null)
      } else if (!planRes.ok) {
        const d = await planRes.json().catch(() => ({}))
        throw new Error(d.detail || `Erreur ${planRes.status} sur le plan de sortie`)
      } else {
        const planData = await planRes.json()
        setPlan(planData)
      }
    } catch (e) {
      setErr(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [id])

  // ── Chargement / erreur ──────────────────────────────────────────────────────
  if (loading) return (
    <div className="py-12 text-center text-sm text-gray-500">Chargement…</div>
  )

  if (err) return (
    <div>
      <Link href="/v2/theses" className="text-xs text-gray-500 hover:text-gray-300 mb-4 inline-block">
        ← Retour aux thèses
      </Link>
      <ErrorState detail={err} />
    </div>
  )

  const ticker = thesis?.ticker_id || `Thèse #${id}`

  // ── État : pas de plan (404) ─────────────────────────────────────────────────
  if (planNotFound) {
    return (
      <div className="space-y-6">
        {/* Fil d'Ariane */}
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Link href="/v2/theses" className="hover:text-gray-300">Thèses V2</Link>
          <span>›</span>
          <Link href={`/v2/theses/${id}`} className="hover:text-gray-300">{ticker}</Link>
          <span>›</span>
          <span className="text-gray-300">Plan de sortie</span>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-2xl font-bold text-white">Plan de sortie</h1>
          {thesis?.status && (
            <Badge variant={thesis.status === 'active' ? 'active' : 'gray'}>Thèse : {thesis.status}</Badge>
          )}
        </div>

        <EmptyState
          title="Aucun plan de sortie"
          description="Un plan de sortie est généré sur une thèse active dont le monitoring a conclu RÉDUIRE ou SORTIR. L'agent lit l'antécédent de suivi en base avant de produire le plan."
        />

        <GeneratePlanButton thesisId={id} onSuccess={loadData} />
      </div>
    )
  }

  if (!plan) return null

  // Construction de l'index executions par ordre
  const execByOrdre = {}
  if (Array.isArray(plan.executions)) {
    plan.executions.forEach(ex => {
      execByOrdre[ex.ordre] = ex
    })
  }

  const tranches = Array.isArray(plan.plan_json?.tranches) ? plan.plan_json.tranches : []
  const conditionsAccelerees = Array.isArray(plan.plan_json?.conditions_accelerees)
    ? plan.plan_json.conditions_accelerees
    : []
  const alerts = Array.isArray(plan.alerts) ? plan.alerts : []

  return (
    <div className="space-y-6">
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link href="/v2/theses" className="hover:text-gray-300">Thèses V2</Link>
        <span>›</span>
        <Link href={`/v2/theses/${id}`} className="hover:text-gray-300">{ticker}</Link>
        <span>›</span>
        <span className="text-gray-300">Plan de sortie</span>
      </div>

      {/* Titre */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-white">Plan de sortie</h1>
        {/* Les deux statuts valent « closed » une fois la position soldée : sans préfixe, deux
            badges identiques côte à côte ne disent plus lequel parle de la thèse et lequel du plan. */}
        {thesis?.status && (
          <Badge variant={thesis.status === 'active' ? 'active' : 'gray'}>Thèse : {thesis.status}</Badge>
        )}
        <Badge variant={plan.exit_status === 'closed' ? 'gray' : 'emerald'}>
          Plan : {plan.exit_status ?? '—'}
        </Badge>
      </div>

      {/* En-tête du plan */}
      <PlanHeader plan={plan} />

      {/* Progression des tranches */}
      <Section title={`Tranches (${tranches.length})`}>
        <p className="text-xs text-gray-600 bg-gray-900/50 border border-gray-800 rounded-lg px-3 py-2">
          Chaque tranche du plan est affichée avec son exécution correspondante quand elle existe. Les tranches non exécutées proposent un formulaire d'enregistrement.
        </p>
        {tranches.length === 0 ? (
          <p className="text-sm text-gray-500">Aucune tranche dans le plan.</p>
        ) : (
          <div className="space-y-3">
            {tranches.map(tr => (
              <TrancheRow
                key={tr.ordre}
                tranche={tr}
                execution={execByOrdre[tr.ordre] ?? null}
                planId={plan.id}
                onReload={loadData}
              />
            ))}
          </div>
        )}
      </Section>

      {/* Conditions accélérées */}
      {conditionsAccelerees.length > 0 && (
        <ConditionsAccelereesBlock conditions={conditionsAccelerees} />
      )}

      {/* Alertes */}
      <AlertsBlock alerts={alerts} />
    </div>
  )
}
