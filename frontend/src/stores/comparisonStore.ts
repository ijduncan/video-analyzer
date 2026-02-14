import { create } from 'zustand'

interface ComparisonState {
  isCompareMode: boolean
  jobIdA: string | null
  jobIdB: string | null
  filenameA: string
  filenameB: string
  videoUrlA: string | null
  videoUrlB: string | null
  youtubeUrlA: string | null
  youtubeUrlB: string | null
  comparisonResult: Record<string, string> | null
  isComparing: boolean
  error: string | null

  toggleCompareMode: () => void
  setJobA: (jobId: string, filename: string, videoUrl: string | null, youtubeUrl: string | null) => void
  setJobB: (jobId: string, filename: string, videoUrl: string | null, youtubeUrl: string | null) => void
  setComparisonResult: (result: Record<string, string>) => void
  setIsComparing: (v: boolean) => void
  setError: (error: string | null) => void
  resetComparison: () => void
}

export const useComparisonStore = create<ComparisonState>((set) => ({
  isCompareMode: false,
  jobIdA: null,
  jobIdB: null,
  filenameA: '',
  filenameB: '',
  videoUrlA: null,
  videoUrlB: null,
  youtubeUrlA: null,
  youtubeUrlB: null,
  comparisonResult: null,
  isComparing: false,
  error: null,

  toggleCompareMode: () => set((state) => ({
    isCompareMode: !state.isCompareMode,
    comparisonResult: null,
    error: null,
  })),
  setJobA: (jobIdA, filenameA, videoUrlA, youtubeUrlA) => set({ jobIdA, filenameA, videoUrlA, youtubeUrlA }),
  setJobB: (jobIdB, filenameB, videoUrlB, youtubeUrlB) => set({ jobIdB, filenameB, videoUrlB, youtubeUrlB }),
  setComparisonResult: (comparisonResult) => set({ comparisonResult, isComparing: false }),
  setIsComparing: (isComparing) => set({ isComparing }),
  setError: (error) => set({ error, isComparing: false }),
  resetComparison: () => set({
    jobIdA: null,
    jobIdB: null,
    filenameA: '',
    filenameB: '',
    videoUrlA: null,
    videoUrlB: null,
    youtubeUrlA: null,
    youtubeUrlB: null,
    comparisonResult: null,
    isComparing: false,
    error: null,
  }),
}))
