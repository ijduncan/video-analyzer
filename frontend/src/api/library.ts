import { getApiKey } from './apiKey'
import type { FlashAnalysis, SceneDeepAnalysis, VideoSummary } from './types'

export type ReviewStatus = 'unreviewed' | 'reviewed' | 'needs_changes'
export type RightsStatus = 'unknown' | 'cleared' | 'restricted'
export interface AssetMetadata {
  title: string
  client: string
  project: string
  campaign: string
  tags: string[]
  notes: string
  rights_status: RightsStatus
  review_status: ReviewStatus
  collections: string[]
}
export interface LibraryAsset {
  job_id: string
  filename: string
  status: string
  created_at: string
  size_bytes: number
  mime_type: string
  youtube_url?: string | null
  metadata: AssetMetadata
  technical: {
    duration_seconds?: number | null
    width?: number | null
    height?: number | null
    frame_rate?: number | null
    codec?: string | null
    source_timecode?: string | null
    has_audio?: boolean | null
  }
  shot_count: number
  summary: string
  thumbnail_url: string | null
  preview_url: string | null
  match_context?: string
}
export interface LibraryResponse {
  assets: LibraryAsset[]
  total: number
  active_jobs?: number
  facets: { projects: string[]; tags: string[]; collections?: string[] }
  stats: { assets: number; shots: number; reviewed: number; duration_seconds: number }
}
export interface ShotAnnotation {
  tags: string[]
  notes: string
  review_status: ReviewStatus
}
export interface AnalysisProgress {
  stage?: string | null
  completed_sections?: number | null
  total_sections?: number | null
  failed_sections?: number | null
  completed_shots?: number | null
  processed_seconds?: number | null
  total_seconds?: number | null
  updated_at?: string | null
}
export interface AssetDetail extends LibraryAsset {
  flash: FlashAnalysis | null
  deep: SceneDeepAnalysis[] | null
  video_summary: VideoSummary | null
  custom_result: Record<string, unknown> | null
  shot_annotations: Record<string, ShotAnnotation>
  progress?: { message?: string; pass?: number; scene?: number; total?: number } | string | null
  analysis_progress?: AnalysisProgress | null
  error?: string | null
  warnings?: string[]
  analysis_config?: { provider?: string; analysis_model?: string; deep_model?: string; fps?: number; mode?: string; started_at?: string; timestamp_accuracy?: string; grouping?: string }
  cost_estimate?: { estimated_cost_usd: number | null; pricing_status?: string; pricing_as_of?: string; warnings?: string[]; total_input_tokens?: number; total_output_tokens?: number } | null
  transcript: { start_time?: string; end_time?: string; start_seconds?: number; text?: string; speaker?: string }[]
}
export interface LibraryShot {
  job_id: string
  filename: string
  scene_number: number
  scene_title: string
  shot_number: number
  start_time: string
  end_time: string
  start_seconds: number
  end_seconds: number
  visual_description: string
  shot_type: string
  camera_movement: string
  subjects: string[]
  mood: string
  tags: string[]
  thumbnail_url: string | null
  preview_url: string | null
  review_status: ReviewStatus
}
export interface Capabilities {
  google_configured: boolean
  models: { analysis: string; deep: string }
  local_media: boolean
}
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status}). Please try again.`)
  }
  return response.json() as Promise<T>
}
export function getLibrary(filters: { q?: string; project?: string; review_status?: string; tag?: string; rights_status?: string; collection?: string; limit?: number; offset?: number; sort?: string }, signal?: AbortSignal) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, String(value)) })
  return request<LibraryResponse>(`/api/library?${params}`, { signal })
}
export function getAsset(id: string, signal?: AbortSignal) {
  return request<AssetDetail>(`/api/library/${encodeURIComponent(id)}`, { signal })
}
export function getShots(filters: { q: string; project?: string; review_status?: string; tag?: string; rights_status?: string; collection?: string; limit?: number; offset?: number }, signal?: AbortSignal) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, String(value)) })
  return request<{ shots: LibraryShot[]; total: number }>(`/api/library/search/shots?${params}`, { signal })
}
export function saveMetadata(id: string, metadata: Partial<AssetMetadata>) {
  return request<LibraryAsset>(`/api/library/${encodeURIComponent(id)}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(metadata),
  })
}
export function saveShot(id: string, number: number, annotation: ShotAnnotation, expectedRange: { start_time: string; end_time: string }) {
  const params = new URLSearchParams({ expected_start_time: expectedRange.start_time, expected_end_time: expectedRange.end_time })
  return request<ShotAnnotation>(`/api/library/${encodeURIComponent(id)}/shots/${number}?${params}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(annotation),
  })
}
export function analyzeAsset(id: string, mode: 'flash_only' | 'flash_pro', fps: number, customPrompt: string) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const apiKey = getApiKey()
  if (apiKey) headers['X-API-Key'] = apiKey
  return request<{ job_id: string; status: string }>(`/api/library/${encodeURIComponent(id)}/analyze`, {
    method: 'POST', headers, body: JSON.stringify({ mode, fps, custom_prompt: customPrompt }),
  })
}
export function getCapabilities() { return request<Capabilities>('/api/capabilities') }
export function cancelAnalysis(id: string) { return request<{ status: string }>(`/api/library/${encodeURIComponent(id)}/cancel`, { method: 'POST' }) }
export function deleteAsset(id: string) {
  const headers: Record<string, string> = {}
  const apiKey = getApiKey()
  if (apiKey) headers['X-API-Key'] = apiKey
  return request<{ status: 'deleted'; remote_deleted: boolean; note: string | null }>(`/api/files/${encodeURIComponent(id)}`, {
    method: 'DELETE', headers,
  })
}
export function exportUrl(id: string, format: 'json' | 'csv' | 'xmp' | 'srt' | 'edl' | 'fcpxml') {
  return `/api/library/${encodeURIComponent(id)}/export?format=${format}`
}
