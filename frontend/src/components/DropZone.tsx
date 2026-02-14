import { useCallback, useState, useRef } from 'react'
import { useUpload } from '../hooks/useUpload'
import { ACCEPTED_FORMATS } from '../utils/constants'

export function DropZone() {
  const [isDragging, setIsDragging] = useState(false)
  const [mode, setMode] = useState<'file' | 'url'>('file')
  const [urlValue, setUrlValue] = useState('')
  const [urlError, setUrlError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const { handleUpload, handleYoutubeUrl } = useUpload()

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleUpload(file)
    },
    [handleUpload],
  )

  const onFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) handleUpload(file)
    },
    [handleUpload],
  )

  const onSubmitUrl = useCallback(() => {
    const url = urlValue.trim()
    if (!url) return
    const ytPattern = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([\w-]{11})/
    if (!ytPattern.test(url)) {
      setUrlError('Please enter a valid YouTube URL')
      return
    }
    setUrlError('')
    handleYoutubeUrl(url)
  }, [urlValue, handleYoutubeUrl])

  return (
    <div className="w-full max-w-md">
      {/* Tab toggle */}
      <div className="flex mb-3 bg-zinc-900 rounded-lg p-0.5">
        <button
          onClick={() => setMode('file')}
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
            mode === 'file' ? 'bg-zinc-700 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Upload File
        </button>
        <button
          onClick={() => setMode('url')}
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
            mode === 'url' ? 'bg-zinc-700 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          YouTube URL
        </button>
      </div>

      {mode === 'file' ? (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`
            w-full aspect-video rounded-xl border-2 border-dashed
            flex flex-col items-center justify-center gap-3 cursor-pointer
            transition-all duration-200
            ${isDragging
              ? 'border-blue-500 bg-blue-500/10 scale-[1.02]'
              : 'border-zinc-700 bg-zinc-900/50 hover:border-zinc-500 hover:bg-zinc-900'}
          `}
        >
          <svg
            className="w-12 h-12 text-zinc-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
          <div className="text-center">
            <p className="text-sm text-zinc-300">
              {isDragging ? 'Drop video here' : 'Drag & drop a video file'}
            </p>
            <p className="text-xs text-zinc-500 mt-1">or click to browse</p>
            <p className="text-xs text-zinc-600 mt-2">
              MP4, MOV, AVI, WEBM, WMV, MPEG, FLV, 3GPP
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_FORMATS}
            onChange={onFileSelect}
            className="hidden"
          />
        </div>
      ) : (
        <div className="w-full aspect-video rounded-xl border-2 border-dashed border-zinc-700 bg-zinc-900/50 flex flex-col items-center justify-center gap-4 px-8">
          <svg className="w-10 h-10 text-red-500/60" viewBox="0 0 24 24" fill="currentColor">
            <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
          </svg>
          <div className="w-full">
            <input
              type="text"
              value={urlValue}
              onChange={(e) => { setUrlValue(e.target.value); setUrlError('') }}
              onKeyDown={(e) => e.key === 'Enter' && onSubmitUrl()}
              placeholder="https://youtube.com/watch?v=..."
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-blue-500"
            />
            {urlError && <p className="text-red-400 text-xs mt-1">{urlError}</p>}
          </div>
          <button
            onClick={onSubmitUrl}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded transition-colors"
          >
            Load Video
          </button>
        </div>
      )}
    </div>
  )
}
