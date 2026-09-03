import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import {
  Card, CardHeader, CardBody, Badge, KeyValue, Dl, Section, EmptyState, ErrorState,
} from '../../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const fmtPct = v => (v === null || v === undefined ? null : `${Number(v).toFixed(2)} %`)
const fmtNum = v => (v === null || v === undefined ? null : Number(v).toLocaleString('fr-FR'))

// Champ absent du payload ≠ champ présent à null. Les deux se voient différemment.
function Val({ v, unite }) {
  if (v === undefined) return <span className="text-amber-400 text-xs">— champ absent</span>
  if (v === null) return <span className="text-gray-600">non renseigné (null)</span>
  return <>{v}{unite ? ` ${unite}` : ''}</>
}

// ── G2 ───────────────────────────────────────────────────────────────────────
// Le verdict, le sizing et les conditions d'entrée sont produits par la synthèse et
// lus en base. Ils ne sont JAMAIS des champs de saisie : les afficher en lecture seule
// est le seul rendu correct. Un sizing différent du recommandé se trace en amont dans
// la synthèse (override A7), pas ici.
function BlocFige({ these }) {
  return (
    <Card className="border-emerald-900/60">
      <CardHeader
        title="Ce que la synthèse a décidé"
        subtitle="Lu en base, jamais saisi ici — l'utilisateur acquitte, il ne rédige pas la décision."
        action={<Badge variant={these.verdict || 'gray'}>{these.verdict || '—'}</Badge>}
      />
      <CardBody className="space-y-4">
        <Dl cols={3}>
          <KeyValue
            label="Verdict"
            locked
            value={these.verdict ? <Badge variant={these.verdict}>{these.verdict}</Badge> : <Val v={these.verdict} />}
          />
          <KeyValue
            label="Sizing recommandé"
            locked
            value={fmtPct(these.position_sizing_pct) ?? <Val v={these.position_sizing_pct} />}
            note="du portefeuille"
          />
          <KeyValue
            label="Synthèse source"
            locked
            value={these.synthesis_analysis_id
              ? <Link href={`/v2/analyses/${these.synthesis_analysis_id}`} className="text-emerald-400 hover:underline">
                  analyse #{these.synthesis_analysis_id}
                </Link>
              : <Val v={these.synthesis_analysis_id} />}
          />
          <KeyValue
            label="Research memo source"
            locked
            value={these.research_memo_id
              ? <Link href={`/v2/research/${these.research_memo_id}`} className="text-emerald-400 hover:underline">
                  memo #{these.research_memo_id}
                </Link>
              : <Val v={these.research_memo_id} />}
          />
          <KeyValue label="schema_version" locked value={<Val v={these.schema_version} />} />
          <KeyValue label="Statut de la thèse" value={<Badge variant={these.status || 'gray'}>{these.status}</Badge>} />
        </Dl>

        <Section title="Fourchette de valorisation">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-lg border border-gray-800 bg-gray-950/40 px-3 py-2">
              <p className="text-[11px] text-gray-500 uppercase tracking-wide mb-1">valuation_range (courante)</p>
              {these.valuation_range
                ? <Dl cols={3}>
                    <KeyValue label="low" value={<Val v={these.valuation_range.low} />} />
                    <KeyValue label="base" value={<Val v={these.valuation_range.base} />} />
                    <KeyValue label="high" value={<Val v={these.valuation_range.high} />} />
                  </Dl>
                : <Val v={these.valuation_range} />}
            </div>
            <div className="rounded-lg border border-emerald-900/50 bg-emerald-950/20 px-3 py-2">
              <p className="text-[11px] text-emerald-500 uppercase tracking-wide mb-1">
                valuation_range_figee — gelée au validate
              </p>
              {these.valuation_range_figee
                ? <Dl cols={3}>
                    <KeyValue label="low" value={<Val v={these.valuation_range_figee.low} />} />
                    <KeyValue label="base" value={<Val v={these.valuation_range_figee.base} />} />
                    <KeyValue label="high" value={<Val v={these.valuation_range_figee.high} />} />
                  </Dl>
                : <Val v={these.valuation_range_figee} />}
            </div>
          </div>
        </Section>

        <Section title="Conditions d'entrée">
          {Array.isArray(these.conditions_entree) && these.conditions_entree.length > 0 ? (
            <ul className="space-y-1.5">
              {these.conditions_entree.map((c, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-300">
                  <span className="text-sky-500 shrink-0">▸</span>
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          ) : Array.isArray(these.conditions_entree) ? (
            <p className="text-sm text-gray-500">
              Aucune condition d&apos;entrée — l&apos;entrée n&apos;est subordonnée à aucun prix ni événement.
            </p>
          ) : (
            <Val v={these.conditions_entree} />
          )}
        </Section>
      </CardBody>
    </Card>
  )
}

// Les acquittements réellement enregistrés, réconciliés avec les libellés de risque
// de la synthèse. `risk_acks` ne contient que {risk_index, accepted} : sans la matrice
// on afficherait « risque 0 accepté », ce qui n'apprend rien.
function BlocAcquittements({ these, risques, preMortem }) {
  const acks = Array.isArray(these.risk_acks) ? these.risk_acks : []
  const parIndex = new Map(acks.map(a => [a.risk_index, a]))
  const bijection = risques !== null && acks.length === risques.length

  return (
    <Card>
      <CardHeader
        title="Acquittements de l'utilisateur"
        subtitle="La seule chose que l'utilisateur fournit au moment de décider (hors faits d'exécution)."
        action={
          <Badge variant={these.risk_matrix_acked ? 'emerald' : 'amber'}>
            risk_matrix_acked : {String(these.risk_matrix_acked)}
          </Badge>
        }
      />
      <CardBody className="space-y-4">
        {risques === null && (
          <p className="text-xs text-amber-400">
            Matrice de risques de la synthèse non chargée — les libellés ne peuvent pas être
            réconciliés avec les index acquittés. Les index bruts sont affichés tels quels.
          </p>
        )}
        {risques !== null && !bijection && (
          <p className="text-xs text-amber-400">
            ⚠ {acks.length} acquittement(s) pour {risques.length} risque(s) dans la synthèse — la
            bijection n&apos;est pas respectée.
          </p>
        )}

        <Section title={`Risques acceptés (${acks.length})`}>
          <div className="space-y-2">
            {acks.length === 0 && <p className="text-sm text-gray-500">Aucun acquittement enregistré.</p>}
            {acks.map(a => {
              const r = risques && risques[a.risk_index]
              return (
                <div
                  key={a.risk_index}
                  className={`rounded-lg border px-3 py-2 ${
                    a.accepted ? 'border-emerald-900/60 bg-emerald-950/20' : 'border-red-900/60 bg-red-950/20'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span className={a.accepted ? 'text-emerald-400' : 'text-red-400'}>
                      {a.accepted ? '☑' : '☐'}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm text-gray-200">
                        {r ? r.risque : <span className="text-amber-400">risque #{a.risk_index} — libellé non résolu</span>}
                      </p>
                      {r && (
                        <p className="text-xs text-gray-500 mt-1">
                          impact {r.impact} · probabilité {r.probabilite} · réversible {String(r.reversible)}
                          {r.hypothese_liee ? ` · lié à ${r.hypothese_liee}` : ''}
                        </p>
                      )}
                      {r && r.reponse_si_materialise && (
                        <p className="text-xs text-gray-400 mt-1">
                          <span className="text-gray-600">Réponse si matérialisé : </span>
                          {r.reponse_si_materialise}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </Section>

        <Section title="Pre-mortem">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant={these.pre_mortem_acked ? 'emerald' : 'amber'}>
              pre_mortem_acked : {String(these.pre_mortem_acked)}
            </Badge>
          </div>
          {Array.isArray(preMortem) && preMortem.length > 0 ? (
            <ul className="space-y-2">
              {preMortem.map((s, i) => (
                <li key={i} className="text-sm text-gray-300 rounded-lg border border-gray-800 bg-gray-950/40 px-3 py-2">
                  {s}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">
              Scénarios de pre-mortem non disponibles depuis la synthèse.
            </p>
          )}
        </Section>
      </CardBody>
    </Card>
  )
}

// Faits d'exécution : ce qui s'est réellement passé sur le marché. Ce ne sont pas des
// jugements — d'où leur présence légitime en saisie utilisateur (G2).
function BlocPosition({ these }) {
  const p = these.position
  return (
    <Card>
      <CardHeader
        title="Exécution"
        subtitle="Faits de marché constatés — pas un jugement."
        action={p ? <Badge variant="emerald">position #{p.id}</Badge> : <Badge variant="gray">aucune position</Badge>}
      />
      <CardBody>
        {p ? (
          <Dl cols={4}>
            <KeyValue label="shares" value={fmtNum(p.shares) ?? <Val v={p.shares} />} />
            <KeyValue label="purchase_price_eur" value={fmtNum(p.purchase_price_eur) ?? <Val v={p.purchase_price_eur} />} note="EUR" />
            <KeyValue label="purchase_date" value={<Val v={p.purchase_date} />} />
            <KeyValue label="status" value={<Val v={p.status} />} />
          </Dl>
        ) : (
          <p className="text-sm text-gray-500">
            Aucune position ouverte pour cette thèse. La décision n&apos;a pas encore été exécutée.
          </p>
        )}
      </CardBody>
    </Card>
  )
}

export default function DecisionV2() {
  const router = useRouter()
  const { ticker_id } = router.query
  const [these, setThese] = useState(null)
  const [risques, setRisques] = useState(null)
  const [preMortem, setPreMortem] = useState(null)
  const [err, setErr] = useState(null)
  const [aucuneThese, setAucuneThese] = useState(false)

  const charger = useCallback(async () => {
    setErr(null); setThese(null); setAucuneThese(false); setRisques(null); setPreMortem(null)
    try {
      const rl = await fetch(`${API}/v2/theses?ticker_id=${encodeURIComponent(ticker_id)}`)
      if (!rl.ok) throw new Error(`HTTP ${rl.status} sur /v2/theses`)
      const liste = await rl.json()
      if (!Array.isArray(liste) || liste.length === 0) { setAucuneThese(true); return }

      // Plusieurs thèses possibles (draft puis active) : on prend la plus récente.
      const cible = liste.slice().sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))[0]

      const rd = await fetch(`${API}/v2/theses/${cible.id}`)
      if (!rd.ok) throw new Error(`HTTP ${rd.status} sur /v2/theses/${cible.id}`)
      const detail = await rd.json()
      setThese(detail)

      // La matrice de risques vit dans la synthèse, pas dans la thèse. Sans elle,
      // les risk_acks ne sont que des index — on charge donc l'analyse de synthèse.
      if (detail.synthesis_analysis_id) {
        const ra = await fetch(`${API}/analyses/${detail.synthesis_analysis_id}`)
        if (ra.ok) {
          const a = await ra.json()
          const rm = a && a.result_json ? a.result_json.risk_matrix : null
          if (rm) {
            setRisques(Array.isArray(rm.risques_acceptes) ? rm.risques_acceptes : null)
            setPreMortem(Array.isArray(rm.pre_mortem) ? rm.pre_mortem : null)
          }
        }
      }
    } catch (e) {
      setErr(String(e.message || e))
    }
  }, [ticker_id])

  useEffect(() => { if (ticker_id) charger() }, [ticker_id, charger])

  if (!ticker_id) return null

  const entete = (
    <div>
      <Link href={`/v2/tickers/${ticker_id}`} className="text-xs text-gray-500 hover:text-emerald-300">
        ← {ticker_id}
      </Link>
      <h1 className="text-xl font-bold text-white mt-1">Décision — {ticker_id}</h1>
      <p className="text-sm text-gray-500 mt-1">
        L&apos;acte de validation : ce que la synthèse a décidé (figé, en lecture seule) face à ce que
        l&apos;utilisateur acquitte et exécute.
      </p>
    </div>
  )

  if (err) return <div className="space-y-4">{entete}<ErrorState detail={err} /></div>

  if (aucuneThese) {
    return (
      <div className="space-y-4">
        {entete}
        <EmptyState
          title="Aucune thèse V2 pour ce ticker"
          description="La décision se prend à partir d'une synthèse « final ». Passe d'abord par l'écran Analyses."
        />
        <div className="flex justify-center">
          <Link
            href={`/v2/tickers/${ticker_id}/analyses`}
            className="px-3 py-1.5 text-xs text-gray-300 border border-gray-700 hover:border-emerald-600 rounded-lg"
          >
            Voir les analyses →
          </Link>
        </div>
      </div>
    )
  }

  if (!these) return <div className="space-y-4">{entete}<p className="text-sm text-gray-500">Chargement…</p></div>

  const estValidee = these.status !== 'draft'

  return (
    <div className="space-y-5">
      {entete}

      <div className="rounded-lg border border-gray-800 bg-gray-900/40 px-4 py-3 flex items-center gap-3 flex-wrap">
        <Badge variant={these.status || 'gray'}>thèse #{these.id} · {these.status}</Badge>
        {these.validated_at
          ? <span className="text-xs text-gray-400">validée le {new Date(these.validated_at).toLocaleString('fr-FR')}</span>
          : <span className="text-xs text-amber-400">non validée</span>}
        <span className="text-xs text-gray-600 ml-auto">
          créée le {new Date(these.created_at).toLocaleString('fr-FR')}
        </span>
      </div>

      {/* La validation est un POST irréversible (fige la décision ET ouvre la position).
          Cet écran est délibérément en lecture seule : il rend compte de la décision,
          il ne la déclenche pas. */}
      {!estValidee && (
        <div className="rounded-lg border border-amber-900/60 bg-amber-950/20 px-4 py-3">
          <p className="text-sm text-amber-300 font-medium">Thèse en brouillon — non validée</p>
          <p className="text-xs text-amber-200/70 mt-1">
            La validation fige la décision et ouvre la position en une seule opération irréversible.
            Elle ne se déclenche pas depuis cet écran de lecture.
          </p>
        </div>
      )}

      <BlocFige these={these} />
      <BlocAcquittements these={these} risques={risques} preMortem={preMortem} />
      <BlocPosition these={these} />

      <Card>
        <CardHeader
          title="Hypothèses de la thèse"
          action={<Badge variant="gray">{Array.isArray(these.hypotheses) ? these.hypotheses.length : 0}</Badge>}
        />
        <CardBody>
          {Array.isArray(these.hypotheses) && these.hypotheses.length > 0 ? (
            <div className="space-y-2">
              {these.hypotheses.map((h, i) => (
                <div key={h.id || i} className="rounded-lg border border-gray-800 bg-gray-950/40 px-3 py-2">
                  <div className="flex items-start gap-2 flex-wrap">
                    <Badge variant="gray">{h.id}</Badge>
                    <Badge variant={h.statut === 'active' ? 'emerald' : 'gray'}>{h.statut}</Badge>
                    <p className="text-sm text-gray-200 flex-1 min-w-[12rem]">{h.enonce}</p>
                  </div>
                  <p className="text-xs text-gray-500 mt-1.5">
                    KPI {h.kpi}
                    {h.unite ? ` (${h.unite})` : ''} · alerte {h.seuil_alerte} · invalidation {h.seuil_invalidation}
                    {h.horizon ? ` · horizon ${h.horizon}` : ''}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">Aucune hypothèse enregistrée.</p>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
