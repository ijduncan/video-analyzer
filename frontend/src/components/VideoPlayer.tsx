interface Props {
  setVideoRef: (node: HTMLVideoElement | null) => void
  src: string
  youtubeUrl?: string | null
}

function extractYoutubeId(url: string): string | null {
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([\w-]{11})/)
  return match ? match[1] : null
}

export function VideoPlayer({ setVideoRef, src, youtubeUrl }: Props) {
  if (youtubeUrl) {
    const videoId = extractYoutubeId(youtubeUrl)
    if (videoId) {
      return (
        <iframe
          src={`https://www.youtube.com/embed/${videoId}?autoplay=0&rel=0`}
          className="w-full h-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          title="YouTube video player"
        />
      )
    }
  }

  return (
    <video
      ref={setVideoRef}
      src={src}
      className="max-h-full max-w-full"
      preload="metadata"
    />
  )
}
