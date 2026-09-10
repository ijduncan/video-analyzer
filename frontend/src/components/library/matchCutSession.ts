import type { VisualIndex, VisualMatch, VisualResults, VisualShape } from '../../api/visual'

export interface MatchCutSession {
  run: string | null
  shotNumber: number
  seconds: number
  targetIds: string[]
  weights: { shape: number; composition: number; color: number }
  region: number[] | null
  sourceShapeId: number | null
  alignShape: boolean
  knownShapes: { key: string; forms: VisualShape[] } | null
  indexes: VisualIndex[]
  result: VisualResults | null
  resultKey: string
  searchIntent: string
  selected: VisualMatch | null
  incoming: number
  handle: number
}

const PREFIX = 'video-analyzer:match-cuts:v1:'
const memory = new Map<string, MatchCutSession>()

export function readMatchCutSession(id: string, run: string | null): MatchCutSession | null {
  try {
    const cached = memory.get(id)
    const raw = cached ? null : localStorage.getItem(PREFIX + id)
    const saved: MatchCutSession | null = cached || (raw ? JSON.parse(raw) : null)
    if (!saved || saved.run !== run || !Number.isFinite(saved.shotNumber) || !Number.isFinite(saved.seconds) ||
      !Array.isArray(saved.targetIds) || !saved.targetIds.every(id => typeof id === 'string') ||
      !saved.weights || !['shape', 'composition', 'color'].every(axis => {
        const weight = saved.weights[axis as keyof typeof saved.weights]
        return Number.isFinite(weight) && weight >= 0 && weight <= 1
      }) || !Array.isArray(saved.indexes) || typeof saved.searchIntent !== 'string' ||
      typeof saved.resultKey !== 'string' || typeof saved.alignShape !== 'boolean' ||
      !Number.isFinite(saved.incoming) || ![.5, 1, 2, 3, 5].includes(saved.handle) ||
      (saved.region !== null && (!Array.isArray(saved.region) || saved.region.length !== 4 || !saved.region.every(Number.isFinite))) ||
      (saved.sourceShapeId !== null && (!Number.isInteger(saved.sourceShapeId) || saved.sourceShapeId < 0)) ||
      (saved.knownShapes !== null && (typeof saved.knownShapes?.key !== 'string' || !Array.isArray(saved.knownShapes?.forms))) ||
      (saved.result && !Array.isArray(saved.result.matches))) return null
    return saved
  } catch { return memory.get(id)?.run === run ? memory.get(id)! : null }
}

export function saveMatchCutSession(id: string, session: MatchCutSession) {
  memory.set(id, session)
  try { localStorage.setItem(PREFIX + id, JSON.stringify(session)) }
  catch { /* Navigation still restores from memory when browser storage is unavailable. */ }
}
