/**
 * NIVEAU 1 du parcours du comité — la page d'un titre répond d'abord à « peut-on décider ? »
 * (arbitrage du comité n°3, 2026-09-25). Ordre imposé : l'ALERTE en tête (ce qui manque et pourquoi),
 * puis la note de qualité de chaque méthodologie, puis leurs conclusions (la note de comité).
 * Tout vient de `GET /v2/tickers/:id/dossier`, recalculé à chaque lecture.
 */
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardHeader, CardBody, Badge, ErrorState } from './index'
import { API, ManqueBloc, ScoreQualite, StatutBadge } from './parcours'

function Alerte({ d }) {
  const p = d.peut_on_decider
  if (p.etat === 'dossier_complet') {
    return (
      <div className="rounded-xl border border-emerald-800 bg-emerald-950/30 px-4 py-3">
        <p className="text-sm font-semibold text-emerald-200">Peut-on décider ? Oui — le dossier est complet.</p>
        <p className="text-xs text-emerald-300/80 mt-0.5">{p.motif}</p>
      </div>
    )
  }
  if (p.etat === 'non_revalidable') {
    return (
      <div className="rounded-xl border border-gray-700 bg-gray-900/60 px-4 py-3">
        <p className="text-sm font-semibold text-gray-200">Peut-on décider ? On ne peut pas le dire.</p>
        <p className="text-xs text-gray-400 mt-0.5">{p.motif}</p>
      </div>
    )
  }
  return (
    <div className="rounded-xl border border-amber-700 bg-amber-950/20 overflow-hidden">
      <div className="px-4 py-3 border-b border-amber-900/60">
        <p className="text-sm font-semibold text-amber-200">
          ⚠ Peut-on décider ? Pas encore — le dossier est incomplet.
        </p>
        <p className="text-xs text-amber-300/80 mt-0.5">{p.motif}</p>
      </div>
      <div className="px-4 py-3 space-y-2">
        {p.manques.map(m => (
          <ManqueBloc key={`${m.framework_id}.${m.question_id}`} m={m} tickerId={d.ticker_id} />
        ))}
      </div>
    </div>
  )
}

function NotesQualite({ d }) {
  return (
    <Card>
      <CardHeader
        title="Note de qualité par méthodologie"
        subtitle="Part des questions applicables qui ont une réponse fondée et à jour. La solidité des sources est affichée à côté, jamais fondue dans la note."
      />
      <CardBody className="space-y-2">
        {d.frameworks.map(s => (
          <Link key={s.framework_id} href={`/v2/tickers/${d.ticker_id}/frameworks/${s.framework_id}`}
                className="flex items-center justify-between gap-4 rounded-lg border border-gray-800 px-4 py-3 hover:border-gray-600">
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-100">{s.libelle}</p>
              <p className="text-xs text-gray-500 mt-0.5">
                {s.n_applicables === null
                  ? `${s.n_questions} questions — applicabilité inconnue (société non classée)`
                  : `${s.n_applicables} question(s) applicable(s) sur ${s.n_questions}`}
                {s.n_manques > 0 && <span className="text-amber-300"> · {s.n_manques} manque(s)</span>}
                {s.n_renvoyees > 0 && <span className="text-red-300"> · {s.n_renvoyees} renvoyée(s)</span>}
              </p>
            </div>
            <div className="flex items-center gap-4 shrink-0">
              <div className="text-right">
                <p className="text-[10px] uppercase tracking-wide text-gray-500">qualité</p>
                <ScoreQualite qualite={s.qualite} />
              </div>
              <div className="text-right">
                <p className="text-[10px] uppercase tracking-wide text-gray-500">sources (rang moyen)</p>
                <p className="text-sm text-gray-200">{s.qualite?.rang_moyen ?? '—'}</p>
              </div>
            </div>
          </Link>
        ))}
      </CardBody>
    </Card>
  )
}

function Conclusions({ d }) {
  return (
    <Card>
      <CardHeader
        title="Conclusions des méthodologies"
        subtitle="La note de comité : seules les réponses passées au contrôle y figurent. Aucune opinion n'y est ajoutée."
      />
      <CardBody className="space-y-4">
        {d.memo.rubriques.filter(r => r.framework_id).map(r => (
          <div key={r.bloc} className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-semibold text-gray-200">{r.libelle}</p>
              <span className="text-xs text-gray-500">{r.motif}</span>
            </div>
            {r.points.map(pt => (
              <Link key={`${pt.question_id}.${pt.answer.analyste}`}
                    href={`/v2/tickers/${d.ticker_id}/frameworks/${r.framework_id}/q/${pt.question_id}`}
                    className="block rounded-lg border border-gray-800 px-3 py-2 hover:border-gray-600">
                <div className="flex items-center gap-2 flex-wrap">
                  <StatutBadge statut={pt.answer.statut} />
                  <span className="text-xs text-gray-400">{pt.enonce}</span>
                </div>
                <p className="text-sm text-gray-200 mt-1">
                  {pt.answer.reponse?.verbatim || pt.answer.sans_objet?.motif || pt.answer.gap?.manque}
                </p>
              </Link>
            ))}
          </div>
        ))}
      </CardBody>
    </Card>
  )
}

export default function DossierComite({ tickerId }) {
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => {
    if (!tickerId) return
    setD(null); setErr(null)
    fetch(`${API}/v2/tickers/${tickerId}/dossier`)
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(setD)
      .catch(e => setErr(String(e)))
  }, [tickerId])

  if (err) return <ErrorState detail={`Le dossier du comité n'a pas pu être dressé (${err}).`} />
  if (!d) return <p className="text-sm text-gray-500">Dossier du comité en cours de recalcul…</p>
  return (
    <div className="space-y-4" data-testid="dossier-comite">
      <Alerte d={d} />
      <NotesQualite d={d} />
      <Conclusions d={d} />
      <p className="text-[11px] text-gray-600">
        Recalculé à la lecture le {new Date(d.genere_le).toLocaleString('fr-FR')}
        {d.archetype && <> · profil de la société : <Badge variant="gray">{d.archetype.replaceAll('_', ' ')}</Badge></>}
      </p>
    </div>
  )
}
