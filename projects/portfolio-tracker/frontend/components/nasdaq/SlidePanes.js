import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useRouter } from 'next/router'

// Deux volets côte à côte ; ouvrir une fiche fait glisser le volet principal vers la gauche, sans le démonter :
// il garde donc exactement sa position de défilement. La fiche ouverte vit dans l'URL (?t=) : le retour du
// navigateur referme la fiche au lieu de quitter la page.
export function useSelectedTicker() {
  const router = useRouter()
  const pushed = useRef(false)
  const raw = router.query.t
  const selected = typeof raw === 'string' && raw ? raw.toUpperCase() : null
  const open = (t) => {
    pushed.current = true
    router.push({ pathname: router.pathname, query: { ...router.query, t } }, undefined, { shallow: true, scroll: false })
  }
  const close = () => {
    if (pushed.current) { pushed.current = false; router.back() } else {
      const { t, ...rest } = router.query
      router.replace({ pathname: router.pathname, query: rest }, undefined, { shallow: true, scroll: false })
    }
  }
  return [selected, open, close]
}

export default function SlidePanes({ selected, main, detail }) {
  const box = useRef(null)
  const [height, setHeight] = useState(null)
  const [last, setLast] = useState(selected)
  useEffect(() => { if (selected) setLast(selected) }, [selected])
  useLayoutEffect(() => {
    const fit = () => box.current && setHeight(Math.max(320, window.innerHeight - box.current.getBoundingClientRect().top - 8))
    fit()
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
  }, [])
  return (
    <div ref={box} className="overflow-hidden" style={{ height: height || '85vh' }}>
      <div className="flex h-full w-[200%] transition-transform duration-300 ease-in-out"
        style={{ transform: selected ? 'translateX(-50%)' : 'translateX(0)' }}>
        <div className="w-1/2 h-full overflow-y-auto pr-2" aria-hidden={!!selected} inert={selected ? '' : undefined}>{main}</div>
        <div className="w-1/2 h-full overflow-y-auto pl-2" aria-hidden={!selected}>{last ? detail(last) : null}</div>
      </div>
    </div>
  )
}
