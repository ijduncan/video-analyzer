import { getApiKey } from './apiKey'
import type { AnalysisEvent } from './types'

export interface AnalysisConnection { close: () => void }

// Fetch streaming keeps credentials in headers, out of URLs and browser history.
export function connectAnalysisStream(
  jobId: string, fps: number, mode: string,
  onEvent: (event: AnalysisEvent) => void,
  onError: (error: Event) => void,
  customPrompt?: string,
): AnalysisConnection {
  const controller = new AbortController()
  const params = new URLSearchParams({ fps: String(fps), mode })
  if (customPrompt) params.set('custom_prompt', customPrompt)
  const headers: Record<string, string> = { Accept: 'text/event-stream' }
  const key = getApiKey()
  if (key) headers['X-API-Key'] = key

  void (async () => {
    try {
      const response = await fetch(`/api/analyze/${jobId}?${params}`, { headers, signal: controller.signal })
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unable to start analysis' }))
        onEvent({ type: 'error_event', data: { message: error.detail, recoverable: false } })
        return
      }
      if (!response.body) throw new Error('No analysis stream returned')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let pending = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        pending += decoder.decode(value, { stream: true })
        let boundary: RegExpExecArray | null
        while ((boundary = /\r?\n\r?\n/.exec(pending))) {
          const block = pending.slice(0, boundary.index)
          pending = pending.slice(boundary.index + boundary[0].length)
          const lines = block.split(/\r?\n/)
          const type = lines.find(line => line.startsWith('event:'))?.slice(6).trim()
          const data = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
          if (type && data) onEvent({ type, data: JSON.parse(data) } as AnalysisEvent)
        }
      }
      if (!controller.signal.aborted) onError(new Event('error'))
    } catch {
      if (!controller.signal.aborted) onError(new Event('error'))
    }
  })()
  return { close: () => controller.abort() }
}
