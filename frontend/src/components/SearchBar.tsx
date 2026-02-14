import { useAnalysisStore } from '../stores/analysisStore'

export function SearchBar() {
  const { searchQuery, setSearchQuery } = useAnalysisStore()

  return (
    <input
      type="text"
      value={searchQuery}
      onChange={(e) => setSearchQuery(e.target.value)}
      placeholder="Search scenes..."
      className="w-48 px-3 py-1.5 text-xs bg-zinc-800 border border-zinc-700 rounded text-zinc-300 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-500"
    />
  )
}
