import { useAnalysisStore } from '../stores/analysisStore'
import type { ShotMatch } from '../api/types'

interface Props {
  seekTo: (seconds: number) => void
}

function SimilarityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-zinc-400 font-mono w-8">{pct}%</span>
    </div>
  )
}

function ShotLabel({ shotNumber, jobId, hasThumbs }: { shotNumber: number; jobId: string | null; hasThumbs: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {hasThumbs && jobId && (
        <img
          src={`/api/thumbnails/${jobId}/${shotNumber}`}
          alt=""
          className="w-12 h-8 object-cover rounded bg-zinc-800"
          loading="lazy"
        />
      )}
      <span className="text-xs text-zinc-300 font-mono">Shot {shotNumber}</span>
    </div>
  )
}

export function ShotMatchesView({ seekTo }: Props) {
  const { shotMatches, flashResult, thumbnailsReady, jobId, analysisStatus } = useAnalysisStore()

  if (shotMatches.length === 0) {
    if (analysisStatus === 'running') {
      return (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center text-zinc-400">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm">Analyzing shot similarities...</p>
          </div>
        </div>
      )
    }
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-zinc-500">
        <p className="text-sm">No similar shots found</p>
      </div>
    )
  }

  // Build a lookup for shot start times
  const shotTimes: Record<number, string> = {}
  if (flashResult) {
    for (const scene of flashResult.scenes) {
      for (const shot of scene.shots) {
        shotTimes[shot.shot_number] = shot.start_time
      }
    }
  }

  const parseTime = (t: string): number => {
    const parts = t.split(':').map(Number)
    if (parts.length === 2) return parts[0] * 60 + parts[1]
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0
  }

  return (
    <div className="p-4 space-y-2">
      <div className="text-xs text-zinc-500 mb-3">
        {shotMatches.length} similar shot pair{shotMatches.length !== 1 ? 's' : ''} found
      </div>

      {shotMatches.map((match: ShotMatch, i: number) => (
        <div
          key={i}
          className="bg-zinc-900 rounded-lg border border-zinc-800 p-3 hover:border-zinc-700 transition-colors"
        >
          <div className="flex items-center gap-4 mb-2">
            <button
              onClick={() => {
                const t = shotTimes[match.shot_a]
                if (t) seekTo(parseTime(t))
              }}
              className="hover:opacity-80 transition-opacity"
            >
              <ShotLabel shotNumber={match.shot_a} jobId={jobId} hasThumbs={thumbnailsReady} />
            </button>

            <div className="flex items-center gap-1 text-zinc-600">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
            </div>

            <button
              onClick={() => {
                const t = shotTimes[match.shot_b]
                if (t) seekTo(parseTime(t))
              }}
              className="hover:opacity-80 transition-opacity"
            >
              <ShotLabel shotNumber={match.shot_b} jobId={jobId} hasThumbs={thumbnailsReady} />
            </button>

            <div className="flex-1" />
            <SimilarityBar score={match.similarity} />
          </div>

          {match.reasons && match.reasons.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {match.reasons.map((reason, j) => (
                <span key={j} className="text-[10px] px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-400">
                  {reason}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
