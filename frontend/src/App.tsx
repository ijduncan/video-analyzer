import { lazy, Suspense, useState } from 'react'
import { LibraryWorkspace } from './components/LibraryWorkspace'
const Analyzer = lazy(() => import('./components/AppShell').then(module => ({ default: module.AppShell })))

function App() {
  const [view, setView] = useState<'library' | 'analyzer'>('library')
  if (view === 'analyzer') return <div className="lw-analyzer-shell">
    <div className="lw-analyzer-back"><button onClick={() => setView('library')}>← Back to footage library</button><span>Detailed analysis workspace</span></div>
    <Suspense fallback={<div className="lw-app-loading">Opening analyzer…</div>}><Analyzer /></Suspense>
  </div>
  return <LibraryWorkspace onOpenAnalyzer={() => setView('analyzer')} />
}

export default App
