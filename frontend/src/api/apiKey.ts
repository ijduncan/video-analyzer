import { useSettingsStore } from '../stores/settingsStore'

export function getApiKey(): string {
  return useSettingsStore.getState().apiKey
}
