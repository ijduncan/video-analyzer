import { useAnalysisStore } from '../stores/analysisStore'

export function FullSummary() {
  const { summary, costEstimate } = useAnalysisStore()

  if (!summary) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-600">
        <p>Waiting for summary...</p>
      </div>
    )
  }

  return (
    <div className="p-4 max-w-3xl space-y-6">
      {/* Executive Summary */}
      <div>
        <h2 className="text-lg font-semibold text-zinc-100 mb-2">Executive Summary</h2>
        <p className="text-sm text-zinc-300 leading-relaxed">{summary.executive_summary}</p>
      </div>

      {/* Metadata grid */}
      <div className="grid grid-cols-2 gap-3">
        <MetaCard label="Genre" value={summary.genre_category} />
        <MetaCard label="Production Value" value={summary.production_value} />
        <MetaCard label="Target Audience" value={summary.target_audience} />
        <MetaCard label="Runtime" value={summary.total_runtime} />
        <MetaCard label="Scenes" value={String(summary.total_scenes)} />
        <MetaCard label="Shots" value={String(summary.total_shots)} />
      </div>

      {/* Visual Style */}
      <div>
        <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Visual Style</h3>
        <p className="text-sm text-zinc-300 leading-relaxed">{summary.visual_style}</p>
      </div>

      {/* Key Themes */}
      {summary.key_themes.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Key Themes</h3>
          <div className="flex flex-wrap gap-2">
            {summary.key_themes.map((theme, i) => (
              <span
                key={i}
                className="px-2 py-1 text-xs bg-zinc-800 text-zinc-300 rounded"
              >
                {theme}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Notable Observations */}
      {summary.notable_observations && (
        <div>
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Notable Observations</h3>
          <p className="text-sm text-zinc-300 leading-relaxed">{summary.notable_observations}</p>
        </div>
      )}

      {/* Cost Estimate */}
      {costEstimate && (
        <div className="border-t border-zinc-800 pt-4">
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">API Usage</h3>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="bg-zinc-900 rounded p-2">
              <div className="text-zinc-500">Flash Tokens</div>
              <div className="font-mono text-zinc-300">
                {(costEstimate.flash_input_tokens + costEstimate.flash_output_tokens).toLocaleString()}
              </div>
            </div>
            <div className="bg-zinc-900 rounded p-2">
              <div className="text-zinc-500">Pro Tokens</div>
              <div className="font-mono text-zinc-300">
                {(costEstimate.pro_input_tokens + costEstimate.pro_output_tokens).toLocaleString()}
              </div>
            </div>
            <div className="bg-zinc-900 rounded p-2">
              <div className="text-zinc-500">Est. Cost</div>
              <div className="font-mono text-zinc-300">
                ${costEstimate.estimated_cost_usd.toFixed(4)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MetaCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-zinc-900 rounded-lg p-3 border border-zinc-800">
      <div className="text-[10px] text-zinc-500 uppercase">{label}</div>
      <div className="text-sm text-zinc-200 mt-0.5">{value}</div>
    </div>
  )
}
