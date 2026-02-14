import { create } from 'zustand'

const STORAGE_KEY = 'video-analyzer-api-key'

interface SettingsState {
  apiKey: string
  setApiKey: (key: string) => void
}

export const useSettingsStore = create<SettingsState>((set) => ({
  apiKey: localStorage.getItem(STORAGE_KEY) || '',
  setApiKey: (apiKey) => {
    if (apiKey) {
      localStorage.setItem(STORAGE_KEY, apiKey)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
    set({ apiKey })
  },
}))
