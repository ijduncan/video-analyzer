import { useAnalysisStore } from '../stores/analysisStore'
import { FPS_OPTIONS } from '../utils/constants'

const FPS_LABELS: Record<number, string> = {
  1:  '1fps',
  4:  '4fps',
  12: '12fps',
  24: '24fps',
}

const FPS_DESCRIPTIONS: Record<number, string> = {
  1:  'Fast — may miss cuts < 1s',
  4:  'Balanced — catches most cuts',
  12: 'Detailed — for fast edits',
  24: 'Maximum — catches every cut',
}

export function FpsSelector() {
  const { fps, setFps, analysisStatus } = useAnalysisStore()
  const disabled = analysisStatus === 'running'

  return (
    <div className="flex items-center gap-1">
      <span
        className="text-[10px] text-zinc-500 mr-1"
        title="Shot detection frame rate. Higher = more accurate cut detection, longer scan time."
      >
        Shots
      </span>
      {FPS_OPTIONS.map((option) => (
        <button
          key={option}
          onClick={() => !disabled && setFps(option)}
          disabled={disabled}
          title={FPS_DESCRIPTIONS[option]}
          className={`px-2 py-0.5 text-[11px] rounded font-mono transition-colors ${
            fps === option
              ? 'bg-blue-600 text-white'
              : disabled
                ? 'text-zinc-700'
                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
          }`}
        >
          {FPS_LABELS[option]}
        </button>
      ))}
    </div>
  )
}
