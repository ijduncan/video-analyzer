import { useCallback, useEffect, useRef } from 'react'
import { connectAnalysisStream } from '../api/analyze'
import type { AnalysisEvent, FlashAnalysis, SceneDeepAnalysis, VideoSummary, CostEstimate } from '../api/types'
import { useAnalysisStore } from '../stores/analysisStore'

export function useAnalysis() {
  const store = useAnalysisStore()
  const esRef = useRef<EventSource | null>(null)

  const handleEvent = useCallback((event: AnalysisEvent) => {
    switch (event.type) {
      case 'pass_start':
        store.setCurrentPass(event.data.pass, event.data.name)
        break

      case 'pass_complete':
        if (event.data.pass === 1 && event.data.result) {
          store.setFlashResult(event.data.result as FlashAnalysis)
        }
        if (event.data.pass === 3 && event.data.result) {
          store.setSummary(event.data.result as VideoSummary)
        }
        break

      case 'scenes_detected':
        // Stage 1 complete — intermediate info, no store update needed (pass_complete fires later)
        break

      case 'shot_detection_progress':
        store.setShotDetectionProgress(event.data.scene, event.data.total, event.data.scene_title)
        break

      case 'scene_start':
        store.setCurrentScene(event.data.scene, event.data.total)
        break

      case 'scene_complete':
        store.appendDeepResult(event.data.result as SceneDeepAnalysis)
        break

      case 'custom_complete':
        store.setCustomResult(event.data.result)
        break

      case 'matches_complete':
        store.setShotMatches(event.data.matches)
        break

      case 'thumbnails_ready':
        store.setThumbnailsReady(true)
        break

      case 'analysis_complete':
        store.setAnalysisStatus('complete')
        store.setFlashResult(event.data.flash)
        if (event.data.summary) {
          store.setSummary(event.data.summary)
        }
        if (event.data.custom) {
          store.setCustomResult(event.data.custom)
        }
        store.setCostEstimate(event.data.cost_estimate)
        store.setRawData(event.data as Record<string, unknown>)
        esRef.current?.close()
        break

      case 'error_event':
        if (!event.data.recoverable) {
          store.setAnalysisStatus('error')
          store.setError(event.data.message)
          esRef.current?.close()
        } else {
          console.warn('Recoverable error:', event.data.message)
        }
        break
    }
  }, [store])

  const startAnalysis = useCallback(() => {
    const { jobId, fps, mode, customPrompt } = useAnalysisStore.getState()
    if (!jobId) return

    store.setAnalysisStatus('running')
    store.setError(null)
    store.setCustomResult(null as unknown as Record<string, unknown>)

    esRef.current = connectAnalysisStream(
      jobId,
      fps,
      mode,
      handleEvent,
      () => {
        const state = useAnalysisStore.getState()
        if (state.analysisStatus === 'running') {
          store.setAnalysisStatus('error')
          store.setError('Connection lost during analysis')
        }
      },
      customPrompt || undefined,
    )
  }, [store, handleEvent])

  const cancelAnalysis = useCallback(() => {
    esRef.current?.close()
    store.setAnalysisStatus('idle')
  }, [store])

  useEffect(() => {
    return () => {
      esRef.current?.close()
    }
  }, [])

  return { startAnalysis, cancelAnalysis }
}
