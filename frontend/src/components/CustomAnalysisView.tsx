import { useAnalysisStore } from '../stores/analysisStore'
import { JsonTree } from './JsonTree'

export function CustomAnalysisView() {
  const { customResult, customPrompt, analysisStatus, currentPass } = useAnalysisStore()

  if (!customPrompt) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center text-zinc-500 max-w-sm">
          <svg className="w-10 h-10 mx-auto mb-3 text-zinc-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm mb-1">No custom prompt set</p>
          <p className="text-xs text-zinc-600">
            Click the "Custom" button in the header to add a prompt before analyzing.
          </p>
        </div>
      </div>
    )
  }

  if (!customResult) {
    if (analysisStatus === 'running' && currentPass >= 4) {
      return (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center text-zinc-400">
            <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm">Running custom analysis...</p>
            <p className="text-xs text-zinc-600 mt-1 max-w-xs">{customPrompt}</p>
          </div>
        </div>
      )
    }

    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center text-zinc-500">
          <p className="text-sm">Custom analysis pending</p>
          <p className="text-xs text-zinc-600 mt-1 max-w-xs">
            Your prompt will run after the main analysis completes.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
        <div className="text-[10px] text-purple-400 uppercase tracking-wider mb-1">Your Prompt</div>
        <p className="text-sm text-zinc-300">{customPrompt}</p>
      </div>

      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
        <div className="text-[10px] text-purple-400 uppercase tracking-wider mb-2">Result</div>
        <div className="font-mono text-xs overflow-x-auto">
          <JsonTree data={customResult} />
        </div>
      </div>
    </div>
  )
}
