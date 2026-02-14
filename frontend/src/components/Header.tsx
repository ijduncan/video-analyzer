import { useAnalysisStore } from '../stores/analysisStore'
import { useAnalysis } from '../hooks/useAnalysis'
import { FpsSelector } from './FpsSelector'
import { ModelSelector } from './ModelSelector'
import { ExportMenu } from './ExportMenu'
import { CustomPromptInput } from './CustomPromptInput'
import { SettingsMenu } from './SettingsMenu'
import { useComparisonStore } from '../stores/comparisonStore'

export function Header() {
  const { uploadStatus, analysisStatus, jobId, error } = useAnalysisStore()
  const { isCompareMode, toggleCompareMode } = useComparisonStore()
  const { startAnalysis, cancelAnalysis } = useAnalysis()

  const canAnalyze = jobId && uploadStatus === 'ready' && analysisStatus !== 'running'
  const canReanalyze = jobId && (analysisStatus === 'complete' || analysisStatus === 'error')
  const isRunning = analysisStatus === 'running'

  return (
    <header className="h-14 border-b border-zinc-800 bg-zinc-900 flex items-center px-4 gap-4 shrink-0">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-blue-500" />
        <h1 className="text-sm font-semibold tracking-wide">Video Analyzer</h1>
      </div>

      <div className="flex-1" />

      <FpsSelector />
      <ModelSelector />
      <CustomPromptInput />

      {(canAnalyze || canReanalyze) && (
        <button
          onClick={startAnalysis}
          className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded transition-colors"
        >
          {canReanalyze ? 'Re-analyze' : 'Analyze'}
        </button>
      )}

      {isRunning && (
        <button
          onClick={cancelAnalysis}
          className="px-4 py-1.5 bg-zinc-700 hover:bg-zinc-600 text-white text-sm font-medium rounded transition-colors"
        >
          Cancel
        </button>
      )}

      <ExportMenu />

      <button
        onClick={toggleCompareMode}
        className={`px-3 py-1.5 text-xs rounded transition-colors ${
          isCompareMode
            ? 'bg-purple-600 text-white'
            : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-400'
        }`}
        title="Toggle side-by-side comparison mode"
      >
        Compare
      </button>

      <SettingsMenu />

      {error && (
        <span className="text-red-400 text-xs truncate max-w-xs" title={error}>
          {error}
        </span>
      )}
    </header>
  )
}
