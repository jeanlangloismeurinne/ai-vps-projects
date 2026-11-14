import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { Card, CardHeader, CardBody, Badge, EmptyState, ErrorState } from '../../../components/v2'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8050'

const INPUT = 'w-full rounded-lg bg-gray-950 border border-gray-700 px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-emerald-600'
const BTN = 'px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white disabled:opacity-50'

// Un appel qui écrit : rend { ok, data } ou { ok:false, detail } — le refus du registre est dit tel quel.
async function envoyer(url, methode, corps) {
  try {
    const r = await fetch(`${API}${url}`, {
      method: methode, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps),
    })
    const data = await r.json().catch(() => ({}))
    if (r.ok) return { ok: true, data }
    const d = data.detail
    const detail = typeof d === 'string' ? d : Array.isArray(d)
      ? d.map(x => x.msg).join(' ; ') : `Refusé (code ${r.status}).`
    return { ok: false, detail }
  } catch (e) {
    return { ok: false, detail: 'Le serveur ne répond pas.' }
  }
}

function Champ({ label, children }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs text-gray-400">{label}</span>
      {children}
    </label>
  )
}

function AjouterEmetteur({ onFait }) {
  const [id, setId] = useState('')
  const [raison, setRaison] = useState('')
  const [motif, setMotif] = useState('')
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  async function soumettre(e) {
    e.preventDefault()
    setBusy(true); setErr(null)
    const r = await envoyer(`/v2/emetteurs/${encodeURIComponent(id.trim())}`, 'PUT',
      { raison_sociale: raison, motif })
    setBusy(false)
    if (!r.ok) { setErr(r.detail); return }
    setId(''); setRaison(''); setMotif('')
    onFait()
  }

  return (
    <Card>
      <CardHeader title="Ajouter un émetteur" subtitle="Une fiche minimale : le reste se complète ensuite sur la fiche." />
      <CardBody>
        <form onSubmit={soumettre} className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Champ label="Identifiant maison">
            <input className={INPUT} value={id} onChange={e => setId(e.target.value)} required />
          </Champ>
          <Champ label="Raison sociale">
            <input className={INPUT} value={raison} onChange={e => setRaison(e.target.value)} required />
          </Champ>
          <Champ label="Motif">
            <input className={INPUT} value={motif} onChange={e => setMotif(e.target.value)} required />
          </Champ>
          <div className="sm:col-span-3 flex items-center gap-3">
            <button type="submit" className={BTN} disabled={busy}>Établir la fiche</button>
            {err && <span className="text-xs text-red-400">{err}</span>}
          </div>
        </form>
      </CardBody>
    </Card>
  )
}

function AdmettreSource({ referentiel, onFait }) {
  const natures = referentiel?.natures || []
  const niveaux = referentiel?.niveaux || []
  const [source, setSource] = useState('')
  const [portee, setPortee] = useState('generale')
  const [choisies, setChoisies] = useState([])
  const [niveau, setNiveau] = useState('')
  const [motif, setMotif] = useState('')
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  function basculer(n) {
    setChoisies(c => c.includes(n) ? c.filter(x => x !== n) : [...c, n])
  }

  async function soumettre(e) {
    e.preventDefault()
    setBusy(true); setErr(null)
    const r = await envoyer('/v2/sources/admettre', 'POST',
      { source: source.trim(), portee: portee.trim(), natures: choisies, niveau: niveau || niveaux[0], motif })
    setBusy(false)
    if (!r.ok) { setErr(r.detail); return }
    setSource(''); setChoisies([]); setMotif('')
    onFait()
  }

  return (
    <Card>
      <CardHeader title="Admettre une source"
        subtitle="Une source vaut pour des natures d'information nommées, jamais pour elle tout entière." />
      <CardBody>
        <form onSubmit={soumettre} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Champ label="Domaine (sans « https:// »)">
            <input className={INPUT} value={source} onChange={e => setSource(e.target.value)} required />
          </Champ>
          <Champ label="Portée : generale, specialite:<nom> ou emetteur:<identifiant>">
            <input className={INPUT} value={portee} onChange={e => setPortee(e.target.value)} required />
          </Champ>
          <div className="space-y-1">
            <span className="text-xs text-gray-400">Natures d'information</span>
            <div className="flex flex-wrap gap-4 pt-1">
              {natures.map(n => (
                <label key={n} className="flex items-center gap-1.5 text-sm text-gray-300">
                  <input type="checkbox" className="accent-emerald-600"
                    checked={choisies.includes(n)} onChange={() => basculer(n)} />
                  {n}
                </label>
              ))}
            </div>
          </div>
          <Champ label="Niveau">
            <select className={INPUT} value={niveau || niveaux[0] || ''} onChange={e => setNiveau(e.target.value)}>
              {niveaux.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </Champ>
          <div className="sm:col-span-2">
            <Champ label="Motif">
              <input className={INPUT} value={motif} onChange={e => setMotif(e.target.value)} required />
            </Champ>
          </div>
          <div className="sm:col-span-2 flex items-center gap-3">
            <button type="submit" className={BTN} disabled={busy || choisies.length === 0}>Admettre</button>
            {err && <span className="text-xs text-red-400">{err}</span>}
          </div>
        </form>
      </CardBody>
    </Card>
  )
}

function Criteres({ criteres }) {
  const noms = Object.keys(criteres || {})
  return (
    <details className="rounded-xl border border-gray-800 bg-gray-900/50">
      <summary className="px-4 py-3 text-sm font-semibold text-gray-300 cursor-pointer">
        Critères écrits pour admettre une source ({noms.length})
      </summary>
      <div className="px-4 pb-4 space-y-3">
        {noms.map(nom => {
          const c = criteres[nom]
          return (
            <div key={nom} className="border-t border-gray-800 pt-3">
              <p className="text-sm text-gray-200 font-mono">{nom}</p>
              <p className="text-xs text-gray-400 mt-1">{c.texte}</p>
              <p className="text-xs text-gray-500 mt-1">
                Niveau plafond : {c.niveau_max} · Natures : {(c.natures || []).join(', ')}
              </p>
            </div>
          )
        })}
      </div>
    </details>
  )
}

function Journal({ actes, onFait }) {
  const [err, setErr] = useState(null)

  async function revoquer(a) {
    const motif = window.prompt(`Motif de la révocation de ${a.source} (${a.portee}) :`)
    if (!motif || !motif.trim()) return
    setErr(null)
    const r = await envoyer('/v2/sources/revoquer', 'POST', { source: a.source, portee: a.portee, motif })
    if (!r.ok) { setErr(r.detail); return }
    onFait()
  }

  if (!actes.length) {
    return <EmptyState title="Aucune source admise" description="Le journal se remplit à chaque admission ou révocation." />
  }
  return (
    <div className="space-y-2">
      {err && <ErrorState detail={err} />}
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-xs">
          <thead className="bg-gray-900 text-gray-400">
            <tr>
              {['Rang', 'Date', 'Acte', 'Source', 'Portée', 'Natures', 'Niveau', 'Auteur', 'Critère', 'Motif', ''].map(h => (
                <th key={h} className="py-2 px-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {actes.map(a => (
              <tr key={a.rang} className="border-t border-gray-800 align-top">
                <td className="py-2 px-3 text-gray-400">{a.rang}</td>
                <td className="py-2 px-3 text-gray-400 whitespace-nowrap">{a.le}</td>
                <td className="py-2 px-3">
                  {a.acte === 'admettre'
                    ? <Badge variant={a.en_vigueur ? 'emerald' : 'gray'}>{a.en_vigueur ? 'admission en vigueur' : 'admission'}</Badge>
                    : <Badge variant="red">révocation</Badge>}
                </td>
                <td className="py-2 px-3 font-mono text-gray-200">{a.source}</td>
                <td className="py-2 px-3 text-gray-400">{a.portee}</td>
                <td className="py-2 px-3 text-gray-400">{(a.natures || []).join(', ') || '—'}</td>
                <td className="py-2 px-3 text-gray-300">{a.niveau || '—'}</td>
                <td className="py-2 px-3 text-gray-400">{a.auteur}</td>
                <td className="py-2 px-3 text-gray-400">{a.critere || '—'}</td>
                <td className="py-2 px-3 text-gray-400">{a.motif}</td>
                <td className="py-2 px-3">
                  {a.en_vigueur && (
                    <button className="text-red-400 hover:text-red-300 underline" onClick={() => revoquer(a)}>Révoquer</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function EmetteursV2() {
  const [vue, setVue] = useState(null)
  const [err, setErr] = useState(null)

  const charger = useCallback(() => {
    fetch(`${API}/v2/emetteurs`)
      .then(r => r.ok ? r.json() : Promise.reject(`code ${r.status}`))
      .then(d => { setVue(d); setErr(null) })
      .catch(e => setErr(String(e)))
  }, [])

  useEffect(() => { charger() }, [charger])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Émetteurs et sources</h1>
        <p className="text-sm text-gray-500 mt-1">
          Une fiche par société (qui elle est, où elle publie, sa spécialité) et le journal des sources
          que la maison tient pour fiables. Chaque acte est daté, motivé et signé.
        </p>
      </div>

      {err && <ErrorState detail={`Chargement impossible (${err}).`} />}
      {!err && !vue && <p className="text-sm text-gray-500">Chargement…</p>}

      {vue && (
        <>
          <Section2 titre="Émetteurs">
            {vue.emetteurs.length === 0 ? (
              <EmptyState title="Aucun émetteur" description="Ajoute le premier avec le formulaire ci-dessous." />
            ) : (
              <div className="overflow-x-auto rounded-xl border border-gray-800">
                <table className="w-full text-sm">
                  <thead className="bg-gray-900 text-xs text-gray-400">
                    <tr>
                      {['Identifiant', 'Raison sociale', 'Spécialité', 'Révision', 'Date'].map(h => (
                        <th key={h} className="py-2 px-3 text-left font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {vue.emetteurs.map(e => (
                      <tr key={e.emetteur} className="border-t border-gray-800">
                        <td className="py-2 px-3">
                          <Link href={`/v2/emetteurs/${encodeURIComponent(e.emetteur)}`}
                            className="font-mono text-emerald-400 hover:text-emerald-300">{e.emetteur}</Link>
                        </td>
                        <td className="py-2 px-3 text-gray-200">{e.raison_sociale}</td>
                        <td className="py-2 px-3 text-gray-400">{e.specialite || 'généraliste'}</td>
                        <td className="py-2 px-3 text-gray-400">n° {e.revision}</td>
                        <td className="py-2 px-3 text-gray-400">{e.le}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section2>

          <AjouterEmetteur onFait={charger} />

          <Section2 titre="Journal des sources">
            <Journal actes={vue.journal_des_sources} onFait={charger} />
          </Section2>

          <AdmettreSource referentiel={vue.referentiel} onFait={charger} />
          <Criteres criteres={vue.referentiel?.criteres} />
        </>
      )}
    </div>
  )
}

function Section2({ titre, children }) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">{titre}</h2>
      {children}
    </section>
  )
}
