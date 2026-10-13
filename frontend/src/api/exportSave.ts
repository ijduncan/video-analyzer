import { getDesktopToken } from './desktop'

declare global {
  interface Window { pywebview?: { api?: { choose_files?: () => Promise<string[]>; choose_folders?: () => Promise<string[]>; choose_export_file?: (filename: string) => Promise<string | null> } } }
}
export interface SavedExport {
  saved?: boolean
  cancelled?: boolean
  path?: string
  sidecars?: { id: string; filename: string; written: boolean; path?: string; error?: string }[]
}

export async function saveExport(filename: string, url: string, media?: Record<string, unknown>, writeSidecars = false, signal?: AbortSignal): Promise<SavedExport> {
  const choose = window.pywebview?.api?.choose_export_file
  let path: string | null | undefined
  if (choose) {
    path = await choose(filename)
    if (!path) return { cancelled: true }
  }
  if (signal?.aborted) return { cancelled: true }
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getDesktopToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const selection = await fetch('/api/local-media/export-destination', { method: 'POST', headers,
    body: JSON.stringify({ filename, ...(path ? { path } : {}) }), signal })
  const destination = await selection.json()
  if (!selection.ok) throw new Error(typeof destination.detail === 'string' ? destination.detail : 'Could not choose an export location.')
  if (destination.cancelled) return { cancelled: true }
  const response = await fetch('/api/local-media/save-download', { method: 'POST', headers,
    body: JSON.stringify({ ticket: destination.ticket, url, media, write_sidecars: writeSidecars }), signal })
  const result = await response.json()
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not save export.')
  return result
}

export function savedExportMessage(result: SavedExport) {
  if (result.cancelled) return 'Export cancelled.'
  const written = result.sidecars?.filter(item => item.written).length || 0
  const failed = result.sidecars?.filter(item => !item.written) || []
  return `Saved to ${result.path}.${written ? ` ${written} XMP sidecar${written === 1 ? '' : 's'} written beside original media.` : ''}${failed.length ? ` ${failed.length} sidecar${failed.length === 1 ? '' : 's'} could not be written: ${failed.map(item => `${item.filename}: ${item.error}`).join('; ')}` : ''}`
}
