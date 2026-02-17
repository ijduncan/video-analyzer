// --- Pass 1: Flash Analysis ---

export interface Shot {
  shot_number: number
  start_time: string
  end_time: string
  shot_type: string
  camera_movement: string
  visual_description: string
  audio_notes: string
  subjects: string[]
  dominant_colors: string[]
  mood: string
}

export interface Scene {
  scene_number: number
  scene_title: string
  scene_description: string
  start_time: string
  end_time: string
  shots: Shot[]
}

export interface FlashAnalysis {
  total_duration: string
  total_shots: number
  total_scenes: number
  scenes: Scene[]
}

// --- Pass 2: Deep Analysis ---

export interface CinematographyDetail {
  lighting: string
  color_palette: string
  composition: string
  production_design: string
  visual_effects: string
}

export interface MotionEditingDetail {
  pacing: string
  transitions: string
  camera_technique: string
}

export interface AudioDetail {
  dialogue: string
  music: string
  sound_design: string
}

export interface NarrativeDetail {
  story_beat: string
  emotional_tone: string
  text_graphics: string
  brands_products: string
  people: string
}

export interface SceneDeepAnalysis {
  scene_number: number
  visual_analysis: CinematographyDetail
  motion_editing: MotionEditingDetail
  audio_analysis: AudioDetail
  narrative_context: NarrativeDetail
}

// --- Pass 3: Summary ---

export interface VideoSummary {
  executive_summary: string
  genre_category: string
  production_value: string
  target_audience: string
  visual_style: string
  key_themes: string[]
  total_runtime: string
  total_scenes: number
  total_shots: number
  notable_observations: string
}

// --- Shot Matching ---

export interface ShotMatch {
  shot_a: number
  shot_b: number
  similarity: number
  reasons: string[]
}

// --- Cost ---

export interface CostEstimate {
  flash_input_tokens: number
  flash_output_tokens: number
  pro_input_tokens: number
  pro_output_tokens: number
  total_input_tokens: number
  total_output_tokens: number
  estimated_cost_usd: number
}

// --- API Responses ---

export interface UploadResponse {
  job_id: string
  file_id: string
  filename: string
  size_bytes: number
  mime_type: string
  status: string
}

export interface YoutubeUploadResponse extends UploadResponse {
  youtube_url: string
  youtube_id: string
}

// --- SSE Events ---

export type AnalysisEvent =
  | { type: 'pass_start'; data: { pass: number; name: string } }
  | { type: 'pass_complete'; data: { pass: number; result?: unknown } }
  | { type: 'scenes_detected'; data: { total_scenes: number; total_duration: string } }
  | { type: 'shot_detection_progress'; data: { scene: number; total: number; scene_title: string } }
  | { type: 'scene_start'; data: { scene: number; total: number } }
  | { type: 'scene_complete'; data: { scene: number; result: SceneDeepAnalysis } }
  | { type: 'custom_complete'; data: { result: Record<string, unknown> } }
  | { type: 'matches_complete'; data: { matches: ShotMatch[] } }
  | { type: 'thumbnails_ready'; data: { job_id: string } }
  | { type: 'analysis_complete'; data: { flash: FlashAnalysis; deep: SceneDeepAnalysis[]; summary: VideoSummary | null; custom: Record<string, unknown> | null; cost_estimate: CostEstimate } }
  | { type: 'error_event'; data: { message: string; recoverable: boolean } }
