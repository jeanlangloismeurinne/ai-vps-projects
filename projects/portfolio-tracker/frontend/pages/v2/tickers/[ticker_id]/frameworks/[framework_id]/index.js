/**
 * NIVEAU 2 du parcours du comité — une méthodologie : ses questions, le statut de chacune, l'avis du
 * contrôle et ses quatre vérifications. `GET /v2/tickers/:id/frameworks/:fid`, recalculé à la lecture.
 * Un niveau peut RÉSUMER, jamais ARRONDIR : une approximation reste « approximé ~ ».
 */
import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import { Card, CardHeader, CardBody, Badge, ErrorState } from '../../../../../../components/v2'
import {
  API, CONTROLES, ActualiteBadge, ComiteBadge, EtatControle, ManqueBloc, ScoreQualite, StatutBadge,
} from '../../../../../../components/v2/parcours'

function LigneQuestion({ lq, tickerId, frameworkId }) {
  const inapplicable = lq.applicable === false
  return (
    <div className={`rounded-lg border px-4 py-3 space-y-2 ${
      inapplicable ? 'border-gray-900 bg-gray-950/30' : 'border-gray-800 bg-gray-900/30'}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <Link href={`/v2/tickers/${tickerId}/frameworks/${frameworkId}/q/${lq.question_id}`}
              className="text-sm text-gray-100 hover:underline min-w-0">
          <span className="text-xs text-gray-500 mr-2 font-mono">{lq.question_id}</span>{lq.enonce}
        </Link>
        <div className="flex gap-1.5 shrink-0">
          {inapplicable && <Badge variant="gray">ne s'applique pas à cette société</Badge>}
          {lq.dispensee && <Badge variant="gray">dispensée par le comité</Badge>}
          <ComiteBadge pos={lq.comite} />
          {lq.applicable === null && <Badge variant="gray">applicabilité inconnue</Badge>}
        </div>
      </div>
      {lq.reponses.length === 0 && !inapplicable && (
        <p className="text-xs text-amber-300">Aucune réponse au dossier.</p>
      )}
      {lq.reponses.map(r => (
        <div key={r.answer_id} className="flex items-center gap-3 flex-wrap text-xs">
          <StatutBadge statut={r.statut} />
          {r.rang_derive && <span className="text-gray-400">rang {r.rang_derive}</span>}
          <ActualiteBadge actualite={r.actualite} />
          <span className="text-gray-600">·</span>
          {r.verdict === 'acquitte' && <Badge variant="emerald">acquittée par le contrôle</Badge>}
          {r.verdict === 'renvoye' && <Badge variant="red">renvoyée par le contrôle</Badge>}
          {r.verdict === null && <Badge variant="gray">non relue (société non classée)</Badge>}
          {r.controles && (
            <span className="flex gap-3 text-gray-500">
              {CONTROLES.map(([k, label]) => (
                <span key={k} title={label}>{label.slice(0, 1)} <EtatControle etat={r.controles[k]} /></span>
              ))}
            </span>
          )}
          <span className="text-gray-600">analyste {r.analyste}</span>
        </div>
      ))}
      {lq.manque && <ManqueBloc m={lq.manque} tickerId={tickerId} lien={false} />}
    </div>
  )
}

export default function FrameworkNiveau2() {
  const router = useRouter()
  const { ticker_id, framework_id } = router.query
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    if (!ticker_id || !framework_id) return
    setD(null); setErr(null)
    fetch(`${API}/v2/tickers/${ticker_id}/frameworks/${framework_id}`)
      .then(r => r.ok ? r.json() : r.json().then(j => Promise.reject(j.detail || `HTTP ${r.status}`)))
      .then(setD)
      .catch(e => setErr(String(e)))
  }, [ticker_id, framework_id])

  if (err) return <ErrorState detail={err} />
  if (!d) return <p className="text-sm text-gray-500">Recalcul de la méthodologie…</p>
  const s = d.synthese
  const applicables = d.questions.filter(q => q.applicable !== false)
  const horsObjet = d.questions.filter(q => q.applicable === false)

  return (
    <div className="space-y-5" data-testid="niveau-2">
      <div>
        <Link href={`/v2/tickers/${d.ticker_id}`} className="text-xs text-gray-500 hover:text-emerald-300">
          ← {d.ticker_id} · peut-on décider ?
        </Link>
        <h1 className="text-xl font-bold text-white mt-1">{s.libelle}</h1>
        <p className="text-xs text-gray-500 mt-1 max-w-3xl">{s.methodologie}</p>
      </div>

      <Card>
        <CardHeader title="Note de qualité" subtitle={`Référentiel ${s.framework_version}`} />
        <CardBody className="flex gap-8 flex-wrap">
          <div><p className="text-[10px] uppercase text-gray-500">qualité</p><ScoreQualite qualite={s.qualite} /></div>
          <div><p className="text-[10px] uppercase text-gray-500">sources (rang moyen)</p>
            <p className="text-sm text-gray-200">{s.qualite?.rang_moyen ?? '—'}</p></div>
          <div><p className="text-[10px] uppercase text-gray-500">applicables</p>
            <p className="text-sm text-gray-200">{s.n_applicables ?? '?'} / {s.n_questions}</p></div>
          <div><p className="text-[10px] uppercase text-gray-500">acquittées · renvoyées</p>
            <p className="text-sm text-gray-200">{s.n_acquittees} · {s.n_renvoyees}</p></div>
          <div><p className="text-[10px] uppercase text-gray-500">acceptées par le comité</p>
            <p className="text-sm text-gray-200">{s.n_acceptees_comite}</p></div>
          <div><p className="text-[10px] uppercase text-gray-500">manques</p>
            <p className={`text-sm ${s.n_manques ? 'text-amber-300' : 'text-gray-200'}`}>{s.n_manques}</p></div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Les questions qui s'appliquent" subtitle="Cliquer une question pour voir la preuve." />
        <CardBody className="space-y-2">
          {applicables.map(lq => (
            <LigneQuestion key={lq.question_id} lq={lq} tickerId={d.ticker_id} frameworkId={s.framework_id} />
          ))}
        </CardBody>
      </Card>

      {horsObjet.length > 0 && (
        <Card>
          <CardHeader title="Questions sans objet pour cette société"
                      subtitle="Sorties de la note de qualité : elles ne la font pas baisser." />
          <CardBody className="space-y-2">
            {horsObjet.map(lq => (
              <LigneQuestion key={lq.question_id} lq={lq} tickerId={d.ticker_id} frameworkId={s.framework_id} />
            ))}
          </CardBody>
        </Card>
      )}
    </div>
  )
}
