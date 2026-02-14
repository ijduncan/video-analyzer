import { useAnalysisStore } from '../stores/analysisStore'
import { parseTimeToSeconds } from '../utils/formatTime'
import { SCENE_COLORS } from '../utils/constants'

interface Props {
  seekTo: (seconds: number) => void
}

export function TimelineView({ seekTo }: Props) {
  const { flashResult, searchQuery, setSelectedScene, thumbnailsReady, jobId } = useAnalysisStore()

  if (!flashResult) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-600">
        <p>Waiting for scene detection...</p>
      </div>
    )
  }

  const query = searchQuery.toLowerCase()
  const filteredScenes = flashResult.scenes.filter((scene) => {
    if (!query) return true
    return (
      scene.scene_title.toLowerCase().includes(query) ||
      scene.scene_description.toLowerCase().includes(query) ||
      scene.shots.some(
        (shot) =>
          shot.visual_description.toLowerCase().includes(query) ||
          shot.audio_notes.toLowerCase().includes(query) ||
          shot.subjects.some((s) => s.toLowerCase().includes(query)),
      )
    )
  })

  return (
    <div className="p-4 space-y-3">
      <div className="text-xs text-zinc-500 mb-2">
        {flashResult.total_scenes} scenes, {flashResult.total_shots} shots, {flashResult.total_duration} total
      </div>

      {filteredScenes.map((scene, i) => (
        <div
          key={scene.scene_number}
          className="bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden hover:border-zinc-700 transition-colors"
        >
          {/* Scene header */}
          <button
            onClick={() => {
              setSelectedScene(scene.scene_number)
              seekTo(parseTimeToSeconds(scene.start_time))
            }}
            className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-zinc-800/50 transition-colors"
          >
            <div
              className="w-3 h-3 rounded-full shrink-0"
              style={{ backgroundColor: SCENE_COLORS[i % SCENE_COLORS.length] }}
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2">
                <span className="text-sm font-medium text-zinc-200">
                  Scene {scene.scene_number}: {scene.scene_title}
                </span>
                <span className="font-mono text-[10px] text-zinc-500">
                  {scene.start_time} — {scene.end_time}
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-0.5 truncate">
                {scene.scene_description}
              </p>
            </div>
            <span className="text-[10px] text-zinc-600 shrink-0">
              {scene.shots.length} shot{scene.shots.length !== 1 ? 's' : ''}
            </span>
          </button>

          {/* Shots list */}
          <div className="border-t border-zinc-800/50">
            {scene.shots.map((shot) => (
              <button
                key={shot.shot_number}
                onClick={() => seekTo(parseTimeToSeconds(shot.start_time))}
                className="w-full flex items-start gap-3 px-4 py-2 text-left hover:bg-zinc-800/30 transition-colors border-b border-zinc-800/30 last:border-b-0"
              >
                {thumbnailsReady && jobId && (
                  <img
                    src={`/api/thumbnails/${jobId}/${shot.shot_number}`}
                    alt=""
                    className="w-16 h-10 object-cover rounded shrink-0 bg-zinc-800"
                    loading="lazy"
                  />
                )}
                <span className="font-mono text-[10px] text-zinc-600 mt-0.5 shrink-0 w-16">
                  {shot.start_time}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-400">
                      {shot.shot_type}
                    </span>
                    <span className="text-[10px] text-zinc-600">
                      {shot.camera_movement}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-0.5">{shot.visual_description}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
