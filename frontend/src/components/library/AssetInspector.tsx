import { useRef, useState } from 'react'
import { analyzeAsset, cancelAnalysis, deleteAsset, exportUrl, saveMetadata, saveShot } from '../../api/library'
import type { AssetDetail, AssetMetadata, Capabilities, ReviewStatus, ShotAnnotation } from '../../api/library'
import type { Shot } from '../../api/types'
import { useSettingsStore } from '../../stores/settingsStore'
import { Icon } from './Icon'
import { bytes, duration, errorMessage, reviewLabel, splitTags, timestamp } from './format'

interface Props {
  asset: AssetDetail
  initialSeconds?: number
  initialShot?: number
  capabilities: Capabilities | null
  onClose: () => void
  onRefresh: () => void
  onConfigure: () => void
  onRemoved?: (note: string | null) => void
}

export function AssetInspector({ asset, initialSeconds, initialShot, capabilities, onClose, onRefresh, onConfigure, onRemoved }: Props) {
  const [tab, setTab] = useState<'metadata' | 'shots' | 'analysis'>(initialShot ? 'shots' : 'metadata')
  const [draft, setDraft] = useState<AssetMetadata>(() => ({ ...asset.metadata }))
  const [baseline, setBaseline] = useState(() => JSON.stringify(asset.metadata))
  const [tags, setTags] = useState(() => asset.metadata.tags.join(', '))
  const [collections, setCollections] = useState(() => asset.metadata.collections.join(', '))
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState(false)
  const [mode, setMode] = useState<'flash_only' | 'flash_pro'>('flash_only')
  const [fps, setFps] = useState<1 | 4>(1)
  const [prompt, setPrompt] = useState('')
  const [starting, setStarting] = useState(false)
  const [confirmRemoval, setConfirmRemoval] = useState(false)
  const [removing, setRemoving] = useState(false)
  const apiKey = useSettingsStore(state => state.apiKey)
  const video = useRef<HTMLVideoElement>(null)
  const body = useRef<HTMLDivElement>(null)
  const busy = ['queued', 'analyzing', 'processing'].includes(asset.status) || starting
  const removalDisabled = busy || removing || saving || asset.status === 'deleting'
  const warnings = [...new Set([...(asset.warnings || []), ...(asset.flash?.analysis_warnings || [])])]
  const metadata = { ...draft, tags: splitTags(tags), collections: splitTags(collections) }
  const dirty = JSON.stringify(metadata) !== baseline
  const shots = asset.flash?.scenes.flatMap(scene => scene.shots.map(shot => ({ ...shot, scene_title: scene.scene_title }))) || []
  function field<K extends keyof AssetMetadata>(name: K, value: AssetMetadata[K]) { setDraft(previous => ({ ...previous, [name]: value })) }
  async function save() {
    setSaving(true); setError(''); setNotice('')
    try {
      const result = await saveMetadata(asset.job_id, metadata)
      setDraft(result.metadata); setBaseline(JSON.stringify(result.metadata))
      setTags(result.metadata.tags.join(', ')); setCollections(result.metadata.collections.join(', '))
      setNotice('Saved.'); onRefresh()
    } catch (err) { setError(errorMessage(err)) } finally { setSaving(false) }
  }
  async function analyze() {
    if (busy || removing || asset.status === 'deleting') return
    if (!capabilities?.google_configured && !apiKey) { onConfigure(); return }
    setTab('analysis'); body.current?.scrollTo({ top: 0 })
    setStarting(true); setError(''); setNotice('')
    try { await analyzeAsset(asset.job_id, mode, fps, prompt); onRefresh() }
    catch (err) { setError(errorMessage(err)) }
    finally { setStarting(false) }
  }
  async function cancel() {
    setError('')
    try { await cancelAnalysis(asset.job_id); onRefresh() } catch (err) { setError(errorMessage(err)) }
  }
  async function remove() {
    if (removalDisabled) return
    setRemoving(true); setError(''); setNotice('')
    const player = video.current
    if (player) { player.pause(); player.removeAttribute('src'); player.load() }
    try {
      const result = await deleteAsset(asset.job_id)
      onClose(); onRefresh(); onRemoved?.(result.note)
    } catch (err) {
      setError(errorMessage(err)); body.current?.scrollTo({ top: 0 })
      if (player?.isConnected && asset.preview_url) { player.src = asset.preview_url; player.load() }
    } finally { setRemoving(false) }
  }
  function seek(seconds: number) {
    if (video.current) { video.current.currentTime = seconds; video.current.play().catch(() => {}) }
  }
  async function download(format: 'json' | 'csv' | 'xmp' | 'srt' | 'edl' | 'fcpxml') {
    setError('')
    try {
      const response = await fetch(exportUrl(asset.job_id, format))
      if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(typeof body?.detail === 'string' ? body.detail : 'Export failed. Please try again.') }
      const objectUrl = URL.createObjectURL(await response.blob())
      const anchor = document.createElement('a')
      anchor.href = objectUrl; anchor.download = `${(asset.metadata.title || asset.filename).replace(/\.[^.]+$/, '')}.${format}`
      anchor.click(); setTimeout(() => URL.revokeObjectURL(objectUrl), 1000); setExporting(false)
    } catch (err) { setError(errorMessage(err)) }
  }
  return <aside className="lw-inspector" aria-label="Footage details">
    <div className="lw-inspector-heading"><h2 className="truncate" title={asset.filename} style={{ margin: 0, fontSize: 13, fontWeight: 500 }}>{asset.metadata.title || asset.filename}</h2><button className="lw-icon-button" aria-label="Close asset details" onClick={onClose}><Icon name="close" /></button></div>
    <div className="lw-preview">
      {asset.preview_url ? <video ref={video} src={asset.preview_url} poster={asset.thumbnail_url || undefined} controls preload="metadata" onLoadedMetadata={() => { if (video.current && initialSeconds != null) video.current.currentTime = initialSeconds }} /> : <div className="lw-no-preview"><Icon name="film" size={32} /><span>{asset.youtube_url ? 'Source video on YouTube' : 'Preview unavailable for this format'}</span>{asset.youtube_url && <a href={asset.youtube_url} target="_blank" rel="noreferrer">Open source ↗</a>}</div>}
    </div>
    <div className="lw-primary-action">
      <button className="lw-button lw-button-primary lw-analyze-primary" disabled={busy || removing || asset.status === 'deleting'} onClick={analyze}>
        <Icon name="spark" size={20} />
        {busy ? asset.status === 'queued' ? 'Queued…' : 'Analyzing…' : !capabilities?.google_configured && !apiKey ? 'Connect Gemini' : asset.status === 'error' ? 'Retry analysis' : asset.flash ? 'Analyze again' : 'Analyze video'}
      </button>
    </div>
    <div className="lw-inspector-tabs" role="tablist" aria-label="Asset information">{(['metadata', 'shots', 'analysis'] as const).map(value => <button id={`asset-tab-${value}`} aria-controls={`asset-panel-${value}`} role="tab" tabIndex={tab === value ? 0 : -1} onKeyDown={event => { const items = ['metadata', 'shots', 'analysis'] as const; const current = items.indexOf(tab); const next = event.key === 'ArrowRight' ? (current + 1) % items.length : event.key === 'ArrowLeft' ? (current + items.length - 1) % items.length : event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : -1; if (next >= 0) { event.preventDefault(); setTab(items[next]); document.getElementById(`asset-tab-${items[next]}`)?.focus() } }} aria-selected={tab === value} onClick={() => setTab(value)} key={value}>{value === 'shots' ? 'Shots' : value === 'analysis' ? 'Analysis' : 'Metadata'}</button>)}</div>
    <div ref={body} className="lw-inspector-body" role="tabpanel" id={`asset-panel-${tab}`} aria-labelledby={`asset-tab-${tab}`}>
      {error && <div className="lw-inline-error" role="alert">{error}</div>}{notice && <div className="lw-inline-success" role="status">{notice}</div>}
      {warnings.length > 0 && <details className="lw-details"><summary>Analysis notes<Icon name="down" size={14} /></summary><div className="lw-analysis-warning">{warnings.map(warning => <p key={warning}>{warning}</p>)}</div></details>}
      {tab === 'metadata' && <>
        {asset.summary && <details className="lw-details"><summary>AI summary<Icon name="down" size={14} /></summary><p className="lw-panel-description">{asset.summary}</p></details>}
        <label className="lw-field">Title<input value={draft.title} onChange={event => field('title', event.target.value)} placeholder={asset.filename} /></label>
        <label className="lw-field">Tags<textarea rows={2} value={tags} onChange={event => setTags(event.target.value)} placeholder="Separate tags with commas" /></label>
        <label className="lw-field">Project<input value={draft.project} onChange={event => field('project', event.target.value)} /></label>
        <div className="lw-field-pair"><label className="lw-field">Review<select value={draft.review_status} onChange={event => field('review_status', event.target.value as ReviewStatus)}><option value="unreviewed">Unreviewed</option><option value="reviewed">Reviewed</option><option value="needs_changes">Needs changes</option></select></label><label className="lw-field">Usage rights<select title="Set by your team; AI does not verify usage rights." value={draft.rights_status} onChange={event => field('rights_status', event.target.value as AssetMetadata['rights_status'])}><option value="unknown">Unverified</option><option value="cleared">Cleared</option><option value="restricted">Restricted</option></select></label></div>
        <details className="lw-details"><summary>More metadata<Icon name="down" size={14} /></summary><div style={{ paddingTop: 14 }}>
          <label className="lw-field">Client<input value={draft.client} onChange={event => field('client', event.target.value)} /></label>
          <label className="lw-field">Campaign<input value={draft.campaign} onChange={event => field('campaign', event.target.value)} /></label>
          <label className="lw-field">Collections<input value={collections} onChange={event => setCollections(event.target.value)} placeholder="Separate collections with commas" /></label>
          <label className="lw-field">Notes<textarea rows={3} value={draft.notes} onChange={event => field('notes', event.target.value)} /></label>
        </div></details>
        <details className="lw-details"><summary>File details<Icon name="down" size={14} /></summary><dl><div><dt>Filename</dt><dd>{asset.filename}</dd></div><div><dt>Duration</dt><dd>{duration(asset.technical.duration_seconds)}</dd></div><div><dt>Size</dt><dd>{bytes(asset.size_bytes)}</dd></div>{asset.technical.width != null && <div><dt>Resolution</dt><dd>{asset.technical.width} × {asset.technical.height}</dd></div>}{asset.technical.frame_rate != null && <div><dt>Frame rate</dt><dd>{Number(asset.technical.frame_rate).toFixed(2).replace(/\.00$/, '')} fps</dd></div>}<div><dt>Format</dt><dd>{asset.mime_type || 'Unknown'}</dd></div><div><dt>Codec</dt><dd>{asset.technical.codec || 'Unknown'}</dd></div><div><dt>Source timecode</dt><dd>{asset.technical.source_timecode || 'Not embedded'}</dd></div><div><dt>Audio</dt><dd>{asset.technical.has_audio == null ? 'Unknown' : asset.technical.has_audio ? 'Present' : 'No audio track'}</dd></div><div><dt>Imported</dt><dd>{asset.created_at ? new Date(asset.created_at).toLocaleDateString() : 'Unknown'}</dd></div></dl><div className="lw-remove-section">{confirmRemoval ? <div className="lw-remove-confirm" role="group" aria-label="Confirm asset removal"><strong>Remove this asset?</strong><p>Permanently removes the uploaded copy, metadata, thumbnails and analysis from this workspace. Your source file outside this workspace stays in place.</p><div><button className="lw-button" disabled={removing} onClick={() => setConfirmRemoval(false)}>Cancel</button><button className="lw-button lw-button-danger" disabled={removalDisabled} onClick={remove}>{removing ? 'Removing…' : 'Remove asset'}</button></div></div> : <button className="lw-text-button lw-remove-link" disabled={removalDisabled} onClick={() => setConfirmRemoval(true)}>Remove asset</button>}{busy && <small>Finish or cancel analysis before removing.</small>}</div></details>
      </>}
      {tab === 'shots' && <>
        {shots.length ? shots.map(shot => <ShotEditor key={`${shot.shot_number}-${shot.start_time}-${shot.end_time}`} jobId={asset.job_id} shot={shot} annotation={asset.shot_annotations?.[String(shot.shot_number)]} selected={shot.shot_number === initialShot} onSeek={() => seek(timestamp(shot.start_time))} onRefresh={onRefresh} />) : <div className="lw-panel-empty"><p>No shots yet.</p></div>}
      </>}
      {tab === 'analysis' && <>
        {busy && <div className="lw-analysis-progress" role="status"><div className="lw-progress-orbit" /><div><strong>{asset.status === 'queued' ? 'Queued' : 'Analyzing…'}</strong>{asset.progress && <p>{typeof asset.progress === 'string' ? asset.progress : asset.progress.message}</p>}</div></div>}
        {asset.error && <div className="lw-inline-error">{asset.error}</div>}
        {busy && <button className="lw-text-button lw-cancel-analysis" onClick={cancel}>Cancel analysis</button>}
        <label className="lw-field">Analysis<select value={mode} onChange={event => setMode(event.target.value as 'flash_only' | 'flash_pro')}><option value="flash_only">Shots and tags</option><option value="flash_pro">Full analysis</option></select></label>
        <details className="lw-details"><summary>Options<Icon name="down" size={14} /></summary><div style={{ paddingTop: 14 }}>
          <label className="lw-field">Sampling<select value={fps} onChange={event => setFps(Number(event.target.value) as 1 | 4)}><option value={1}>1 fps</option><option value={4}>4 fps · fast action</option></select><span className="lw-field-hint">Higher sampling uses more tokens. Short cuts may be missed.</span></label>
          <label className="lw-field">Instructions<textarea rows={3} value={prompt} onChange={event => setPrompt(event.target.value)} placeholder="Optional analysis instructions" /></label>
          <p className="lw-model-note">{capabilities?.models ? `${capabilities.models.analysis}${mode === 'flash_pro' ? ` + ${capabilities.models.deep}` : ''}` : 'Gemini'}</p>
        </div></details>
        <p className="lw-model-note">Gemini API charges apply.</p>
        {asset.analysis_config?.analysis_model && <details className="lw-details"><summary>Run details<Icon name="down" size={14} /></summary><dl><div><dt>Index model</dt><dd>{asset.analysis_config.analysis_model}</dd></div>{asset.analysis_config.mode === 'flash_pro' && <div><dt>Creative model</dt><dd>{asset.analysis_config.deep_model}</dd></div>}<div><dt>Sampling</dt><dd>{asset.analysis_config.fps} frame(s) per second</dd></div><div><dt>Schema</dt><dd>{asset.flash?.schema_version || 'Legacy'}</dd></div><div><dt>Started</dt><dd>{asset.analysis_config.started_at ? new Date(asset.analysis_config.started_at).toLocaleString() : 'Not recorded'}</dd></div><div><dt>Timestamp precision</dt><dd>Approximate · verify against source before editing</dd></div>{asset.cost_estimate && <div><dt>Estimated API cost</dt><dd>{asset.cost_estimate.estimated_cost_usd == null ? 'Unavailable for this model or usage record' : `$${asset.cost_estimate.estimated_cost_usd.toFixed(4)} USD`}</dd></div>}</dl>{asset.cost_estimate?.warnings?.map(warning => <p className="lw-model-note" key={warning}>{warning}</p>)}</details>}
        {asset.video_summary && <details className="lw-details"><summary>Summary<Icon name="down" size={14} /></summary><p className="lw-panel-description">{asset.video_summary.executive_summary}</p><dl><div><dt>Visual style</dt><dd>{asset.video_summary.visual_style}</dd></div><div><dt>Audience</dt><dd>{asset.video_summary.target_audience}</dd></div></dl></details>}
        {!!asset.deep?.length && <details className="lw-details"><summary>Scenes<Icon name="down" size={14} /></summary>{asset.deep.map(scene => <details className="lw-details" key={scene.scene_number}><summary>Scene {scene.scene_number}<Icon name="down" size={14} /></summary><dl>{Object.entries(scene.visual_analysis || {}).filter(([, value]) => value).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{value}</dd></div>)}{scene.narrative_context?.story_beat && <div><dt>Story beat</dt><dd>{scene.narrative_context.story_beat}</dd></div>}{scene.audio_analysis?.dialogue && <div><dt>Dialogue notes</dt><dd>{scene.audio_analysis.dialogue}</dd></div>}</dl></details>)}</details>}
        {!!asset.transcript?.length && <details className="lw-details"><summary>Transcript<Icon name="down" size={14} /></summary>{asset.transcript.map((segment, index) => <button className="lw-transcript-line" key={index} onClick={() => seek(segment.start_seconds ?? timestamp(segment.start_time || '0'))}><time>{segment.start_time || duration(segment.start_seconds)}</time><span>{segment.speaker && <strong>{segment.speaker}: </strong>}{segment.text}</span></button>)}</details>}
      </>}
    </div>
    <div className="lw-inspector-footer"><div className="lw-export-wrap"><button className="lw-button" onClick={() => setExporting(!exporting)} aria-expanded={exporting}><Icon name="download" size={16} />Export<Icon name="down" size={12} /></button>{exporting && <div className="lw-export-menu">{(['json', 'csv', 'xmp', 'srt', 'edl', 'fcpxml'] as const).map(format => <button key={format} onClick={() => download(format)}><strong>{format.toUpperCase()}</strong><span>{{ json: 'Metadata', csv: 'Shot list', xmp: 'Sidecar', srt: 'Subtitles', edl: 'Edit list', fcpxml: 'Timeline' }[format]}</span></button>)}</div>}</div>{tab === 'metadata' ? <button className="lw-button lw-button-primary" disabled={!dirty || saving || removing} onClick={save}>{saving ? 'Saving…' : dirty ? 'Save' : 'Saved'}<Icon name="check" size={15} /></button> : <button className="lw-button" onClick={() => setTab('metadata')}>Metadata<Icon name="arrow" size={15} /></button>}</div>
  </aside>
}

function ShotEditor({ jobId, shot, annotation, selected, onSeek, onRefresh }: {
  jobId: string
  shot: Shot & { scene_title: string }
  annotation?: ShotAnnotation
  selected: boolean
  onSeek: () => void
  onRefresh: () => void
}) {
  const [expanded, setExpanded] = useState(selected)
  const [tags, setTags] = useState(annotation?.tags.join(', ') || '')
  const [notes, setNotes] = useState(annotation?.notes || '')
  const [review, setReview] = useState<ReviewStatus>(annotation?.review_status || 'unreviewed')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  async function save() {
    setSaving(true); setMessage(''); setError('')
    try { await saveShot(jobId, shot.shot_number, { tags: splitTags(tags), notes, review_status: review }); setMessage('Saved.'); onRefresh() }
    catch (err) { setError(errorMessage(err)) } finally { setSaving(false) }
  }
  return <div className={`lw-shot-detail ${selected ? 'is-selected' : ''}`}>
    <button className="lw-shot-jump" onClick={onSeek} aria-label={`Play shot ${shot.shot_number} at ${shot.start_time}`}><span className="lw-shot-play"><Icon name="play" size={15} /></span><span><strong>Shot {String(shot.shot_number).padStart(2, '0')}</strong><time>{shot.start_time} — {shot.end_time}</time></span><span className={`lw-review-dot ${review}`} title={reviewLabel(review)} /></button>
    <p>{shot.visual_description}</p><div className="lw-tags">{[shot.shot_type, shot.camera_movement, shot.mood].filter(Boolean).map((value, i) => <span key={`${value}-${i}`}>{value}</span>)}</div>
    {!!shot.tags?.length && <details className="lw-details"><summary>AI tags<Icon name="down" size={13} /></summary><div className="lw-tags">{shot.tags.map(tag => <span key={tag}>{tag}</span>)}</div></details>}
    {(shot.evidence?.length || shot.visible_text?.length || shot.logos?.length || shot.subjects?.length || shot.actions?.length || shot.location || shot.transcript || shot.audio_notes) ? <details className="lw-details lw-shot-evidence"><summary>Details<Icon name="down" size={13} /></summary><dl>{shot.subjects?.length > 0 && <div><dt>Subjects</dt><dd>{shot.subjects.join(', ')}</dd></div>}{!!shot.actions?.length && <div><dt>Actions</dt><dd>{shot.actions.join(', ')}</dd></div>}{!!shot.visible_text?.length && <div><dt>Visible text</dt><dd>{shot.visible_text.join(' · ')}</dd></div>}{!!shot.logos?.length && <div><dt>Potential logos</dt><dd>{shot.logos.join(', ')}</dd></div>}{shot.location && <div><dt>Location description</dt><dd>{shot.location}</dd></div>}{shot.transcript && <div><dt>Model transcript</dt><dd>{shot.transcript}</dd></div>}{shot.audio_notes && <div><dt>Audio observations</dt><dd>{shot.audio_notes}</dd></div>}{shot.evidence?.map((evidence, index) => <div key={index}><dt>{evidence.modality} · {evidence.start_time}–{evidence.end_time}</dt><dd>{evidence.description}</dd></div>)}</dl><p className="lw-model-note">Model observations are unverified. Shot timestamps are approximate.{shot.confidence != null ? ' Model confidence is uncalibrated and is not a reliability score.' : ''}</p></details> : null}
    {!!shot.analysis_warnings?.length && <details className="lw-details"><summary>Notes<Icon name="down" size={13} /></summary><div className="lw-analysis-warning">{shot.analysis_warnings.map(warning => <p key={warning}>{warning}</p>)}</div></details>}
    <button className="lw-text-button" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>{expanded ? 'Close edit' : 'Edit'}<Icon name="down" size={13} /></button>
    {expanded && <div className="lw-shot-fields"><label className="lw-field">Your tags<input value={tags} onChange={event => setTags(event.target.value)} placeholder="Comma-separated tags" /></label><label className="lw-field">Notes<textarea rows={2} value={notes} onChange={event => setNotes(event.target.value)} /></label><label className="lw-field">Review<select value={review} onChange={event => setReview(event.target.value as ReviewStatus)}><option value="unreviewed">Unreviewed</option><option value="reviewed">Reviewed</option><option value="needs_changes">Needs changes</option></select></label><button className="lw-button" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save shot'}</button>{message && <small className="lw-inline-success" role="status">{message}</small>}{error && <small className="lw-inline-error" role="alert">{error}</small>}</div>}
  </div>
}
