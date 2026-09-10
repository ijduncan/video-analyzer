import { useMemo } from 'react'
import './SearchHighlight.css'

// Keep word-boundary rules aligned with library_service._term_pattern.
const exactTerms = new Set(('red tan blue gold golden rose pink orange yellow black white gray grey green purple brown cyan magenta amber beige teal maroon violet lime navy aqua aquamarine azure burgundy bronze charcoal copper coral cream crimson emerald fuchsia indigo ivory khaki lavender lilac mauve mint mustard ochre olive peach plum salmon scarlet silver taupe turquoise ecu mcu ots pov els reviewed unreviewed needs_review').split(' '))

export function SearchHighlight({ text, query = '' }: { text: string; query?: string }) {
  const pattern = useMemo(() => {
    const terms = [...new Set(query.toLowerCase().match(/[\p{L}\p{N}_]+/gu) || [])].sort((a, b) => b.length - a.length)
    if (!terms.length) return null
    return new RegExp(terms.map(term => term.length <= 2 || exactTerms.has(term)
      ? `(?<![\\p{L}\\p{N}_])${term}(?![\\p{L}\\p{N}_])`
      : term).join('|'), 'giu')
  }, [query])
  if (!pattern) return <>{text}</>
  const parts = []
  let end = 0
  for (const match of text.matchAll(pattern)) {
    parts.push(text.slice(end, match.index))
    parts.push(<mark className="lw-search-highlight" key={match.index}>{match[0]}</mark>)
    end = match.index + match[0].length
  }
  parts.push(text.slice(end))
  return <>{parts}</>
}
