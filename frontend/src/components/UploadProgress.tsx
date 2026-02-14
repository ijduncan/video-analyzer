import { useAnalysisStore } from '../stores/analysisStore'

export function UploadProgress() {
  const { uploadProgress, uploadStatus } = useAnalysisStore()

  const label =
    uploadStatus === 'uploading'
      ? `Uploading... ${uploadProgress}%`
      : uploadStatus === 'processing'
        ? 'Processing video...'
        : ''

  return (
    <div className="w-full max-w-md mt-4">
      <div className="flex justify-between text-xs text-zinc-400 mb-1">
        <span>{label}</span>
      </div>
      <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${
            uploadStatus === 'processing'
              ? 'bg-amber-500 animate-pulse w-full'
              : 'bg-blue-500'
          }`}
          style={uploadStatus === 'uploading' ? { width: `${uploadProgress}%` } : undefined}
        />
      </div>
    </div>
  )
}
