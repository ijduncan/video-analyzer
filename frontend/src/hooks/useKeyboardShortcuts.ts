import { useEffect } from 'react'
import { useAnalysisStore, type ActiveTab } from '../stores/analysisStore'
import { parseTimeToSeconds } from '../utils/formatTime'

interface PlayerControls {
  togglePlay: () => void
  seekTo: (seconds: number) => void
}

export function useKeyboardShortcuts(player: PlayerControls) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture when typing in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return
      }

      const state = useAnalysisStore.getState()

      switch (e.key) {
        case ' ':
          e.preventDefault()
          player.togglePlay()
          break

        case 'ArrowLeft': {
          e.preventDefault()
          if (state.flashResult) {
            const scenes = state.flashResult.scenes
            const currentScene = state.selectedScene || 1
            const prevScene = scenes.find((s) => s.scene_number === currentScene - 1)
            if (prevScene) {
              state.setSelectedScene(prevScene.scene_number)
              player.seekTo(parseTimeToSeconds(prevScene.start_time))
            }
          }
          break
        }

        case 'ArrowRight': {
          e.preventDefault()
          if (state.flashResult) {
            const scenes = state.flashResult.scenes
            const currentScene = state.selectedScene || 0
            const nextScene = scenes.find((s) => s.scene_number === currentScene + 1)
            if (nextScene) {
              state.setSelectedScene(nextScene.scene_number)
              player.seekTo(parseTimeToSeconds(nextScene.start_time))
            }
          }
          break
        }

        case '1':
          state.setActiveTab('timeline' as ActiveTab)
          break
        case '2':
          state.setActiveTab('detail' as ActiveTab)
          break
        case '3':
          state.setActiveTab('summary' as ActiveTab)
          break
        case '4':
          state.setActiveTab('matches' as ActiveTab)
          break
        case '5':
          state.setActiveTab('custom' as ActiveTab)
          break
        case '6':
          state.setActiveTab('raw' as ActiveTab)
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [player])
}
