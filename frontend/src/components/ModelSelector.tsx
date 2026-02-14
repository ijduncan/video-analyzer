import { useAnalysisStore, type AnalysisMode } from '../stores/analysisStore'

const MODES: { key: AnalysisMode; label: string; desc: string }[] = [
  { key: 'flash_only', label: 'Flash', desc: 'Fast, scene detection only' },
  { key: 'flash_pro', label: 'Flash+Pro', desc: 'Comprehensive analysis' },
]

export function ModelSelector() {
  const { mode, setMode, analysisStatus } = useAnalysisStore()
  const disabled = analysisStatus === 'running'

  return (
    <div className="flex items-center gap-1">
      {MODES.map((m) => (
        <button
          key={m.key}
          onClick={() => !disabled && setMode(m.key)}
          disabled={disabled}
          title={m.desc}
          className={`px-2.5 py-0.5 text-[11px] rounded transition-colors ${
            mode === m.key
              ? 'bg-violet-600 text-white'
              : disabled
                ? 'text-zinc-700'
                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  )
}
