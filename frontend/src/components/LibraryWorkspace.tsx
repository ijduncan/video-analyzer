import { useCallback, useEffect, useRef, useState } from 'react'
import { getAsset, getCapabilities, getLibrary, getShots } from '../api/library'
import type { AssetDetail, Capabilities, LibraryAsset, LibraryResponse, LibraryShot } from '../api/library'
import { uploadVideo } from '../api/upload'
import { useSettingsStore } from '../stores/settingsStore'
import { AssetInspector } from './library/AssetInspector'
import { Icon } from './library/Icon'
import { bytes, duration, errorMessage, reviewLabel } from './library/format'
import './LibraryWorkspace.css'

export function LibraryWorkspace({ onOpenAnalyzer }: { onOpenAnalyzer: () => void }) {
  const [section, setSection] = useState<'library' | 'review'>('library')
  const [query, setQuery] = useState('')
  const [project, setProject] = useState('')
  const [review, setReview] = useState('')
  const [tag, setTag] = useState('')
  const [rights, setRights] = useState('')
  const [collection, setCollection] = useState('')
  const [searchMode, setSearchMode] = useState<'assets' | 'shots'>('assets')
  const [layout, setLayout] = useState<'grid' | 'list'>('grid')
  const [sort, setSort] = useState('default')
  const [library, setLibrary] = useState<LibraryResponse | null>(null)
  const [shotResults, setShotResults] = useState<LibraryShot[]>([])
  const [shotTotal, setShotTotal] = useState(0)
  const [pagination, setPagination] = useState({ context: '', page: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [selection, setSelection] = useState<{ id: string; seconds?: number; shot?: number } | null>(null)
  const [detail, setDetail] = useState<AssetDetail | null>(null)
  const [detailError, setDetailError] = useState('')
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [settings, setSettings] = useState(false)
  const [upload, setUpload] = useState<{ filename: string; current: number; total: number; percent: number } | null>(null)
  const [uploadNotice, setUploadNotice] = useState('')
  const [uploadError, setUploadError] = useState('')
  const [dragging, setDragging] = useState(false)
  const uploadLock = useRef(false)
  const dragDepth = useRef(0)
  const fileInput = useRef<HTMLInputElement>(null)
  const searchInput = useRef<HTMLInputElement>(null)
  const apiKey = useSettingsStore(state => state.apiKey)
  const refreshLibrary = useCallback(() => setRefresh(value => value + 1), [])
  const reviewFilter = review || (section === 'review' ? 'unreviewed' : '')
  const pageContext = JSON.stringify([query, project, reviewFilter, tag, rights, collection, searchMode, sort])
  const page = pagination.context === pageContext ? pagination.page : 0
  const pageSize = 60
  const selectedId = selection?.id

  useEffect(() => {
    let active = true
    getCapabilities().then(result => { if (active) setCapabilities(result) }).catch(() => {})
    return () => { active = false }
  }, [settings])

  useEffect(() => {
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setLoading(true); setError('')
      try {
        const [result, shots] = await Promise.all([
          getLibrary({ q: searchMode === 'assets' ? query : '', project, review_status: searchMode === 'assets' ? reviewFilter : '', tag: searchMode === 'assets' ? tag : '', rights_status: rights, collection, limit: pageSize, offset: searchMode === 'assets' ? page * pageSize : 0, sort: sort === 'default' ? (query ? 'relevance' : 'newest') : sort }, controller.signal),
          searchMode === 'shots' ? getShots({ q: query, project, review_status: reviewFilter, tag, rights_status: rights, collection, limit: pageSize, offset: page * pageSize }, controller.signal) : Promise.resolve(null),
        ])
        if (controller.signal.aborted) return
        setLibrary(result); setShotResults(shots?.shots || []); setShotTotal(shots?.total || 0)
        const resultTotal = searchMode === 'shots' ? shots?.total || 0 : result.total
        if (page > 0 && resultTotal <= page * pageSize) setPagination({ context: pageContext, page: Math.max(0, Math.ceil(resultTotal / pageSize) - 1) })
      } catch (err) { if (!controller.signal.aborted) setError(errorMessage(err)) }
      finally { if (!controller.signal.aborted) setLoading(false) }
    }, query ? 280 : 0)
    return () => { clearTimeout(timer); controller.abort() }
  }, [query, project, reviewFilter, tag, rights, collection, searchMode, sort, page, pageContext, refresh])

  useEffect(() => {
    if (!selectedId) return
    const controller = new AbortController()
    getAsset(selectedId, controller.signal).then(result => {
      if (!controller.signal.aborted) { setDetail(result); setDetailError('') }
    }).catch(err => { if (!controller.signal.aborted) setDetailError(errorMessage(err)) })
    return () => controller.abort()
  }, [selectedId, refresh])

  const analyzing = library?.assets.some(asset => ['queued', 'analyzing', 'processing'].includes(asset.status)) || (detail?.job_id === selectedId && detail?.status && ['queued', 'analyzing', 'processing'].includes(detail.status))
  useEffect(() => {
    if (!analyzing) return
    const interval = setInterval(refreshLibrary, 4000)
    return () => clearInterval(interval)
  }, [analyzing, refreshLibrary])

  useEffect(() => {
    function keydown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') { event.preventDefault(); searchInput.current?.focus() }
    }
    window.addEventListener('keydown', keydown)
    return () => window.removeEventListener('keydown', keydown)
  }, [])

  async function importFiles(files: FileList | File[]) {
    const incoming = Array.from(files)
    if (!incoming.length || uploadLock.current) return
    uploadLock.current = true; setUploadNotice(''); setUploadError('')
    let imported = 0
    const errors: string[] = []
    try {
      for (let index = 0; index < incoming.length; index++) {
        const file = incoming[index]
        setUpload({ filename: file.name, current: index + 1, total: incoming.length, percent: 0 })
        try {
          const result = await uploadVideo(file, percent => setUpload(previous => previous ? { ...previous, percent } : previous))
          imported++; refreshLibrary()
          if (incoming.length === 1) { setSelection({ id: result.job_id }); setDetailError('') }
        } catch (err) { errors.push(`${file.name}: ${errorMessage(err)}`) }
      }
      if (imported) setUploadNotice(`${imported} ${imported === 1 ? 'video' : 'videos'} imported. Open an asset to add metadata and run AI analysis.`)
      if (errors.length) setUploadError(errors.join('\n'))
    } finally { setUpload(null); uploadLock.current = false; if (fileInput.current) fileInput.current.value = '' }
  }

  function navigate(value: 'library' | 'review', projectValue = '') { setSection(value); setProject(projectValue); setReview(''); setTag(''); setQuery(''); setRights(''); setCollection('') }
  function clearFilters() { setQuery(''); setProject(''); setReview(''); setTag(''); setRights(''); setCollection('') }
  const assets = library?.assets || []
  const shots = shotResults
  const hasFilters = !!(query || project || review || tag || rights || collection)
  const count = searchMode === 'shots' ? shotTotal : library?.total || 0
  const connected = capabilities?.google_configured || !!apiKey
  return <div className={`lw-workspace ${selection ? 'has-inspector' : ''}`}>
    <aside className="lw-sidebar">
      <a className="lw-brand" href="#" onClick={event => { event.preventDefault(); navigate('library') }} aria-label="Frame library home"><span className="lw-brand-mark"><i /><i /><i /></span><span>FRAME<span className="lw-brand-sub">VIDEO INTELLIGENCE</span></span></a>
      <div className="lw-workspace-selector"><span className="lw-workspace-avatar">W</span><span><strong>Your workspace</strong><small>Creative library</small></span><span className="lw-local-pill">LOCAL</span></div>
      <span className="lw-nav-label">WORKSPACE</span>
      <nav className="lw-nav" aria-label="Workspace navigation"><button aria-label="Footage library" className={section === 'library' && !project ? 'is-active' : ''} onClick={() => navigate('library')}><Icon name="grid" /><span>Footage library</span>{library && <small>{library.stats.assets}</small>}</button><button aria-label="Review queue" className={section === 'review' ? 'is-active' : ''} onClick={() => navigate('review')}><Icon name="review" /><span>Review queue</span>{library && library.stats.assets - library.stats.reviewed > 0 && <span className="lw-nav-dot" />}</button><button aria-label="Open analyzer" onClick={onOpenAnalyzer}><Icon name="spark" /><span>Analyzer</span><Icon name="arrow" size={14} /></button></nav>
      <div className="lw-nav-section"><span className="lw-nav-label">PROJECTS</span>{library?.facets.projects.length ? <nav className="lw-nav lw-project-nav" aria-label="Projects">{library.facets.projects.map(name => <button className={project === name ? 'is-active' : ''} key={name} onClick={() => navigate('library', name)}><Icon name="folder" size={16} /><span>{name}</span></button>)}</nav> : <p className="lw-sidebar-empty">Projects appear here when you add them to your footage.</p>}</div>
      <div className="lw-sidebar-bottom"><div className="lw-workflow-note"><Icon name="film" size={21} /><p>Good footage deserves<br />another great edit.</p><span>Import. Understand. Rediscover.</span></div><button aria-label="Workspace settings" className="lw-settings-link" onClick={() => setSettings(true)}><Icon name="settings" size={17} /><span>Workspace settings</span></button><div className="lw-connection"><i className={connected ? 'is-connected' : ''} /><span>{connected ? 'Gemini connected' : 'AI connection needed'}</span></div></div>
    </aside>
    <main className="lw-main" onDragEnter={event => { event.preventDefault(); if (event.dataTransfer.types.includes('Files')) { dragDepth.current++; setDragging(true) } }} onDragOver={event => { if (event.dataTransfer.types.includes('Files')) event.preventDefault() }} onDragLeave={event => { event.preventDefault(); dragDepth.current--; if (dragDepth.current <= 0) { dragDepth.current = 0; setDragging(false) } }} onDrop={event => { event.preventDefault(); dragDepth.current = 0; setDragging(false); importFiles(event.dataTransfer.files) }}>
      <header className="lw-topbar"><div className="lw-breadcrumb">Workspace<Icon name="chevron" size={12} /><span>{section === 'review' ? 'Review queue' : 'Footage library'}</span>{project && <><Icon name="chevron" size={12} /><span>{project}</span></>}</div><div className="lw-topbar-right"><span className="lw-private-label"><Icon name="shield" size={13} />Your footage, organized</span><button className="lw-avatar" aria-label="Open workspace settings" onClick={() => setSettings(true)}>W</button></div></header>
      <div className="lw-library-content">
        <section className="lw-page-heading"><div><div className="lw-eyebrow">{section === 'review' ? 'CONFIDENCE IN EVERY CUT' : 'YOUR CREATIVE MEMORY'}</div><h1>{project || (section === 'review' ? 'Ready for a second look.' : 'Every frame. More potential.')}</h1><p>{section === 'review' ? 'Verify AI labels, refine your selects, and clear footage for reuse.' : 'Find the right footage. Keep the context. Make something new.'}</p></div><button className="lw-button lw-button-primary lw-import-button" onClick={() => fileInput.current?.click()} disabled={!!upload}><Icon name="plus" size={18} />{upload ? 'Importing…' : 'Import footage'}</button></section>
        <input ref={fileInput} className="lw-file-input" type="file" multiple accept="video/*,.mxf,.mkv,.avi,.mov,.mp4,.webm,.m4v,.mpg,.mpeg,.mts,.m2ts" aria-label="Select videos to import" onChange={event => { if (event.target.files) importFiles(event.target.files) }} />
        <div className="lw-stats-strip"><div><span>VIDEO ASSETS</span><strong>{library ? library.stats.assets.toLocaleString() : '—'}</strong></div><div><span>INDEXED SHOTS</span><strong>{library ? library.stats.shots.toLocaleString() : '—'}</strong></div><div><span>TOTAL RUNTIME</span><strong className="lw-runtime">{library ? duration(library.stats.duration_seconds) : '—'}</strong></div><div><span>REVIEWED</span><strong>{library ? library.stats.reviewed.toLocaleString() : '—'}<span className="lw-stat-context">{library ? `/ ${library.stats.assets}` : ''}</span></strong></div><div className="lw-stat-note"><span className="lw-small-spark"><Icon name="spark" size={19} /></span><span>Build a library that<br />works as hard as you do.</span></div></div>
        {upload && <div className="lw-upload-progress" role="status"><Icon name="upload" size={17} /><div><strong>Importing {upload.current} of {upload.total} · {upload.filename}</strong><span>{upload.percent === 100 ? 'Preparing media and metadata…' : `${upload.percent}% uploaded`}</span><progress max={100} value={upload.percent} /></div></div>}
        {uploadNotice && <div className="lw-notice" role="status"><Icon name="check" size={17} /><span>{uploadNotice}</span><button className="lw-icon-button" aria-label="Dismiss import notification" onClick={() => setUploadNotice('')}><Icon name="close" size={15} /></button></div>}
        {uploadError && <div className="lw-inline-error" role="alert">{uploadError}<button className="lw-text-button" onClick={() => setUploadError('')}>Dismiss</button></div>}
        <div className="lw-discovery"><div className="lw-search-row"><div className="lw-search"><Icon name="search" size={21} /><input ref={searchInput} value={query} onChange={event => setQuery(event.target.value)} placeholder={searchMode === 'shots' ? 'Search indexed shots, subjects, mood, camera movement…' : 'Search footage, tags, projects, descriptions…'} aria-label="Search footage" />{query ? <button className="lw-icon-button" aria-label="Clear search" onClick={() => setQuery('')}><Icon name="close" size={15} /></button> : <kbd>Ctrl K</kbd>}</div><div className="lw-segmented" aria-label="Search result type"><button className={searchMode === 'assets' ? 'is-active' : ''} aria-pressed={searchMode === 'assets'} onClick={() => setSearchMode('assets')}>Videos</button><button className={searchMode === 'shots' ? 'is-active' : ''} aria-pressed={searchMode === 'shots'} onClick={() => setSearchMode('shots')}>Shots</button></div></div>
          <div className="lw-filter-row"><div className="lw-filters"><label><Icon name="folder" size={14} /><select aria-label="Filter by project" value={project} onChange={event => setProject(event.target.value)}><option value="">All projects</option>{library?.facets.projects.map(name => <option key={name}>{name}</option>)}</select></label><label><Icon name="review" size={14} /><select aria-label="Filter by review status" value={reviewFilter} onChange={event => setReview(event.target.value)}>{section !== 'review' && <option value="">Any review status</option>}<option value="unreviewed">Unreviewed</option><option value="reviewed">Reviewed</option><option value="needs_changes">Needs changes</option></select></label><label><Icon name="bookmark" size={14} /><select aria-label="Filter by tag" value={tag} onChange={event => setTag(event.target.value)}><option value="">All tags</option>{library?.facets.tags.map(name => <option key={name}>{name}</option>)}</select></label><label><Icon name="shield" size={14} /><select aria-label="Filter by usage rights" value={rights} onChange={event => setRights(event.target.value)}><option value="">All usage rights</option><option value="cleared">Cleared for reuse</option><option value="restricted">Restricted</option><option value="unknown">Rights not verified</option></select></label><label><Icon name="bookmark" size={14} /><select aria-label="Filter by collection" value={collection} onChange={event => setCollection(event.target.value)}><option value="">All collections</option>{library?.facets.collections?.map(name => <option key={name}>{name}</option>)}</select></label>{hasFilters && <button className="lw-text-button" onClick={clearFilters}>Clear filters</button>}</div><span className="lw-search-note">Indexed keyword search<Icon name="info" size={13} /></span></div>
        </div>
        <div className="lw-results-heading"><div><h2>{section === 'review' ? 'Review footage' : searchMode === 'shots' ? 'Shot explorer' : query ? 'Search results' : 'All footage'}</h2><span className="lw-count">{library ? count : '—'}</span>{loading && library && <span className="lw-updating" role="status">Updating…</span>}</div><div className="lw-results-controls">{searchMode === 'assets' && <select aria-label="Sort footage" value={sort === 'newest' && !query ? 'default' : sort} onChange={event => setSort(event.target.value)}><option value="default">{query ? 'Relevance' : 'Newest first'}</option><option value="name">Name A–Z</option>{query && <option value="newest">Newest first</option>}</select>}<div className="lw-view-toggle"><button className={layout === 'grid' ? 'is-active' : ''} aria-label="Grid view" aria-pressed={layout === 'grid'} onClick={() => setLayout('grid')}><Icon name="grid" size={16} /></button><button className={layout === 'list' ? 'is-active' : ''} aria-label="List view" aria-pressed={layout === 'list'} onClick={() => setLayout('list')}><Icon name="list" size={17} /></button></div></div></div>
        {error ? <div className="lw-empty-state lw-error-state"><Icon name="info" size={30} /><h2>Your library couldn’t be loaded.</h2><p>{error}</p><button className="lw-button" onClick={refreshLibrary}><Icon name="refresh" size={16} />Try again</button></div> : loading && !library ? <div className="lw-asset-grid" aria-label="Loading library" aria-busy="true">{Array.from({ length: 6 }, (_, index) => <div className="lw-skeleton" key={index}><div /><span /><span /></div>)}</div> : !count ? <EmptyState hasLibrary={!!library?.stats.assets} filtered={hasFilters || section === 'review'} shots={searchMode === 'shots'} review={section === 'review'} onImport={() => fileInput.current?.click()} onClear={clearFilters} onVideos={() => setSearchMode('assets')} /> : <div className={`${layout === 'grid' ? 'lw-asset-grid' : 'lw-asset-list'} ${loading ? 'is-updating' : ''}`}>{searchMode === 'assets' ? assets.map(asset => <AssetCard key={asset.job_id} asset={asset} selected={selection?.id === asset.job_id} onClick={() => { setSelection({ id: asset.job_id }); setDetailError('') }} />) : shots.map(shot => <ShotCard key={`${shot.job_id}-${shot.shot_number}`} shot={shot} selected={selection?.id === shot.job_id && selection?.shot === shot.shot_number} onClick={() => { setSelection({ id: shot.job_id, seconds: shot.start_seconds, shot: shot.shot_number }); setDetailError('') }} />)}</div>}
        {!error && count > pageSize && <div className="lw-pagination"><span>{(page * pageSize + 1).toLocaleString()}–{Math.min((page + 1) * pageSize, count).toLocaleString()} of {count.toLocaleString()} {searchMode === 'shots' ? 'shots' : 'videos'}</span><div><button className="lw-button" disabled={page === 0 || loading} onClick={() => setPagination({ context: pageContext, page: page - 1 })}>Previous</button><button className="lw-button" disabled={(page + 1) * pageSize >= count || loading} onClick={() => setPagination({ context: pageContext, page: page + 1 })}>Next<Icon name="arrow" size={13} /></button></div></div>}<footer className="lw-library-footer"><span><Icon name="film" size={13} />A home for footage worth keeping.</span><span>{searchMode === 'shots' ? 'AI-generated shot boundaries · review before editing' : 'Original files + creative context'}</span></footer>
      </div>
      {dragging && <div className="lw-drop-overlay"><Icon name="upload" size={44} /><h2>Drop footage into your library.</h2><p>Import multiple videos at once.</p></div>}
    </main>
    {selection && (detail?.job_id === selection.id ? <AssetInspector key={`${selection.id}-${selection.shot || 'asset'}`} asset={detail} initialSeconds={selection.seconds} initialShot={selection.shot} capabilities={capabilities} onClose={() => setSelection(current => current?.id === selection.id ? null : current)} onRefresh={refreshLibrary} onConfigure={() => setSettings(true)} onRemoved={note => setUploadNotice(`Asset removed from your workspace.${note ? ` ${note}` : ''}`)} /> : <aside className="lw-inspector lw-inspector-loading"><button className="lw-icon-button" aria-label="Close asset details" onClick={() => setSelection(null)}><Icon name="close" /></button>{detailError ? <><p role="alert">{detailError}</p><button className="lw-button" onClick={refreshLibrary}>Try again</button></> : <p role="status">Opening footage…</p>}</aside>)}
    {settings && <SettingsDialog capabilities={capabilities} onClose={() => setSettings(false)} />}
  </div>
}

function AssetCard({ asset, selected, onClick }: { asset: LibraryAsset; selected: boolean; onClick: () => void }) {
  const isAnalyzing = ['queued', 'analyzing', 'processing'].includes(asset.status)
  return <button className={`lw-asset-card ${selected ? 'is-selected' : ''}`} onClick={onClick} aria-pressed={selected}>
    <div className="lw-card-image">{asset.thumbnail_url ? <img src={asset.thumbnail_url} alt="" loading="lazy" /> : <div className="lw-card-placeholder"><Icon name="film" size={32} /><span>{asset.mime_type?.split('/')[1]?.toUpperCase() || 'VIDEO'}</span></div>}<span className="lw-card-play"><Icon name="play" size={17} /></span><span className="lw-card-duration">{duration(asset.technical.duration_seconds)}</span>{isAnalyzing ? <span className="lw-card-status analyzing"><Icon name="spark" size={11} />{asset.status === 'queued' ? 'Queued' : 'Analyzing'}</span> : asset.status === 'error' ? <span className="lw-card-status error">Analysis failed</span> : asset.shot_count > 0 ? <span className="lw-card-status"><Icon name="spark" size={11} />Indexed</span> : <span className="lw-card-status pending">Ready to index</span>}</div>
    <div className="lw-card-content"><div className="lw-card-title"><h3 title={asset.metadata.title || asset.filename}>{asset.metadata.title || asset.filename}</h3><span className={`lw-review-dot ${asset.metadata.review_status}`} title={reviewLabel(asset.metadata.review_status)} /></div><div className="lw-card-subtitle"><span>{asset.metadata.project || 'No project'}</span><span>{asset.shot_count ? `${asset.shot_count} shots` : bytes(asset.size_bytes)}</span></div>{asset.match_context && <p className="lw-match-context">{asset.match_context}</p>}<div className="lw-card-tags">{asset.metadata.tags.length ? <>{asset.metadata.tags.slice(0, 3).map(tag => <span key={tag}>{tag}</span>)}{asset.metadata.tags.length > 3 && <span>+{asset.metadata.tags.length - 3}</span>}</> : <span className="lw-no-tags">Add tags to make it easier to find</span>}</div></div>
    <div className="lw-list-review"><span className={`lw-review-dot ${asset.metadata.review_status}`} />{reviewLabel(asset.metadata.review_status)}</div><Icon name="chevron" className="lw-list-chevron" size={16} />
  </button>
}
function ShotCard({ shot, selected, onClick }: { shot: LibraryShot; selected: boolean; onClick: () => void }) {
  return <button className={`lw-asset-card lw-shot-card ${selected ? 'is-selected' : ''}`} onClick={onClick} aria-pressed={selected}><div className="lw-card-image">{shot.thumbnail_url ? <img src={shot.thumbnail_url} alt="" loading="lazy" /> : <div className="lw-card-placeholder"><Icon name="film" size={32} /><span>SHOT {String(shot.shot_number).padStart(2, '0')}</span></div>}<span className="lw-card-play"><Icon name="play" size={17} /></span><span className="lw-card-duration">{shot.start_time} – {shot.end_time}</span><span className="lw-card-status">SHOT {String(shot.shot_number).padStart(2, '0')}</span></div><div className="lw-card-content"><div className="lw-card-title"><h3>{shot.scene_title || `Shot ${shot.shot_number}`}</h3><span className={`lw-review-dot ${shot.review_status}`} /></div><div className="lw-card-subtitle"><span title={shot.filename}>{shot.filename}</span></div><p className="lw-shot-description">{shot.visual_description}</p><div className="lw-card-tags">{[shot.shot_type, shot.mood, ...shot.tags].filter(Boolean).slice(0, 3).map((tag, index) => <span key={`${tag}-${index}`}>{tag}</span>)}</div></div><Icon name="chevron" className="lw-list-chevron" size={16} /></button>
}
function EmptyState({ hasLibrary, filtered, shots, review, onImport, onClear, onVideos }: { hasLibrary: boolean; filtered: boolean; shots: boolean; review: boolean; onImport: () => void; onClear: () => void; onVideos: () => void }) {
  if (hasLibrary) return <div className="lw-empty-state"><span className="lw-empty-icon"><Icon name={review ? 'review' : 'search'} size={26} /></span><h2>{review ? 'Nothing waiting in this view.' : shots && !filtered ? 'Your next discovery starts with an index.' : 'No footage found. Keep exploring.'}</h2><p>{review ? 'Try another review status to see footage that needs attention.' : shots && !filtered ? 'Open a video and run AI analysis to make its scenes and shots searchable.' : 'Try fewer keywords or clear your filters to widen the search.'}</p>{shots && !filtered ? <button className="lw-button" onClick={onVideos}>Browse videos<Icon name="arrow" size={16} /></button> : filtered && <button className="lw-button" onClick={onClear}>Clear filters</button>}</div>
  return <section className="lw-first-import"><div className="lw-empty-art" aria-hidden="true"><div className="lw-art-frame lw-art-back" /><div className="lw-art-frame lw-art-middle" /><div className="lw-art-frame lw-art-front"><span className="lw-art-cross top-left" /><span className="lw-art-cross bottom-right" /><Icon name="film" size={38} /><span className="lw-art-time">00:00:00:00</span></div><span className="lw-art-spark"><Icon name="spark" size={21} /></span></div><div className="lw-eyebrow">FROM HARD DRIVE TO CREATIVE POSSIBILITY</div><h2>Great footage shouldn’t get lost.</h2><p>Give your videos a home. Turn every scene into searchable<br className="lw-desktop-break" /> context, and find your next great shot in what you already have.</p><button className="lw-button lw-button-primary" onClick={onImport}><Icon name="upload" size={17} />Import your first footage</button><span className="lw-import-hint">Drag & drop videos here · multiple files welcome</span><div className="lw-empty-steps"><div><span>01</span><strong>Bring it together</strong><p>Original videos, organized<br />by client and project.</p></div><Icon name="arrow" size={17} /><div><span>02</span><strong>Understand every shot</strong><p>AI descriptions, subjects,<br />mood and camera movement.</p></div><Icon name="arrow" size={17} /><div><span>03</span><strong>Find it. Use it again.</strong><p>Search, review and export<br />with the context intact.</p></div></div></section>
}
function SettingsDialog({ capabilities, onClose }: { capabilities: Capabilities | null; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const apiKey = useSettingsStore(state => state.apiKey)
  const setApiKey = useSettingsStore(state => state.setApiKey)
  const [key, setKey] = useState(apiKey)
  useEffect(() => { dialog.current?.showModal() }, [])
  return <dialog ref={dialog} className="lw-settings-dialog" onCancel={onClose} onClose={onClose}><div className="lw-dialog-heading"><span className="lw-eyebrow">WORKSPACE SETTINGS</span><button className="lw-icon-button" aria-label="Close settings" onClick={onClose}><Icon name="close" /></button></div><span className="lw-settings-symbol"><Icon name="spark" size={25} /></span><h2>Your creative intelligence.</h2><p>Connect Gemini to analyze video. You can import, organize and review footage without an API key.</p><div className={`lw-provider-status ${capabilities?.google_configured ? 'is-connected' : ''}`}><i /><span>{capabilities?.google_configured ? 'A Gemini key is configured on your server.' : 'No server key detected. Add your own key below.'}</span></div><form onSubmit={event => { event.preventDefault(); setApiKey(key.trim()); onClose() }}><label className="lw-field">Gemini API key<input type="password" autoComplete="off" value={key} onChange={event => setKey(event.target.value)} placeholder={capabilities?.google_configured ? 'Optional personal key override' : 'Paste your Gemini API key'} /><span className="lw-field-hint">Stored in this browser and sent only to your analysis server. Leave blank to use the server key.</span></label><div className="lw-settings-models"><div><span>Video indexing</span><strong>{capabilities?.models.analysis || 'Server-configured Gemini model'}</strong></div><div><span>Creative analysis</span><strong>{capabilities?.models.deep || 'Server-configured Gemini model'}</strong></div></div><p className="lw-settings-note">Analysis sends video to Google and uses your API billing. Review your provider’s data terms for client footage.</p><div className="lw-dialog-actions"><button type="button" className="lw-button" onClick={onClose}>Cancel</button><button type="submit" className="lw-button lw-button-primary">Save settings<Icon name="check" size={16} /></button></div></form></dialog>
}
