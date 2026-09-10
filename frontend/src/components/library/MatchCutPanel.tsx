import { useCallback, useEffect, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import { getProjects } from '../../api/library'
import type { AssetDetail, LibraryProject } from '../../api/library'
import type { Shot } from '../../api/types'
import { visualFrame, visualRequest } from '../../api/visual'
import type { VisualIndex, VisualMatch, VisualResults } from '../../api/visual'
import { errorMessage, timestamp } from './format'
import './MatchCutPanel.css'

const AXES = ['shape', 'composition', 'color'] as const
const time = (seconds: number) => `${Math.floor(seconds / 60)}:${(seconds % 60).toFixed(3).padStart(6, '0')}`
const midpoint = (shot: Shot) => (timestamp(shot.start_time) + timestamp(shot.end_time)) / 2

export function MatchCutPanel({ asset, shots, initialShot }: { asset: AssetDetail; shots: Shot[]; initialShot?: Shot }) {
  const [shotNumber, setShotNumber] = useState(initialShot?.shot_number || shots[0]?.shot_number)
  const shot = shots.find(s => s.shot_number === shotNumber) || shots[0]
  const [seconds, setSeconds] = useState(shot ? midpoint(shot) : 0)
  const [frameSeconds, setFrameSeconds] = useState(seconds)
  const [projects, setProjects] = useState<LibraryProject[]>([])
  const [targetIds, setTargetIds] = useState([asset.job_id])
  const [indexes, setIndexes] = useState<VisualIndex[]>([])
  const [weights, setWeights] = useState({ shape: 1, composition: 1, color: 1 })
  const [region, setRegion] = useState<number[] | null>(null)
  const [result, setResult] = useState<VisualResults | null>(null)
  const [selected, setSelected] = useState<VisualMatch | null>(null)
  const [incoming, setIncoming] = useState(0)
  const [incomingFrame, setIncomingFrame] = useState(0)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [working, setWorking] = useState(false)
  const [preview, setPreview] = useState(false)
  const [handle, setHandle] = useState(2)
  const [indexErrors, setIndexErrors] = useState<string[]>([])
  const request = useRef<AbortController | null>(null)
  const sourceIndex = indexes.find(i => i.job_id === asset.job_id)
  const scopeKey = JSON.stringify([...new Set([asset.job_id, ...targetIds])])
  const searchKey = JSON.stringify([shotNumber, frameSeconds, targetIds, weights, region, indexes.map(i => [i.job_id, i.revision, i.composition?.version])])
  const [resultKey, setResultKey] = useState('')
  const stale = !!result && resultKey !== searchKey
  const coverage = indexes.filter(i => targetIds.includes(i.job_id)).map(i => `${i.job_id}:${i.composition?.indexed || 0}`).join('|')
  const lastCoverage = useRef('')
  const sourceRevision = sourceIndex?.revision
  const number = shot?.shot_number

  useEffect(() => {
    const controller = new AbortController()
    getProjects(controller.signal).then(data => setProjects(data.projects.filter(p => p.shot_count > 0))).catch(err => { if (!controller.signal.aborted) setError(errorMessage(err)) })
    return () => { controller.abort(); request.current?.abort() }
  }, [])
  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      const ids = JSON.parse(scopeKey) as string[]
      const rows = await Promise.all(ids.map(async id => {
        try { return { data: await visualRequest<VisualIndex>(`${encodeURIComponent(id)}/index`, undefined, controller.signal) } }
        catch (err) { return { error: errorMessage(err) } }
      }))
      if (controller.signal.aborted) return
      setIndexes(rows.flatMap(row => row.data ? [row.data] : []))
      setIndexErrors([...new Set(rows.flatMap(row => row.error ? [row.error] : []))])
      timer = setTimeout(poll, 1800)
    }
    void poll()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [scopeKey])
  useEffect(() => {
    const timer = setTimeout(() => setFrameSeconds(seconds), 250)
    return () => clearTimeout(timer)
  }, [seconds])
  useEffect(() => {
    const timer = setTimeout(() => setIncomingFrame(incoming), 250)
    return () => clearTimeout(timer)
  }, [incoming])
  useEffect(() => { request.current?.abort(); setWorking(false) }, [searchKey])

  async function build() {
    setError('')
    try {
      for (const id of targetIds) await visualRequest(`${encodeURIComponent(id)}/index`, {})
      setNotice('Search as frames arrive; search again for newly indexed shots.')
    } catch (err) { setError(errorMessage(err)) }
  }
  const find = useCallback(async (automatic = false) => {
    if (!number || !sourceRevision) return
    request.current?.abort()
    const controller = new AbortController(); request.current = controller
    lastCoverage.current = coverage
    setWorking(true); setError(''); setNotice('')
    try {
      const data = await visualRequest<VisualResults>(`${asset.job_id}/search`, {
        shot_number: number, seconds: frameSeconds, revision: sourceRevision,
        target_ids: targetIds, ...weights, region: weights.shape ? region : null, prepare_composition: !automatic,
      }, controller.signal)
      if (controller.signal.aborted) return
      setResult(data); setResultKey(searchKey)
      if (!automatic) setSelected(null)
    } catch (err) { if (!controller.signal.aborted) setError(errorMessage(err)) }
    finally { if (!controller.signal.aborted) setWorking(false) }
  }, [number, sourceRevision, coverage, asset.job_id, frameSeconds, targetIds, weights, region, searchKey])
  useEffect(() => {
    if (!weights.composition || !result || resultKey !== searchKey || working || coverage === lastCoverage.current) return
    const timer = setTimeout(() => { void find(true) }, 300)
    return () => clearTimeout(timer)
  }, [weights.composition, result, resultKey, searchKey, working, coverage, find])
  function choose(match: VisualMatch) { setSelected(match); setIncoming(match.seconds); setIncomingFrame(match.seconds) }
  function exportPair() {
    if (!selected || !shot || stale) return
    const data = { version: 1, type: 'visual_match_cut', timing: 'media_file_seconds', timestamp_accuracy: 'approximate; verify in editor',
      outgoing: { job_id: asset.job_id, filename: asset.filename, shot_number: shot.shot_number, revision: sourceIndex?.revision,
        start_seconds: Math.max(timestamp(shot.start_time), frameSeconds - handle), end_seconds: frameSeconds },
      incoming: { job_id: selected.job_id, title: selected.title, filename: selected.filename, shot_number: selected.shot_number, revision: selected.revision,
        start_seconds: incoming, end_seconds: Math.min(selected.end_seconds, incoming + handle) },
      discovery: { sampled_outgoing_seconds: frameSeconds, sampled_incoming_seconds: selected.seconds,
        scores: selected.scores, score_basis: result?.score_basis || 'local_visual_measurements', weights, source_region: region } }
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = `match-cut-${shot.shot_number}-${selected.shot_number}.json`; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  if (!shot || !asset.preview_url) return <p className="lw-panel-empty">Import and analyze a local video to discover match cuts.</p>
  const start = timestamp(shot.start_time), end = timestamp(shot.end_time)
  const step = Math.min(1 / (asset.technical.frame_rate || 24), (end - start) / 2)
  const targets = indexes.filter(i => targetIds.includes(i.job_id))
  const available = targets.reduce((sum, index) => sum + index.indexed, 0)
  const readingComposition = targets.some(i => i.composition?.running)
  const sourceBox = !stale && weights.composition && result?.source_composition?.subject_box
  const subjectBox = sourceBox ? [sourceBox[1] / 1000, sourceBox[0] / 1000, (sourceBox[3] - sourceBox[1]) / 1000, (sourceBox[2] - sourceBox[0]) / 1000] : null
  return <section className="mc-panel" aria-label="Visual match-cut discovery">
    <div className="mc-heading"><div><h2>Match cuts</h2><p>Match shape, composition, and color across your footage.</p></div><button className="lw-button lw-button-primary mc-find" onClick={() => find()} disabled={working || !available || !targetIds.length || !sourceIndex || seconds !== frameSeconds || !Object.values(weights).some(Boolean)}>{working ? weights.composition ? 'Reading composition…' : 'Finding matches…' : 'Find match cut'}</button></div>
    <div className="mc-controls">
      <label className="lw-field">Outgoing shot<select aria-label="Outgoing shot" value={shot.shot_number} onChange={event => {
        const next = shots.find(s => s.shot_number === Number(event.target.value))!
        setShotNumber(next.shot_number); setSeconds(midpoint(next)); setFrameSeconds(midpoint(next)); setRegion(null); setSelected(null)
      }}>{shots.map(s => <option key={s.shot_number} value={s.shot_number}>Shot {String(s.shot_number).padStart(2, '0')} · {s.start_time}</option>)}</select></label>
      <details className="mc-projects"><summary>Search {targetIds.length} project{targetIds.length === 1 ? '' : 's'}</summary>{projects.map(p => <label key={p.id}><input type="checkbox" checked={targetIds.includes(p.id)} onChange={event => setTargetIds(ids => event.target.checked ? [...ids, p.id] : ids.filter(id => id !== p.id))} />{p.title || p.filename}</label>)}</details>
      <div className="mc-weights">{AXES.map(axis => <label key={axis}>{axis}<input aria-label={`${axis} weight`} type="range" min="0" max="1" step="0.1" value={weights[axis]} onChange={event => setWeights(w => ({ ...w, [axis]: Number(event.target.value) }))} /><span>{weights[axis] === 0 ? 'Off' : `${Math.round(weights[axis] * 100)}%`}</span></label>)}</div>
    </div>
    <div className="mc-index"><div role="status">{targets.some(i => i.status === 'indexing') ? 'Indexing' : 'Visual index'} · {available} / {targets.reduce((n, i) => n + i.total, 0)} frames{targets.some(i => i.failed) ? ' · Some frames failed; resume to retry.' : ''}</div>
      <button className="lw-button" disabled={!targetIds.length || targets.some(i => i.status === 'indexing') || (targets.length === targetIds.length && targets.every(i => i.status === 'complete'))} onClick={build}>{targets.some(i => i.status === 'indexing') ? 'Indexing…' : targets.every(i => i.status === 'complete') && targets.length ? 'Index ready' : available ? 'Resume indexing' : 'Build visual index'}</button>
      {(targets.some(i => i.status === 'indexing') || readingComposition) && <button className="lw-text-button" onClick={async () => { try { await Promise.all(targetIds.map(id => visualRequest(`${id}/index/cancel`, {}))); setNotice('Indexing paused. Saved frame analysis remains searchable.') } catch (err) { setError(errorMessage(err)) } }}>Pause</button>}
      <small>{weights.composition ? 'Composition uses Gemini · frame analysis is cached' : 'Shape and color use the local index · no API calls'}</small>
    </div>
    {(weights.composition > 0 || readingComposition) && <div className="mc-composition-status" role="status">{readingComposition ? 'Understanding composition' : 'Composition cache'} · {targets.reduce((n, i) => n + (i.composition?.indexed || 0), 0)} / {targets.reduce((n, i) => n + (i.composition?.total || 0), 0)} frames{readingComposition && ' · Matches update as frames are understood.'}</div>}
    {[...indexErrors, ...indexes.flatMap(i => [i.error, weights.composition ? i.composition?.error : null].filter((e): e is string => !!e)), ...(error ? [error] : [])].map((message, i) => <p className="lw-inline-error" role="alert" key={i}>{message}</p>)}
    {notice && <p role="status">{notice}</p>}
    <div className="mc-pair">
      <div><div className="mc-frame-heading"><strong>A · Outgoing</strong><span>{time(frameSeconds)}</span></div>
        <FrameRegion label="Outgoing frame" url={sourceIndex ? visualFrame(asset.job_id, shot.shot_number, frameSeconds, sourceIndex.revision) : undefined} region={weights.shape ? region : null} box={subjectBox || (!stale ? selected?.source_box : null)} onRegion={weights.shape ? setRegion : undefined} />
        {!stale && weights.composition > 0 && result?.source_composition && <p className="mc-composition-summary">{result.source_composition.summary}<small>Outlined: dominant subject · Gemini interpretation</small></p>}
        <div className="mc-trim"><input type="range" aria-label="Outgoing cut frame" min={start} max={Math.max(start, end - step)} step={step} value={seconds} onChange={event => { setSeconds(Number(event.target.value)); setRegion(null) }} /><input type="number" aria-label="Outgoing cut seconds" min={start} max={end - step} step={step} value={Number(seconds.toFixed(3))} onChange={event => { if (event.target.value !== '') setSeconds(Math.min(end - step, Math.max(start, Number(event.target.value)))) }} /></div>
        {weights.shape > 0 && <div className="mc-frame-heading"><small>Drag over a shape to focus. Color compares the whole frame.</small><button className="lw-text-button" onClick={() => setRegion([.25, .25, .5, .5])}>Center region</button>{region && <button className="lw-text-button" onClick={() => setRegion(null)}>Whole frame</button>}</div>}

      </div>
      <div><div className="mc-frame-heading"><strong>B · Incoming{selected ? ` · Shot ${selected.shot_number}` : ''}</strong><span>{selected ? time(incomingFrame) : ''}</span></div>
        {selected && !stale ? <><FrameRegion url={visualFrame(selected.job_id, selected.shot_number, incomingFrame, selected.revision)} box={Math.abs(incomingFrame - selected.seconds) < .001 ? selected.target_box : null} />
          <div className="mc-trim"><input type="range" aria-label="Incoming cut frame" min={selected.start_seconds} max={selected.end_seconds - Math.min(.04, (selected.end_seconds - selected.start_seconds) / 2)} step="0.01" value={incoming} onChange={event => setIncoming(Number(event.target.value))} /><input type="number" aria-label="Incoming cut seconds" min={selected.start_seconds} max={selected.end_seconds - Math.min(.04, (selected.end_seconds - selected.start_seconds) / 2)} step="0.01" value={Number(incoming.toFixed(3))} onChange={event => { if (event.target.value !== '') setIncoming(Math.min(selected.end_seconds - Math.min(.04, (selected.end_seconds - selected.start_seconds) / 2), Math.max(selected.start_seconds, Number(event.target.value)))) }} /></div>
          <p>{selected.title}</p><div className="mc-pair-actions"><button className="lw-button lw-button-primary" disabled={frameSeconds <= start || seconds !== frameSeconds || incoming !== incomingFrame} onClick={() => setPreview(true)}>Play A → B</button><button className="lw-button" disabled={frameSeconds <= start || seconds !== frameSeconds || incoming !== incomingFrame} onClick={exportPair}>Export cut JSON</button><label>Preview each side <select value={handle} onChange={event => setHandle(Number(event.target.value))}>{[.5, 1, 2, 3, 5].map(v => <option key={v} value={v}>{v}s</option>)}</select></label></div>
          {Math.abs(incomingFrame - selected.seconds) > .001 && <small>Scores refer to the discovered frame. Review your adjusted cut in the preview.</small>}
        </> : <div className="mc-placeholder">{stale ? 'Search again to match your new selection.' : 'Choose a match below to preview the cut.'}</div>}
      </div>
    </div>
    {result && !stale && <><div className="mc-results-title"><h3>{result.matches.length} candidate{result.matches.length === 1 ? '' : 's'}</h3><small>Relative visual similarity · not confidence. Motion is not scored yet.</small></div>
      {!result.matches.length && <p>{readingComposition ? 'Reading shot composition. Compatible candidates will appear here.' : weights.composition ? 'No compatible framing found in the analyzed frames. Try another source frame or search more projects.' : 'No candidates yet. Index more shots, change the frame, or widen the region.'}</p>}
      <div className="mc-results">{result.matches.map(match => <button key={`${match.job_id}-${match.shot_number}`} className={`mc-card ${selected?.job_id === match.job_id && selected?.seconds === match.seconds ? 'is-selected' : ''}`} aria-pressed={selected?.job_id === match.job_id && selected?.seconds === match.seconds} onClick={() => choose(match)}><div style={{ aspectRatio: match.aspect_ratio }}><img src={match.frame_url} loading="lazy" alt={`Candidate shot ${match.shot_number} at ${time(match.seconds)}`} /><Box box={match.target_box} /></div><strong>Shot {String(match.shot_number).padStart(2, '0')} <time>{time(match.seconds)}</time></strong><span>{match.title}</span><p>{match.composition_summary || match.description}</p>{match.reasons && <div className="mc-reasons">{match.reasons.map(reason => <span key={reason}>{reason}</span>)}</div>}<div className="mc-scores">{AXES.filter(axis => weights[axis] > 0).map(axis => <span key={axis}>{axis} <b>{Math.round(match.scores[axis] * 100)}</b></span>)}</div></button>)}</div>
    </>}
    {preview && selected && !stale && <CutPreview sourceUrl={asset.preview_url} targetUrl={selected.media_url} aStart={Math.max(start, frameSeconds - handle)} aEnd={frameSeconds} bStart={incoming} bEnd={Math.min(selected.end_seconds, incoming + handle)} onClose={() => setPreview(false)} />}
  </section>
}

function Box({ box }: { box?: number[] | null }) {
  return box ? <span className="mc-box" style={{ left: `${box[0] * 100}%`, top: `${box[1] * 100}%`, width: `${box[2] * 100}%`, height: `${box[3] * 100}%` }} /> : null
}

function FrameRegion({ url, region, box, onRegion, label = 'Incoming frame' }: { label?: string; url?: string; region?: number[] | null; box?: number[] | null; onRegion?: (region: number[] | null) => void }) {
  const anchor = useRef<number[] | null>(null)
  const [drag, setDrag] = useState<number[] | null>(null)
  const [loaded, setLoaded] = useState('')
  const [failed, setFailed] = useState('')
  const [aspect, setAspect] = useState(16 / 9)
  function point(event: PointerEvent<HTMLDivElement>) { const rect = event.currentTarget.getBoundingClientRect(); return [Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)), Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height))] }
  function rectangle(p: number[]) { const a = anchor.current!; return [Math.min(a[0], p[0]), Math.min(a[1], p[1]), Math.abs(a[0] - p[0]), Math.abs(a[1] - p[1])] }
  return <div className={`mc-frame ${onRegion ? 'can-select' : ''}`} style={{ aspectRatio: aspect }} aria-label={onRegion ? `${label}. Drag to select a region.` : label} onPointerDown={event => { if (!onRegion || loaded !== url || event.button !== 0) return; anchor.current = point(event); event.currentTarget.setPointerCapture(event.pointerId) }} onPointerMove={event => { if (anchor.current) setDrag(rectangle(point(event))) }} onPointerUp={event => { if (!anchor.current) return; const r = rectangle(point(event)); anchor.current = null; setDrag(null); onRegion?.(r[2] >= .02 && r[3] >= .02 ? r : null) }} onPointerCancel={() => { anchor.current = null; setDrag(null) }}>
    {url && <img key={url} src={url} alt="Video frame" draggable={false} onLoad={event => { setLoaded(url); setFailed(''); setAspect(event.currentTarget.naturalWidth / event.currentTarget.naturalHeight) }} onError={() => setFailed(url)} />}
    {(!url || loaded !== url) && <span className="mc-frame-status">{url && failed === url ? 'Frame unavailable. Try another time.' : 'Loading frame…'}</span>}
    {loaded === url && <Box box={drag || region || box} />}
  </div>
}

function CutPreview({ sourceUrl, targetUrl, aStart, aEnd, bStart, bEnd, onClose }: { sourceUrl: string; targetUrl: string; aStart: number; aEnd: number; bStart: number; bEnd: number; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const a = useRef<HTMLVideoElement>(null), b = useRef<HTMLVideoElement>(null)
  const phase = useRef<'a' | 'b' | 'stopped'>('stopped')
  const [visible, setVisible] = useState('a')
  const [error, setError] = useState('')
  const [ready, setReady] = useState(false)
  const [seeking, setSeeking] = useState(false)
  useEffect(() => {
    dialog.current?.showModal()
    let frame = 0
    const tick = () => {
      if (phase.current === 'a' && a.current && a.current.currentTime >= aEnd) {
        a.current.pause(); phase.current = 'b'; setVisible('b')
        b.current?.play().catch(() => { phase.current = 'stopped'; setError('Could not play the incoming clip.') })
      }
      if (phase.current === 'b' && b.current && b.current.currentTime >= bEnd) { b.current.pause(); phase.current = 'stopped' }
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(frame); phase.current = 'stopped' }
  }, [aEnd, bEnd])
  function prepare() {
    if (a.current && b.current && a.current.readyState >= 2 && b.current.readyState >= 2) setReady(true)
  }
  async function play() {
    if (!a.current || !b.current) return
    if (seeking) return
    setSeeking(true)
    phase.current = 'stopped'; a.current.pause(); b.current.pause(); setError('')
    try {
      await Promise.all([[a.current, aStart], [b.current, bStart]].map(async ([element, seconds]) => {
        const video = element as HTMLVideoElement, at = seconds as number
        if (Math.abs(video.currentTime - at) < .005) return
        await new Promise<void>((resolve, reject) => {
          const timer = setTimeout(() => { cleanup(); reject(new Error('Seeking timed out. Try again.')) }, 10000)
          const done = () => { cleanup(); resolve() }
          const cleanup = () => { clearTimeout(timer); video.removeEventListener('seeked', done) }
          video.addEventListener('seeked', done); video.currentTime = at
        })
      }))
      if (!a.current?.isConnected) return
      setVisible('a'); phase.current = 'a'; await a.current.play()
    } catch (err) { phase.current = 'stopped'; setError(errorMessage(err)) }
    finally { setSeeking(false) }
  }
  return <dialog ref={dialog} className="mc-preview" onCancel={onClose} onClose={onClose} aria-label="Match-cut preview"><div className="mc-frame-heading"><strong>A → B</strong><button className="lw-button" onClick={onClose}>Close</button></div><div className="mc-preview-stage"><video ref={a} src={sourceUrl} muted playsInline preload="auto" onLoadedData={prepare} onError={() => setError('Outgoing media could not be loaded.')} style={{ visibility: visible === 'a' ? 'visible' : 'hidden' }} /><video ref={b} src={targetUrl} muted playsInline preload="auto" onLoadedData={prepare} onError={() => setError('Incoming media could not be loaded.')} style={{ visibility: visible === 'b' ? 'visible' : 'hidden' }} /></div><div className="mc-pair-actions"><button className="lw-button lw-button-primary" disabled={!ready || seeking} onClick={play}>{ready ? 'Play / replay cut' : 'Loading clips…'}</button><small>Silent visual preview · verify exact cut frames in your editor.</small></div>{error && <p role="alert">{error}</p>}</dialog>
}
