import { useCallback } from 'react'
import { uploadVideo, uploadYoutubeUrl } from '../api/upload'
import { useAnalysisStore } from '../stores/analysisStore'

export function useUpload() {
  const store = useAnalysisStore()

  const handleUpload = useCallback(async (file: File) => {
    store.setFile(file)
    store.setUploadStatus('uploading')
    store.setUploadProgress(0)

    try {
      const response = await uploadVideo(file, (percent) => {
        store.setUploadProgress(percent)
        if (percent >= 100) {
          store.setUploadStatus('processing')
        }
      })
      store.setJobId(response.job_id)
      store.setUploadStatus('ready')
    } catch (err) {
      console.error('Upload failed:', err)
      store.setUploadStatus('error')
      store.setError(err instanceof Error ? err.message : 'Upload failed')
    }
  }, [store])

  const handleYoutubeUrl = useCallback(async (url: string) => {
    store.setYoutubeUrl(url)
    store.setUploadStatus('processing')

    try {
      const response = await uploadYoutubeUrl(url)
      store.setJobId(response.job_id)
      store.setUploadStatus('ready')
    } catch (err) {
      console.error('YouTube URL upload failed:', err)
      store.setUploadStatus('error')
      store.setError(err instanceof Error ? err.message : 'Failed to load YouTube video')
    }
  }, [store])

  return { handleUpload, handleYoutubeUrl }
}
