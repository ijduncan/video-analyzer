import { getApiKey } from './apiKey'
import type { AnalysisEvent } from './types'

export function connectAnalysisStream(
  jobId: string,
  fps: number,
  mode: string,
  onEvent: (event: AnalysisEvent) => void,
  onError: (error: Event) => void,
  customPrompt?: string,
): EventSource {
  const params = new URLSearchParams({ fps: String(fps), mode })
  if (customPrompt) params.set('custom_prompt', customPrompt)
  const key = getApiKey()
  if (key) params.set('api_key', key)
  const url = `/api/analyze/${jobId}?${params}`
  const es = new EventSource(url)

  const eventTypes = [
    'pass_start',
    'pass_complete',
    'scenes_detected',
    'shot_detection_progress',
    'scene_start',
    'scene_complete',
    'custom_complete',
    'matches_complete',
    'thumbnails_ready',
    'analysis_complete',
    'error_event',
  ] as const

  for (const eventType of eventTypes) {
    es.addEventListener(eventType, (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        onEvent({ type: eventType, data } as AnalysisEvent)
      } catch (err) {
        console.error(`Failed to parse SSE event ${eventType}:`, err)
      }
    })
  }

  es.onerror = onError

  return es
}
