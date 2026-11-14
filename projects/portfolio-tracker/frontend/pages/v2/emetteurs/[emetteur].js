import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import { Card, CardHeader, CardBody, Badge, KeyValue, Dl, EmptyState, ErrorState } from '../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const INPUT = 'w-full rounded-lg bg-gray-950 border border-gray-700 px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-emerald-600'
const BTN = 'px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white disabled:opacity-50'

function detailDe(data, code) {
  const d = data && data.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map(x => x.msg).join(' ; ')
  return `Refusé (code ${code}).`
}

// « a | b » par ligne  <->  [[a, b], …]
function enLignes(paires) {
  return (paires || []).map(p => `${p[0]} | ${p[1]}`).join('\n')
}
function enPaires(texte) {
  return texte.split('\n').map(l => l.trim()).filter(Boolean).map(l => {
    const i = l.indexOf('|')
    return i === -1 ? [l, ''] : [l.slice(0, i).trim(), l.slice(i + 1).trim()]
  })
}

function Champ({ label, aide, children }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs text-gray-400">{label}</span>
      {children}
      {aide && <span className="block text-[11px] text-gray-600">{aide}</span>}
    </label>
  )
}

function Titre({ children }) {
  return <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">{children}</h2>
}

function ListeOuTiret({ items, rendu }) {
  if (!items || items.length === 0) return <span className="text-gray-500">—</span>
  return <ul className="space-y-0.5">{items.map(rendu)}</ul>
}

function FicheCard({ f }) {
  const genres = {}
  for (const l of f.lieux) (genres[l.genre] = genres[l.genre] || []).push(l.adresse)
  return (
    <Card>
      <CardHeader title={f.raison_sociale} subtitle={`Identifiant maison : ${f.emetteur}`}
        action={<Badge variant="emerald">révision n° {f.revision}</Badge>} />
      <CardBody>
        <Dl cols={2}>
          <KeyValue label="Pays" value={f.pays || '—'} />
          <KeyValue label="Spécialité" value={f.specialite || 'parcours généraliste'} />
          <KeyValue label="Cotations" value={
            <ListeOuTiret items={f.cotations} rendu={(c, i) => <li key={i}>{c.symbole} · {c.place}</li>} />} />
          <KeyValue label="Références externes" value={
            <ListeOuTiret items={f.references} rendu={(r, i) => <li key={i}>{r.registre} : {r.valeur}</li>} />} />
          <KeyValue label="Lieux de publication" value={
            Object.keys(genres).length === 0 ? '—' : (
              <ul className="space-y-0.5">
                {Object.keys(genres).map(g => (
                  <li key={g}><span className="text-gray-500">{g}</span> : {genres[g].join(', ')}</li>
                ))}
              </ul>
            )} />
          <KeyValue label="Établie le" value={`${f.le} par ${f.auteur}`} />
          <KeyValue label="Motif de cette révision" value={f.motif} />
        </Dl>
      </CardBody>
    </Card>
  )
}

function Corriger({ f, emetteur, onFait }) {
  const [raison, setRaison] = useState(f.raison_sociale)
  const [pays, setPays] = useState(f.pays)
  const [spec, setSpec] = useState(f.specialite)
  const [cot, setCot] = useState(enLignes(f.cotations.map(c => [c.place, c.symbole])))
  const [ref, setRef] = useState(enLignes(f.references.map(r => [r.registre, r.valeur])))
  const [lieux, setLieux] = useState(enLignes(f.lieux.map(l => [l.genre, l.adresse])))
  const [motif, setMotif] = useState('')
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  async function soumettre(e) {
    e.preventDefault()
    setBusy(true); setErr(null)
    try {
      const r = await fetch(`${API}/v2/emetteurs/${encodeURIComponent(emetteur)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          raison_sociale: raison, pays, specialite: spec, motif,
          cotations: enPaires(cot), references: enPaires(ref), lieux: enPaires(lieux),
        }),
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) { setErr(detailDe(data, r.status)); return }
      setMotif('')
      onFait(data)
    } catch (_) {
      setErr('Le serveur ne répond pas.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader title="Corriger la fiche"
        subtitle="Une correction ajoute une révision ; les précédentes restent lisibles plus bas." />
      <CardBody>
        <form onSubmit={soumettre} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Champ label="Raison sociale">
            <input className={INPUT} value={raison} onChange={e => setRaison(e.target.value)} required />
          </Champ>
          <Champ label="Pays" aide="Code à deux lettres majuscules, ou rien.">
            <input className={INPUT} value={pays} onChange={e => setPays(e.target.value)} />
          </Champ>
          <Champ label="Spécialité" aide="Vide : parcours généraliste.">
            <input className={INPUT} value={spec} onChange={e => setSpec(e.target.value)} />
          </Champ>
          <div />
          <Champ label="Cotations" aide="Une par ligne : place | symbole">
            <textarea className={INPUT} rows={3} value={cot} onChange={e => setCot(e.target.value)} />
          </Champ>
          <Champ label="Références externes" aide="Une par ligne : registre | valeur">
            <textarea className={INPUT} rows={3} value={ref} onChange={e => setRef(e.target.value)} />
          </Champ>
          <div className="sm:col-span-2">
            <Champ label="Lieux de publication" aide="Un par ligne : genre | domaine (ex. relations_investisseurs | exemple.example/investisseurs)">
              <textarea className={INPUT} rows={3} value={lieux} onChange={e => setLieux(e.target.value)} />
            </Champ>
          </div>
          <div className="sm:col-span-2">
            <Champ label="Motif de la correction (obligatoire)">
              <input className={INPUT} value={motif} onChange={e => setMotif(e.target.value)} required />
            </Champ>
          </div>
          <div className="sm:col-span-2 flex items-center gap-3">
            <button type="submit" className={BTN} disabled={busy}>Enregistrer la correction</button>
            {err && <span className="text-xs text-red-400">{err}</span>}
          </div>
        </form>
      </CardBody>
    </Card>
  )
}

function SourcesAdmises({ sources }) {
  return (
    <section className="space-y-3">
      <Titre>Sources admises pour cet émetteur</Titre>
      {sources.length === 0 ? (
        <EmptyState title="Aucune source admise" description="Seuls ses propres lieux de publication comptent pour l'instant." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-800">
          <table className="w-full text-xs">
            <thead className="bg-gray-900 text-gray-400">
              <tr>{['Source', 'Portée', 'Natures', 'Niveau', 'Date', 'Auteur', 'Critère', 'Motif'].map(h =>
                <th key={h} className="py-2 px-3 text-left font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {sources.map(s => (
                <tr key={s.rang} className="border-t border-gray-800 align-top">
                  <td className="py-2 px-3 font-mono text-gray-200">{s.source}</td>
                  <td className="py-2 px-3 text-gray-400">{s.portee}</td>
                  <td className="py-2 px-3 text-gray-400">{s.natures.join(', ')}</td>
                  <td className="py-2 px-3 text-gray-300">{s.niveau}</td>
                  <td className="py-2 px-3 text-gray-400 whitespace-nowrap">{s.le}</td>
                  <td className="py-2 px-3 text-gray-400">{s.auteur}</td>
                  <td className="py-2 px-3 text-gray-400">{s.critere || '—'}</td>
                  <td className="py-2 px-3 text-gray-400">{s.motif}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function SourcesRevoquees({ revocations }) {
  if (!revocations.length) return null
  return (
    <section className="space-y-3">
      <Titre>Sources révoquées</Titre>
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-xs">
          <thead className="bg-gray-900 text-gray-400">
            <tr>{['Source', 'Portée', 'Natures retirées', 'Date', 'Auteur', 'Motif'].map(h =>
              <th key={h} className="py-2 px-3 text-left font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {revocations.map(s => (
              <tr key={s.rang} className="border-t border-gray-800 align-top">
                <td className="py-2 px-3 font-mono text-gray-200">{s.source}</td>
                <td className="py-2 px-3 text-gray-400">{s.portee}</td>
                <td className="py-2 px-3 text-gray-400">{(s.natures || []).join(', ') || '—'}</td>
                <td className="py-2 px-3 text-gray-400 whitespace-nowrap">{s.le}</td>
                <td className="py-2 px-3 text-gray-400">{s.auteur}</td>
                <td className="py-2 px-3 text-gray-400">{s.motif}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Revisions({ revisions }) {
  const precedentes = revisions.slice(0, -1).reverse()
  return (
    <section className="space-y-3">
      <Titre>Révisions précédentes</Titre>
      {precedentes.length === 0 ? (
        <p className="text-sm text-gray-500">La fiche n'a jamais été corrigée.</p>
      ) : (
        <div className="space-y-2">
          {precedentes.map(r => (
            <details key={r.revision} className="rounded-xl border border-gray-800 bg-gray-900/50">
              <summary className="px-4 py-2 text-sm text-gray-300 cursor-pointer">
                Révision n° {r.revision} · {r.le} · {r.auteur} — {r.motif}
              </summary>
              <div className="px-4 pb-3 text-xs text-gray-400 space-y-1">
                <p>Raison sociale : {r.raison_sociale} · Pays : {r.pays || '—'} · Spécialité : {r.specialite || 'généraliste'}</p>
                <p>Cotations : {r.cotations.map(c => `${c[1]} (${c[0]})`).join(', ') || '—'}</p>
                <p>Références : {r.references.map(x => `${x[0]} : ${x[1]}`).join(', ') || '—'}</p>
                <p>Lieux : {r.lieux.map(l => `${l[0]} : ${l[1]}`).join(', ') || '—'}</p>
              </div>
            </details>
          ))}
        </div>
      )}
    </section>
  )
}

function TesterAdresse({ emetteur, natures }) {
  const [adresse, setAdresse] = useState('')
  const [nature, setNature] = useState('')
  const [res, setRes] = useState(null)
  const [err, setErr] = useState(null)

  async function tester(e) {
    e.preventDefault()
    setRes(null); setErr(null)
    const q = new URLSearchParams({ adresse, nature: nature || natures[0] })
    try {
      const r = await fetch(`${API}/v2/emetteurs/${encodeURIComponent(emetteur)}/qualification?${q}`)
      const data = await r.json().catch(() => ({}))
      if (!r.ok) { setErr(detailDe(data, r.status)); return }
      setRes(data)
    } catch (_) {
      setErr('Le serveur ne répond pas.')
    }
  }

  return (
    <Card>
      <CardHeader title="Tester une adresse" subtitle="Cette adresse est-elle une source admise pour cet émetteur ?" />
      <CardBody>
        <form onSubmit={tester} className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div className="sm:col-span-2">
            <Champ label="Adresse">
              <input className={INPUT} value={adresse} onChange={e => setAdresse(e.target.value)} required />
            </Champ>
          </div>
          <Champ label="Nature d'information">
            <select className={INPUT} value={nature || natures[0] || ''} onChange={e => setNature(e.target.value)}>
              {natures.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </Champ>
          <div className="sm:col-span-3"><button type="submit" className={BTN}>Tester</button></div>
        </form>
        {err && <p className="text-xs text-red-400 mt-3">{err}</p>}
        {res && (
          <div className="mt-3 text-sm space-y-1">
            <p>
              <Badge variant={res.admise ? 'emerald' : 'red'}>{res.admise ? 'admise' : 'non admise'}</Badge>
              <span className="ml-2 text-gray-300">niveau {res.niveau}{res.source ? ` · source ${res.source}` : ''}</span>
            </p>
            <p className="text-gray-400">{res.motif}</p>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

function EtatDossier({ emetteur }) {
  const [etat, setEtat] = useState(undefined) // undefined : en cours ; null : indisponible

  useEffect(() => {
    setEtat(undefined)
    fetch(`${API}/v2/emetteurs/${encodeURIComponent(emetteur)}/dossier`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(setEtat)
      .catch(() => setEtat(null))
  }, [emetteur])

  const usd = v => `${Number(v || 0).toFixed(2)} $`
  return (
    <section className="space-y-3">
      <Titre>État du dossier</Titre>
      {etat === undefined && <p className="text-sm text-gray-500">Chargement…</p>}
      {etat === null && <p className="text-sm text-gray-500">État indisponible.</p>}
      {etat && (
        <Card>
          <CardBody>
            <Dl cols={2}>
              <KeyValue label="Pas faits" value={etat.faits.length ? etat.faits.join(', ') : 'aucun'} />
              <KeyValue label="Dépense"
                value={`${usd(etat.depense.modeles_usd + etat.depense.web_usd)} (modèles ${usd(etat.depense.modeles_usd)}, recherches ${usd(etat.depense.web_usd)})`} />
              <KeyValue label="Arrêt en cours" value={
                etat.arret ? (
                  <span>
                    <Badge variant="amber">à l'arrêt</Badge>{' '}
                    {etat.arret.motif}
                    {etat.arret.acte && <span className="block text-gray-400 mt-1">Acte attendu : {etat.arret.acte}</span>}
                  </span>
                ) : 'aucun'} />
            </Dl>
          </CardBody>
        </Card>
      )}
    </section>
  )
}

export default function FicheEmetteur() {
  const router = useRouter()
  const emetteur = router.query.emetteur
  const [vue, setVue] = useState(null)
  const [err, setErr] = useState(null)

  const charger = useCallback(() => {
    if (!emetteur) return
    fetch(`${API}/v2/emetteurs/${encodeURIComponent(emetteur)}`)
      .then(async r => {
        const data = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(detailDe(data, r.status))
        return data
      })
      .then(d => { setVue(d); setErr(null) })
      .catch(e => setErr(e.message))
  }, [emetteur])

  useEffect(() => { charger() }, [charger])

  return (
    <div className="space-y-6">
      <div>
        <Link href="/v2/emetteurs" className="text-xs text-gray-500 hover:text-gray-300">← Émetteurs et sources</Link>
        <h1 className="text-xl font-bold text-white mt-1">Fiche de l&apos;émetteur</h1>
      </div>

      {err && <ErrorState detail={err} />}
      {!err && !vue && <p className="text-sm text-gray-500">Chargement…</p>}

      {vue && (
        <>
          <FicheCard f={vue.fiche} />
          {/* key : le formulaire repart des valeurs de la révision en vigueur après chaque correction */}
          <Corriger key={vue.fiche.revision} f={vue.fiche} emetteur={emetteur} onFait={setVue} />
          <SourcesAdmises sources={vue.fiche.sources} />
          <SourcesRevoquees revocations={vue.fiche.revocations} />
          <Revisions revisions={vue.revisions} />
          <TesterAdresse emetteur={emetteur} natures={vue.referentiel.natures} />
          <EtatDossier emetteur={emetteur} />
        </>
      )}
    </div>
  )
}
