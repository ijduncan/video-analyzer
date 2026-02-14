import { useComparisonStore } from '../stores/comparisonStore'

const SECTIONS: { key: string; label: string; icon: string }[] = [
  { key: 'pacing_comparison', label: 'Pacing & Editing', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
  { key: 'visual_comparison', label: 'Visual Style', icon: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z' },
  { key: 'audio_comparison', label: 'Audio', icon: 'M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3' },
  { key: 'production_comparison', label: 'Production Value', icon: 'M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2m-2 0H9m8 0h2a2 2 0 012 2v12a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2h2' },
  { key: 'narrative_comparison', label: 'Narrative Approach', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253' },
  { key: 'overall_verdict', label: 'Overall Verdict', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
]

export function ComparisonResults() {
  const { comparisonResult, isComparing, error, filenameA, filenameB } = useComparisonStore()

  if (isComparing) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-zinc-300">Comparing videos...</p>
          <p className="text-xs text-zinc-500 mt-1">This may take a moment</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center text-red-400">
          <p className="text-sm">{error}</p>
        </div>
      </div>
    )
  }

  if (!comparisonResult) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-zinc-500">
        <p className="text-sm">Upload and analyze both videos, then click Compare</p>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4 overflow-y-auto">
      <div className="text-xs text-zinc-500 mb-2">
        Comparing <span className="text-zinc-300">{filenameA}</span> vs <span className="text-zinc-300">{filenameB}</span>
      </div>

      {SECTIONS.map(({ key, label, icon }) => {
        const value = comparisonResult[key]
        if (!value) return null
        return (
          <div key={key} className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={icon} />
              </svg>
              <h3 className="text-sm font-medium text-zinc-200">{label}</h3>
            </div>
            <p className="text-sm text-zinc-400 leading-relaxed">{value}</p>
          </div>
        )
      })}
    </div>
  )
}
