import { useState } from 'react'
import { useAnalysisStore } from '../stores/analysisStore'

export function CustomPromptInput() {
  const { customPrompt, setCustomPrompt, analysisStatus } = useAnalysisStore()
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`px-3 py-1.5 text-xs rounded transition-colors flex items-center gap-1 ${
          customPrompt
            ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30'
            : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-400'
        }`}
        title="Add a custom analysis prompt"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Custom
        {customPrompt && <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />}
      </button>

      {isExpanded && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsExpanded(false)} />
          <div className="absolute right-0 mt-1 w-80 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-20 p-3">
            <label className="text-xs text-zinc-400 mb-1.5 block">Custom Analysis Prompt</label>
            <textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="e.g. Identify all brand logos and product placements..."
              className="w-full h-24 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200 p-2 resize-none focus:outline-none focus:border-purple-500 placeholder-zinc-600"
              disabled={analysisStatus === 'running'}
            />
            <div className="flex items-center justify-between mt-2">
              <span className="text-[10px] text-zinc-600">Runs as Pass 4 after main analysis</span>
              {customPrompt && (
                <button
                  onClick={() => setCustomPrompt('')}
                  className="text-[10px] text-zinc-500 hover:text-zinc-300"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
