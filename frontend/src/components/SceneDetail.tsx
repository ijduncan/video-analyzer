import { useAnalysisStore } from '../stores/analysisStore'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">{title}</h3>
      <div className="space-y-1.5">{children}</div>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  if (!value) return null
  return (
    <div>
      <span className="text-[10px] text-zinc-500 uppercase">{label}</span>
      <p className="text-sm text-zinc-300 leading-relaxed">{value}</p>
    </div>
  )
}

export function SceneDetail() {
  const { selectedScene, flashResult, deepResults, thumbnailsReady, jobId } = useAnalysisStore()

  if (selectedScene === null) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-600">
        <p>Select a scene to view detailed analysis</p>
      </div>
    )
  }

  const scene = flashResult?.scenes.find((s) => s.scene_number === selectedScene)
  const deep = deepResults.find((d) => d.scene_number === selectedScene)

  return (
    <div className="p-4 max-w-3xl">
      {/* Scene header */}
      {scene && (
        <div className="mb-6">
          <div className="flex gap-4">
            {thumbnailsReady && jobId && scene.shots.length > 0 && (
              <img
                src={`/api/thumbnails/${jobId}/${scene.shots[0].shot_number}`}
                alt=""
                className="w-32 h-20 object-cover rounded bg-zinc-800 shrink-0"
              />
            )}
            <div>
              <h2 className="text-lg font-semibold text-zinc-100">
                Scene {scene.scene_number}: {scene.scene_title}
              </h2>
              <p className="text-sm text-zinc-400 mt-1">{scene.scene_description}</p>
              <span className="font-mono text-xs text-zinc-500 mt-1 block">
                {scene.start_time} — {scene.end_time}
              </span>
            </div>
          </div>
        </div>
      )}

      {!deep ? (
        <div className="text-sm text-zinc-500">
          {deepResults.length > 0
            ? 'Deep analysis not yet available for this scene...'
            : 'Waiting for deep analysis pass...'}
        </div>
      ) : (
        <div className="space-y-6">
          {/* Visual Analysis */}
          <Section title="Visual Analysis">
            <Field label="Lighting" value={deep.visual_analysis.lighting} />
            <Field label="Color Palette" value={deep.visual_analysis.color_palette} />
            <Field label="Composition" value={deep.visual_analysis.composition} />
            <Field label="Production Design" value={deep.visual_analysis.production_design} />
            <Field label="Visual Effects" value={deep.visual_analysis.visual_effects} />
          </Section>

          {/* Motion & Editing */}
          <Section title="Motion & Editing">
            <Field label="Pacing" value={deep.motion_editing.pacing} />
            <Field label="Transitions" value={deep.motion_editing.transitions} />
            <Field label="Camera Technique" value={deep.motion_editing.camera_technique} />
          </Section>

          {/* Audio Analysis */}
          <Section title="Audio Analysis">
            <Field label="Dialogue" value={deep.audio_analysis.dialogue} />
            <Field label="Music" value={deep.audio_analysis.music} />
            <Field label="Sound Design" value={deep.audio_analysis.sound_design} />
          </Section>

          {/* Narrative & Context */}
          <Section title="Narrative & Context">
            <Field label="Story Beat" value={deep.narrative_context.story_beat} />
            <Field label="Emotional Tone" value={deep.narrative_context.emotional_tone} />
            <Field label="Text & Graphics" value={deep.narrative_context.text_graphics} />
            <Field label="Brands & Products" value={deep.narrative_context.brands_products} />
            <Field label="People" value={deep.narrative_context.people} />
          </Section>
        </div>
      )}
    </div>
  )
}
