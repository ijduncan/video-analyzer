import type { Scene } from '../api/types'
import { parseTimeToSeconds } from '../utils/formatTime'
import { SCENE_COLORS } from '../utils/constants'
import { useAnalysisStore } from '../stores/analysisStore'

interface Props {
  scenes: Scene[]
  duration: number
  currentTime: number
  onSeek: (seconds: number) => void
}

export function Timeline({ scenes, duration, currentTime, onSeek }: Props) {
  const { selectedScene, setSelectedScene } = useAnalysisStore()

  if (!duration || duration === 0) return null

  return (
    <div className="px-3 py-2 bg-zinc-900 border-t border-zinc-800">
      <div
        className="relative h-8 bg-zinc-800 rounded cursor-pointer overflow-hidden"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect()
          const pct = (e.clientX - rect.left) / rect.width
          onSeek(pct * duration)
        }}
      >
        {/* Scene blocks */}
        {scenes.map((scene, i) => {
          const start = parseTimeToSeconds(scene.start_time)
          const end = parseTimeToSeconds(scene.end_time)
          const left = (start / duration) * 100
          const width = ((end - start) / duration) * 100

          return (
            <div
              key={scene.scene_number}
              className={`absolute top-0 h-full transition-opacity ${
                selectedScene === scene.scene_number ? 'opacity-100' : 'opacity-60 hover:opacity-80'
              }`}
              style={{
                left: `${left}%`,
                width: `${width}%`,
                backgroundColor: SCENE_COLORS[i % SCENE_COLORS.length],
              }}
              onClick={(e) => {
                e.stopPropagation()
                setSelectedScene(scene.scene_number)
                onSeek(start)
              }}
              title={`Scene ${scene.scene_number}: ${scene.scene_title}`}
            />
          )
        })}

        {/* Playhead */}
        <div
          className="absolute top-0 w-0.5 h-full bg-white z-10 pointer-events-none"
          style={{ left: `${(currentTime / duration) * 100}%` }}
        />
      </div>

      {/* Scene labels */}
      <div className="flex gap-2 mt-1.5 overflow-x-auto">
        {scenes.map((scene, i) => (
          <button
            key={scene.scene_number}
            onClick={() => {
              setSelectedScene(scene.scene_number)
              onSeek(parseTimeToSeconds(scene.start_time))
            }}
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] whitespace-nowrap transition-colors ${
              selectedScene === scene.scene_number
                ? 'bg-zinc-700 text-white'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <div
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: SCENE_COLORS[i % SCENE_COLORS.length] }}
            />
            S{scene.scene_number}
          </button>
        ))}
      </div>
    </div>
  )
}
