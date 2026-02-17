import { useAnalysisStore } from '../stores/analysisStore'

export function ProgressIndicator() {
  const {
    currentPass, currentPassName, currentScene, totalScenes,
    shotDetectionScene, shotDetectionTotal, shotDetectionSceneTitle,
  } = useAnalysisStore()

  const passLabels = ['', 'Scene Detection', 'Deep Analysis', 'Summary']
  const label = currentPassName || passLabels[currentPass] || ''

  const inShotDetection = currentPass === 1 && shotDetectionTotal > 0

  return (
    <div className="px-4 py-3 bg-zinc-900/80 border-b border-zinc-800 shrink-0">
      <div className="flex items-center gap-3 mb-2">
        <div className="flex gap-1">
          {[1, 2, 3].map((p) => (
            <div
              key={p}
              className={`w-2 h-2 rounded-full transition-colors ${
                p < currentPass
                  ? 'bg-emerald-500'
                  : p === currentPass
                    ? 'bg-blue-500 animate-pulse'
                    : 'bg-zinc-700'
              }`}
            />
          ))}
        </div>
        <span className="text-xs text-zinc-300">
          Pass {currentPass}/3: {label}
        </span>
        {inShotDetection && (
          <span className="text-[10px] text-zinc-500 truncate max-w-[200px]" title={shotDetectionSceneTitle}>
            Scene {shotDetectionScene}/{shotDetectionTotal}
            {shotDetectionSceneTitle ? ` — ${shotDetectionSceneTitle}` : ''}
          </span>
        )}
        {currentPass === 2 && totalScenes > 0 && (
          <span className="text-[10px] text-zinc-500">
            Scene {currentScene}/{totalScenes}
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-500"
          style={{
            width: `${getProgress(currentPass, currentScene, totalScenes, shotDetectionScene, shotDetectionTotal)}%`,
          }}
        />
      </div>
    </div>
  )
}

function getProgress(
  pass: number, scene: number, totalScenes: number,
  shotScene: number, shotTotal: number,
): number {
  if (pass === 1) {
    if (shotTotal > 0) {
      // In shot detection sub-pass: 15–30%
      return 15 + (shotScene / shotTotal) * 15
    }
    return 10
  }
  if (pass === 2) {
    const sceneProgress = totalScenes > 0 ? (scene / totalScenes) * 60 : 0
    return 30 + sceneProgress
  }
  if (pass === 3) return 95
  return 0
}
