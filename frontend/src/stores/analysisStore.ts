import { create } from 'zustand'
import type { FlashAnalysis, SceneDeepAnalysis, VideoSummary, CostEstimate, ShotMatch } from '../api/types'

export type UploadStatus = 'idle' | 'uploading' | 'processing' | 'ready' | 'error'
export type AnalysisStatus = 'idle' | 'running' | 'complete' | 'error'
export type ActiveTab = 'timeline' | 'detail' | 'summary' | 'matches' | 'custom' | 'raw'
export type AnalysisMode = 'flash_only' | 'flash_pro'

interface AnalysisState {
  // Upload
  file: File | null
  videoUrl: string | null
  youtubeUrl: string | null
  jobId: string | null
  uploadProgress: number
  uploadStatus: UploadStatus

  // Analysis
  analysisStatus: AnalysisStatus
  currentPass: number
  currentPassName: string
  currentScene: number
  totalScenes: number
  // Shot detection sub-progress (Pass 1b)
  shotDetectionScene: number
  shotDetectionTotal: number
  shotDetectionSceneTitle: string

  // Results
  flashResult: FlashAnalysis | null
  deepResults: SceneDeepAnalysis[]
  summary: VideoSummary | null
  customResult: Record<string, unknown> | null
  costEstimate: CostEstimate | null
  shotMatches: ShotMatch[]
  rawData: Record<string, unknown> | null
  thumbnailsReady: boolean

  // UI
  customPrompt: string
  selectedScene: number | null
  activeTab: ActiveTab
  searchQuery: string
  fps: number
  mode: AnalysisMode
  error: string | null

  // Actions
  setFile: (file: File) => void
  setYoutubeUrl: (url: string) => void
  setJobId: (id: string) => void
  setUploadProgress: (p: number) => void
  setUploadStatus: (s: UploadStatus) => void
  setAnalysisStatus: (s: AnalysisStatus) => void
  setCurrentPass: (pass: number, name: string) => void
  setCurrentScene: (scene: number, total: number) => void
  setShotDetectionProgress: (scene: number, total: number, title: string) => void
  setFlashResult: (result: FlashAnalysis) => void
  appendDeepResult: (result: SceneDeepAnalysis) => void
  setSummary: (summary: VideoSummary) => void
  setCustomResult: (result: Record<string, unknown>) => void
  setCostEstimate: (cost: CostEstimate) => void
  setShotMatches: (matches: ShotMatch[]) => void
  setRawData: (data: Record<string, unknown>) => void
  setThumbnailsReady: (ready: boolean) => void
  setSelectedScene: (n: number | null) => void
  setActiveTab: (tab: ActiveTab) => void
  setCustomPrompt: (prompt: string) => void
  setSearchQuery: (q: string) => void
  setFps: (fps: number) => void
  setMode: (mode: AnalysisMode) => void
  setError: (error: string | null) => void
  reset: () => void
}

const initialState = {
  file: null,
  videoUrl: null,
  youtubeUrl: null,
  jobId: null,
  uploadProgress: 0,
  uploadStatus: 'idle' as UploadStatus,
  analysisStatus: 'idle' as AnalysisStatus,
  currentPass: 0,
  currentPassName: '',
  currentScene: 0,
  totalScenes: 0,
  shotDetectionScene: 0,
  shotDetectionTotal: 0,
  shotDetectionSceneTitle: '',
  flashResult: null,
  deepResults: [],
  summary: null,
  customResult: null,
  costEstimate: null,
  shotMatches: [],
  rawData: null,
  thumbnailsReady: false,
  customPrompt: '',
  selectedScene: null,
  activeTab: 'timeline' as ActiveTab,
  searchQuery: '',
  fps: 4,
  mode: 'flash_pro' as AnalysisMode,
  error: null,
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  ...initialState,

  setFile: (file) => set({
    file,
    videoUrl: URL.createObjectURL(file),
    youtubeUrl: null,
    uploadStatus: 'idle',
    analysisStatus: 'idle',
    flashResult: null,
    deepResults: [],
    summary: null,
    customResult: null,
    shotMatches: [],
    rawData: null,
    thumbnailsReady: false,
    error: null,
  }),
  setYoutubeUrl: (youtubeUrl) => set({
    youtubeUrl,
    videoUrl: null,
    file: null,
    uploadStatus: 'idle',
    analysisStatus: 'idle',
    flashResult: null,
    deepResults: [],
    summary: null,
    customResult: null,
    shotMatches: [],
    rawData: null,
    thumbnailsReady: false,
    error: null,
  }),
  setJobId: (jobId) => set({ jobId }),
  setUploadProgress: (uploadProgress) => set({ uploadProgress }),
  setUploadStatus: (uploadStatus) => set({ uploadStatus }),
  setAnalysisStatus: (analysisStatus) => set({ analysisStatus }),
  setCurrentPass: (currentPass, currentPassName) => set({ currentPass, currentPassName }),
  setCurrentScene: (currentScene, totalScenes) => set({ currentScene, totalScenes }),
  setShotDetectionProgress: (shotDetectionScene, shotDetectionTotal, shotDetectionSceneTitle) =>
    set({ shotDetectionScene, shotDetectionTotal, shotDetectionSceneTitle }),
  setFlashResult: (flashResult) => set({ flashResult }),
  appendDeepResult: (result) => set((state) => ({
    deepResults: [...state.deepResults, result],
  })),
  setSummary: (summary) => set({ summary }),
  setCustomResult: (customResult) => set({ customResult }),
  setCostEstimate: (costEstimate) => set({ costEstimate }),
  setShotMatches: (shotMatches) => set({ shotMatches }),
  setRawData: (rawData) => set({ rawData }),
  setThumbnailsReady: (thumbnailsReady) => set({ thumbnailsReady }),
  setSelectedScene: (selectedScene) => set({ selectedScene, activeTab: selectedScene !== null ? 'detail' : 'timeline' }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setCustomPrompt: (customPrompt) => set({ customPrompt }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setFps: (fps) => set({ fps }),
  setMode: (mode) => set({ mode }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}))
