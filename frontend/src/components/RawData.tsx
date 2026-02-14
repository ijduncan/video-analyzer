import { useState } from 'react'
import { useAnalysisStore } from '../stores/analysisStore'
import { JsonTree } from './JsonTree'

export function RawData() {
  const { rawData, flashResult, deepResults, summary } = useAnalysisStore()
  const [copied, setCopied] = useState(false)

  const data = rawData || {
    flash: flashResult,
    deep: deepResults,
    summary,
  }

  const jsonString = JSON.stringify(data, null, 2)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(jsonString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!flashResult && !rawData) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-600">
        <p>No data yet</p>
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-zinc-500">
          {jsonString.length.toLocaleString()} characters
        </span>
        <button
          onClick={handleCopy}
          className="px-3 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded transition-colors"
        >
          {copied ? 'Copied!' : 'Copy JSON'}
        </button>
      </div>
      <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4 overflow-auto max-h-[calc(100vh-200px)]">
        <JsonTree data={data} />
      </div>
    </div>
  )
}
