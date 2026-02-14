import { getApiKey } from './apiKey'
import type { UploadResponse, YoutubeUploadResponse } from './types'

export async function uploadVideo(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append('file', file)

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        try {
          const err = JSON.parse(xhr.responseText)
          reject(new Error(err.detail || `Upload failed: ${xhr.status}`))
        } catch {
          reject(new Error(`Upload failed: ${xhr.status}`))
        }
      }
    })

    xhr.addEventListener('error', () => reject(new Error('Network error during upload')))
    xhr.addEventListener('abort', () => reject(new Error('Upload aborted')))

    xhr.open('POST', '/api/upload')
    const key = getApiKey()
    if (key) xhr.setRequestHeader('X-API-Key', key)
    xhr.send(formData)
  })
}

export async function uploadYoutubeUrl(url: string): Promise<YoutubeUploadResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const key = getApiKey()
  if (key) headers['X-API-Key'] = key

  const res = await fetch('/api/upload-url', {
    method: 'POST',
    headers,
    body: JSON.stringify({ url }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Upload failed: ${res.status}` }))
    throw new Error(err.detail || `Upload failed: ${res.status}`)
  }
  return res.json()
}
