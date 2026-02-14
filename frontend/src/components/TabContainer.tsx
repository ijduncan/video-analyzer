import { useAnalysisStore, type ActiveTab } from '../stores/analysisStore'
import { TimelineView } from './TimelineView'
import { SceneDetail } from './SceneDetail'
import { FullSummary } from './FullSummary'
import { RawData } from './RawData'
import { CustomAnalysisView } from './CustomAnalysisView'
import { ShotMatchesView } from './ShotMatchesView'
import { SearchBar } from './SearchBar'

const TABS: { key: ActiveTab; label: string; shortcut: string }[] = [
  { key: 'timeline', label: 'Timeline', shortcut: '1' },
  { key: 'detail', label: 'Scene Detail', shortcut: '2' },
  { key: 'summary', label: 'Summary', shortcut: '3' },
  { key: 'matches', label: 'Matches', shortcut: '4' },
  { key: 'custom', label: 'Custom', shortcut: '5' },
  { key: 'raw', label: 'Raw Data', shortcut: '6' },
]

interface Props {
  seekTo: (seconds: number) => void
}

export function TabContainer({ seekTo }: Props) {
  const { activeTab, setActiveTab } = useAnalysisStore()

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Tab bar */}
      <div className="flex items-center border-b border-zinc-800 bg-zinc-900/50 px-2 shrink-0">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors relative ${
              activeTab === tab.key
                ? 'text-blue-400'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {tab.label}
            <span className="ml-1 text-[10px] text-zinc-600">{tab.shortcut}</span>
            {activeTab === tab.key && (
              <div className="absolute bottom-0 left-2 right-2 h-0.5 bg-blue-500 rounded-full" />
            )}
          </button>
        ))}
        <div className="flex-1" />
        <SearchBar />
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'timeline' && <TimelineView seekTo={seekTo} />}
        {activeTab === 'detail' && <SceneDetail />}
        {activeTab === 'summary' && <FullSummary />}
        {activeTab === 'matches' && <ShotMatchesView seekTo={seekTo} />}
        {activeTab === 'custom' && <CustomAnalysisView />}
        {activeTab === 'raw' && <RawData />}
      </div>
    </div>
  )
}
