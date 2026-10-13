import { useEffect, useRef, useState } from 'react'
import { getMediaExportOptions } from '../../api/library'
import { saveExport, savedExportMessage } from '../../api/exportSave'
import type { MediaExportFormat, MediaExportOptions } from '../../api/library'
import { errorMessage } from './format'
import { Icon } from './Icon'
import './MediaExportDialog.css'

export function MediaExportDialog({ media, onClose }: {
  media: { id: string; title: string }[]
  onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const lock = useRef(false)
  const downloadController = useRef<AbortController | null>(null)
  const [options, setOptions] = useState<MediaExportOptions | null>(null)
  const [retry, setRetry] = useState(0)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [title, setTitle] = useState('Video Analyzer selects')
  const [layout, setLayout] = useState<'timeline' | 'bin'>('timeline')
  const [format, setFormat] = useState<MediaExportFormat>('fcpxml')
  const [includeMetadata, setIncludeMetadata] = useState(true)
  const [writeSidecars, setWriteSidecars] = useState(false)
  const idsKey = JSON.stringify(media.map(item => item.id))
  const details = new Map(options?.items.map(item => [item.id, item]))
  const extension = format === 'premiere_xml' ? 'xml' : format
  const libraryOnly = format === 'premiere_xml' || format === 'fcpxml'

  useEffect(() => {
    const element = dialog.current!
    element.showModal()
    return () => { downloadController.current?.abort(); element.close() }
  }, [])
  useEffect(() => {
    const controller = new AbortController()
    getMediaExportOptions(JSON.parse(idsKey), controller.signal, format, layout).then(result => {
      if (!controller.signal.aborted) setOptions(result)
    }).catch(cause => { if (!controller.signal.aborted) setError(errorMessage(cause)) })
    return () => controller.abort()
  }, [idsKey, retry, format, layout])

  async function download() {
    if (lock.current || !options?.available || options.format !== format) return
    lock.current = true; setBusy(true); setError(''); setNotice('')
    const controller = new AbortController()
    downloadController.current = controller
    try {
      const result = await saveExport(`Video Analyzer media export.${includeMetadata ? 'zip' : extension}`, '/api/library/media-export', {
        job_ids: JSON.parse(idsKey), title: title.trim(), layout, format, include_metadata: includeMetadata,
        analysis_versions: Object.fromEntries(options.items.map(item => [item.id, item.analysis_version])),
      }, writeSidecars, controller.signal)
      if (!controller.signal.aborted) setNotice(savedExportMessage(result))
    } catch (cause) { if (!controller.signal.aborted) setError(errorMessage(cause)) }
    finally { lock.current = false; setBusy(false); downloadController.current = null }
  }

  return <dialog ref={dialog} className="lw-settings-dialog me-dialog" aria-labelledby="media-export-title" onCancel={event => { if (lock.current) event.preventDefault(); else onClose() }}>
    <header className="lw-dialog-heading"><h2 id="media-export-title">Export {media.length} selected media</h2><button className="lw-icon-button" aria-label="Close export" disabled={busy} onClick={onClose}><Icon name="close" /></button></header>
    <p>Import all selected original recordings into Premiere or Resolve. Your saved analysis becomes descriptions, logging notes and markers.</p>
    <fieldset disabled={busy}>
      <label className="me-field">Project / timeline name<input value={title} maxLength={200} onChange={event => setTitle(event.target.value)} /></label>
      <label className="me-field">Export format<select value={format} onChange={event => { setFormat(event.target.value as MediaExportFormat); setOptions(null); setError(''); setNotice(''); setLayout('timeline') }}><option value="fcpxml">Final Cut Pro XML · Resolve / Final Cut Pro</option><option value="otio">Resolve OTIO · OpenTimelineIO</option><option value="premiere_xml">Premiere XML · Premiere / Resolve</option><option value="edl">CMX3600 EDL · video only</option></select></label>
      <label className="me-field">Create<select value={layout} onChange={event => { setLayout(event.target.value as 'timeline' | 'bin'); setOptions(null); setError(''); setNotice('') }}><option value="timeline">Whole-media timeline{format === 'premiere_xml' || format === 'fcpxml' ? ' and media library' : ''}</option>{libraryOnly && <option value="bin">Media library only · {format === 'premiere_xml' ? 'Premiere' : 'Final Cut Pro'}</option>}</select></label>
      <p className="me-hint">Whole recordings, in selection order. {format === 'edl' ? 'EDL carries video cuts and comments; audio, transcripts and full metadata stay in the package. All sources must share one frame rate; maximum 999 items.' : 'Analysis clips are markers; they don’t split your recordings.'} {format === 'fcpxml' ? 'Recorded pixel aspect ratios are preserved, including 2× anamorphic.' : format === 'otio' ? 'Resolve reads pixel aspect and orientation from the originals. OTIO is an open timeline format, not a native DRT/DRP project.' : format === 'premiere_xml' ? 'The timeline uses the first selected source’s frame rate and dimensions.' : ''}</p>
      <label className="me-checkbox"><input type="checkbox" checked={includeMetadata} onChange={event => setIncludeMetadata(event.target.checked)} /><span>Include complete metadata package<small>One ZIP with the selected editor file, full analysis JSON, combined CSV, XMP sidecars and available SRT transcripts.</small></span></label>
      <label className="me-checkbox"><input type="checkbox" checked={writeSidecars} onChange={event => setWriteSidecars(event.target.checked)} /><span>Write XMP sidecars beside original media<small>Writes the complete saved analysis beside each original. Existing metadata is merged and backed up. Video files stay unchanged; editor files reference the originals.</small></span></label>
    </fieldset>
    <p className="me-hint">Originals stay in place; relink in the editor if they’ve moved or are offline. Each format has its own metadata support. Use the editor integration to sync other native metadata fields; the package retains the complete data.</p>
    {!options && !error && <p role="status">Checking selected media…</p>}
    <ul className="me-media-list">{media.map(item => {
      const detail = details.get(item.id)
      return <li key={item.id}><strong>{item.title}</strong>{detail && <>{!detail.available && <span className="me-error">{detail.reason}</span>}{!detail.analyzed && <small>No saved clip analysis; original media metadata will be included.</small>}{detail.partial && <small>Includes currently saved results; analysis may be incomplete.</small>}</>}</li>
    })}</ul>
    {options && !options.available && <p className="me-error" role="alert">{options.reason || 'Some media cannot be included in this format. Try another format or resolve the issues above. No media will be silently skipped.'}</p>}
    {error && <p className="me-error" role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    <footer className="lw-dialog-actions"><button className="lw-button" disabled={busy} onClick={() => { setError(''); setOptions(null); setRetry(value => value + 1) }}>Check again</button><button className="lw-button" disabled={busy} onClick={onClose}>Close</button><button className="lw-button lw-button-primary" disabled={busy || !options?.available || options.format !== format || !title.trim()} onClick={() => void download()}><Icon name="download" size={16} />{busy ? 'Preparing export…' : includeMetadata ? 'Save editor package…' : `Save ${format === 'premiere_xml' ? 'XML' : format.toUpperCase()}…`}</button></footer>
  </dialog>
}
