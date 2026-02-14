import { formatSeconds } from '../utils/formatTime'
import { PLAYBACK_RATES } from '../utils/constants'

interface Props {
  player: {
    isPlaying: boolean
    currentTime: number
    duration: number
    playbackRate: number
    togglePlay: () => void
    seekTo: (seconds: number) => void
    setPlaybackRate: (rate: number) => void
  }
}

export function PlaybackControls({ player }: Props) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-zinc-900 border-t border-zinc-800">
      {/* Play/Pause */}
      <button
        onClick={player.togglePlay}
        className="w-8 h-8 flex items-center justify-center text-zinc-300 hover:text-white transition-colors"
        title={player.isPlaying ? 'Pause (Space)' : 'Play (Space)'}
      >
        {player.isPlaying ? (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </button>

      {/* Time */}
      <span className="font-mono text-xs text-zinc-400 min-w-[80px]">
        {formatSeconds(player.currentTime)} / {formatSeconds(player.duration || 0)}
      </span>

      {/* Scrubber */}
      <input
        type="range"
        min={0}
        max={player.duration || 0}
        step={0.1}
        value={player.currentTime}
        onChange={(e) => player.seekTo(Number(e.target.value))}
        className="flex-1 h-1 accent-blue-500 cursor-pointer"
      />

      {/* Speed */}
      <div className="flex items-center gap-1">
        {PLAYBACK_RATES.map((rate) => (
          <button
            key={rate}
            onClick={() => player.setPlaybackRate(rate)}
            className={`px-1.5 py-0.5 text-[10px] rounded font-mono transition-colors ${
              player.playbackRate === rate
                ? 'bg-blue-600 text-white'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {rate}x
          </button>
        ))}
      </div>
    </div>
  )
}
