export interface VisualIndex {
  job_id: string; revision: string; total: number; indexed: number; failed: number
  status: 'not_started' | 'indexing' | 'partial' | 'complete'; error?: string
}
export interface VisualMatch {
  job_id: string; shot_number: number; seconds: number; revision: string
  title: string; filename: string; description: string; frame_url: string; media_url: string
  start_seconds: number; end_seconds: number; score: number
  aspect_ratio: number
  scores: Record<'shape' | 'composition' | 'color', number>
  source_box: number[] | null; target_box: number[] | null
}
export interface VisualResults { matches: VisualMatch[]; indexes: VisualIndex[] }
export async function visualRequest<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/visual/${path}`, body === undefined ? { signal } : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal,
  })
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new Error(typeof data?.detail === 'string' ? data.detail : `Request failed (${response.status}).`)
  }
  return response.json()
}
export function visualFrame(id: string, shot: number, seconds: number, revision: string) {
  return `/api/visual/${encodeURIComponent(id)}/frame?${new URLSearchParams({ shot_number: String(shot), seconds: String(seconds), revision })}`
}
