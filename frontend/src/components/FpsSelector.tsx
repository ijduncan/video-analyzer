import { useAnalysisStore } from '../stores/analysisStore'
import { FPS_OPTIONS } from '../utils/constants'

export function FpsSelector() {
  const { fps, setFps, analysisStatus } = useAnalysisStore()
  const disabled = analysisStatus === 'running'

  return (
    <div className="flex items-center gap-1">
      <span className="text-[10px] text-zinc-500 mr-1" title="Frames per second for analysis. Higher = more detail, slower, more expensive.">
        FPS
      </span>
      {FPS_OPTIONS.map((option) => (
        <button
          key={option}
          onClick={() => !disabled && setFps(option)}
          disabled={disabled}
          className={`px-2 py-0.5 text-[11px] rounded font-mono transition-colors ${
            fps === option
              ? 'bg-blue-600 text-white'
              : disabled
                ? 'text-zinc-700'
                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
          }`}
        >
          {option}
        </button>
      ))}
    </div>
  )
}
