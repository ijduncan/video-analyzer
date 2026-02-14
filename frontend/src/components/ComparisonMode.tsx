import { useCallback } from 'react'
import { useComparisonStore } from '../stores/comparisonStore'
import { useAnalysisStore } from '../stores/analysisStore'
import { VideoPlayer } from './VideoPlayer'
import { ComparisonResults } from './ComparisonResults'
import { getApiKey } from '../api/apiKey'

function VideoSlot({ label, jobId, filename, videoUrl, youtubeUrl, onLoad }: {
  label: string
  jobId: string | null
  filename: string
  videoUrl: string | null
  youtubeUrl: string | null
  onLoad: () => void
}) {
  if (!jobId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-4 border border-zinc-800 rounded-lg bg-zinc-900/30">
        <p className="text-xs text-zinc-500 mb-2">{label}</p>
        <p className="text-xs text-zinc-600">Load this video in the main view first, then assign it here</p>
        <button
          onClick={onLoad}
          className="mt-2 px-3 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded transition-colors"
        >
          Use Current Video
        </button>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col border border-zinc-800 rounded-lg overflow-hidden">
      <div className="px-3 py-1.5 bg-zinc-900 border-b border-zinc-800 flex items-center gap-2">
        <span className="text-[10px] text-zinc-500 uppercase">{label}</span>
        <span className="text-xs text-zinc-300 truncate">{filename}</span>
      </div>
      <div className="flex-1 bg-black flex items-center justify-center min-h-[200px]">
        <VideoPlayer
          setVideoRef={() => {}}
          src={videoUrl || ''}
          youtubeUrl={youtubeUrl}
        />
      </div>
    </div>
  )
}

export function ComparisonMode() {
  const comp = useComparisonStore()
  const mainStore = useAnalysisStore()

  const assignA = useCallback(() => {
    const { jobId, videoUrl, youtubeUrl } = useAnalysisStore.getState()
    const filename = mainStore.flashResult?.scenes?.[0]?.scene_title || `Job ${jobId?.slice(0, 8)}`
    if (jobId) {
      comp.setJobA(jobId, filename, videoUrl, youtubeUrl)
    }
  }, [comp, mainStore])

  const assignB = useCallback(() => {
    const { jobId, videoUrl, youtubeUrl } = useAnalysisStore.getState()
    const filename = mainStore.flashResult?.scenes?.[0]?.scene_title || `Job ${jobId?.slice(0, 8)}`
    if (jobId) {
      comp.setJobB(jobId, filename, videoUrl, youtubeUrl)
    }
  }, [comp, mainStore])

  const runComparison = useCallback(async () => {
    if (!comp.jobIdA || !comp.jobIdB) return
    comp.setIsComparing(true)
    comp.setError(null)

    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      const key = getApiKey()
      if (key) headers['X-API-Key'] = key

      const res = await fetch('/api/compare', {
        method: 'POST',
        headers,
        body: JSON.stringify({ job_id_a: comp.jobIdA, job_id_b: comp.jobIdB }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Comparison failed' }))
        throw new Error(err.detail || 'Comparison failed')
      }
      const data = await res.json()
      comp.setComparisonResult(data.comparison)
    } catch (err) {
      comp.setError(err instanceof Error ? err.message : 'Comparison failed')
    }
  }, [comp])

  const canCompare = comp.jobIdA && comp.jobIdB && !comp.isComparing

  return (
    <div className="flex flex-col h-full">
      {/* Video slots side by side */}
      <div className="flex gap-2 p-2 shrink-0" style={{ height: '40%' }}>
        <VideoSlot
          label="Video A"
          jobId={comp.jobIdA}
          filename={comp.filenameA}
          videoUrl={comp.videoUrlA}
          youtubeUrl={comp.youtubeUrlA}
          onLoad={assignA}
        />
        <VideoSlot
          label="Video B"
          jobId={comp.jobIdB}
          filename={comp.filenameB}
          videoUrl={comp.videoUrlB}
          youtubeUrl={comp.youtubeUrlB}
          onLoad={assignB}
        />
      </div>

      {/* Compare button */}
      <div className="flex items-center justify-center gap-3 py-2 border-y border-zinc-800 shrink-0">
        {canCompare && (
          <button
            onClick={runComparison}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded transition-colors"
          >
            Compare Videos
          </button>
        )}
        {!comp.jobIdA && !comp.jobIdB && (
          <p className="text-xs text-zinc-500">Assign videos using "Use Current Video" above</p>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        <ComparisonResults />
      </div>
    </div>
  )
}
