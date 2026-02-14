import { useCallback, useEffect, useRef, useState } from 'react'

export function useVideoPlayer() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [playbackRate, setPlaybackRateState] = useState(1)
  // Trigger re-run of effect when video element mounts
  const [mounted, setMounted] = useState(0)

  // Callback ref to detect when video element actually mounts
  const setVideoRef = useCallback((node: HTMLVideoElement | null) => {
    (videoRef as React.MutableRefObject<HTMLVideoElement | null>).current = node
    if (node) setMounted((c) => c + 1)
  }, [])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const onTimeUpdate = () => setCurrentTime(video.currentTime)
    const onLoadedMetadata = () => setDuration(video.duration)
    const onDurationChange = () => setDuration(video.duration)
    const onPlay = () => setIsPlaying(true)
    const onPause = () => setIsPlaying(false)

    video.addEventListener('timeupdate', onTimeUpdate)
    video.addEventListener('loadedmetadata', onLoadedMetadata)
    video.addEventListener('durationchange', onDurationChange)
    video.addEventListener('play', onPlay)
    video.addEventListener('pause', onPause)

    // Pick up duration if already loaded
    if (video.duration) setDuration(video.duration)

    return () => {
      video.removeEventListener('timeupdate', onTimeUpdate)
      video.removeEventListener('loadedmetadata', onLoadedMetadata)
      video.removeEventListener('durationchange', onDurationChange)
      video.removeEventListener('play', onPlay)
      video.removeEventListener('pause', onPause)
    }
  }, [mounted])

  const play = useCallback(() => videoRef.current?.play(), [])
  const pause = useCallback(() => videoRef.current?.pause(), [])

  const togglePlay = useCallback(() => {
    if (videoRef.current?.paused) {
      videoRef.current.play()
    } else {
      videoRef.current?.pause()
    }
  }, [])

  const seekTo = useCallback((seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds
    }
  }, [])

  const setPlaybackRate = useCallback((rate: number) => {
    if (videoRef.current) {
      videoRef.current.playbackRate = rate
      setPlaybackRateState(rate)
    }
  }, [])

  return {
    videoRef,
    setVideoRef,
    isPlaying,
    currentTime,
    duration,
    playbackRate,
    play,
    pause,
    togglePlay,
    seekTo,
    setPlaybackRate,
  }
}
