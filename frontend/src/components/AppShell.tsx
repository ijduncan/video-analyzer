import { useAnalysisStore } from '../stores/analysisStore'
import { useComparisonStore } from '../stores/comparisonStore'
import { Header } from './Header'
import { DropZone } from './DropZone'
import { UploadProgress } from './UploadProgress'
import { VideoPlayer } from './VideoPlayer'
import { PlaybackControls } from './PlaybackControls'
import { Timeline } from './Timeline'
import { TabContainer } from './TabContainer'
import { ProgressIndicator } from './ProgressIndicator'
import { ComparisonMode } from './ComparisonMode'
import { useVideoPlayer } from '../hooks/useVideoPlayer'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'

export function AppShell() {
  const { videoUrl, youtubeUrl, uploadStatus, analysisStatus, flashResult } = useAnalysisStore()
  const { isCompareMode } = useComparisonStore()
  const player = useVideoPlayer()
  useKeyboardShortcuts(player)

  const hasVideo = videoUrl || youtubeUrl
  const showVideo = hasVideo && (uploadStatus === 'ready' || analysisStatus !== 'idle')

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100">
      <Header />

      {isCompareMode ? (
        <ComparisonMode />
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* Left Panel - Video */}
          <div className="w-[40%] min-w-[400px] border-r border-zinc-800 flex flex-col">
            {!showVideo ? (
              <div className="flex-1 flex flex-col items-center justify-center p-6">
                <DropZone />
                {uploadStatus === 'uploading' || uploadStatus === 'processing' ? (
                  <UploadProgress />
                ) : null}
              </div>
            ) : (
              <div className="flex flex-col h-full">
                <div className="flex-1 bg-black flex items-center justify-center min-h-0">
                  <VideoPlayer setVideoRef={player.setVideoRef} src={videoUrl || ''} youtubeUrl={youtubeUrl} />
                </div>
                {!youtubeUrl && <PlaybackControls player={player} />}
                {flashResult && (
                  <Timeline
                    scenes={flashResult.scenes}
                    duration={player.duration}
                    currentTime={player.currentTime}
                    onSeek={player.seekTo}
                  />
                )}
              </div>
            )}
          </div>

          {/* Right Panel - Analysis */}
          <div className="w-[60%] flex flex-col overflow-hidden">
            {analysisStatus === 'running' && <ProgressIndicator />}
            {analysisStatus === 'idle' && uploadStatus !== 'ready' && (
              <div className="flex-1 flex items-center justify-center text-zinc-600">
                <p>Upload a video to get started</p>
              </div>
            )}
            {(flashResult || analysisStatus === 'running') && (
              <TabContainer seekTo={player.seekTo} />
            )}
            {analysisStatus === 'idle' && uploadStatus === 'ready' && !flashResult && (
              <div className="flex-1 flex items-center justify-center text-zinc-500">
                <p>Click "Analyze" to begin</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
