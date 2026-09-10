import { useState } from 'react'
import { useAnalysisStore } from '../stores/analysisStore'

export function ExportMenu() {
  const [isOpen, setIsOpen] = useState(false)
  const { analysisStatus, jobId, flashResult, summary } = useAnalysisStore()

  if (analysisStatus !== 'complete') return null

  const handleExport = (format: string) => {
    if (format === 'markdown') {
      // Copy markdown to clipboard
      const md = generateMarkdown()
      navigator.clipboard.writeText(md)
      setIsOpen(false)
      return
    }
    // Download via API
    window.open(`/api/export/${jobId}?format=${format}`, '_blank')
    setIsOpen(false)
  }

  const generateMarkdown = () => {
    const lines: string[] = []
    if (summary) {
      lines.push(`# ${summary.genre_category}\n`)
      lines.push(summary.executive_summary + '\n')
    }
    if (flashResult) {
      lines.push('## Scenes\n')
      for (const scene of flashResult.scenes) {
        lines.push(`### Scene ${scene.scene_number}: ${scene.scene_title}`)
        lines.push(`*${scene.start_time} - ${scene.end_time}*\n`)
        lines.push(scene.scene_description + '\n')
      }
    }
    return lines.join('\n')
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-3 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded transition-colors flex items-center gap-1"
      >
        Export
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-1 w-48 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-20 py-1">
            <ExportOption
              label="JSON"
              desc="Full structured data"
              onClick={() => handleExport('json')}
            />
            <ExportOption
              label="CSV"
              desc="Flat shot list"
              onClick={() => handleExport('csv')}
            />
            <ExportOption
              label="PDF Report"
              desc="Formatted document"
              onClick={() => handleExport('pdf')}
            />
            <ExportOption
              label="Copy Markdown"
              desc="To clipboard"
              onClick={() => handleExport('markdown')}
            />
            <div className="border-t border-zinc-700 my-1" />
            <ExportOption
              label="EDL"
              desc="CMX 3600 for Premiere/Resolve"
              onClick={() => handleExport('edl')}
            />
            <ExportOption
              label="FCP XML"
              desc="Final Cut Pro timeline"
              onClick={() => handleExport('fcpxml')}
            />
          </div>
        </>
      )}
    </div>
  )
}

function ExportOption({ label, desc, onClick }: { label: string; desc: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full px-3 py-2 text-left hover:bg-zinc-700/50 transition-colors"
    >
      <div className="text-xs text-zinc-200">{label}</div>
      <div className="text-[10px] text-zinc-500">{desc}</div>
    </button>
  )
}
