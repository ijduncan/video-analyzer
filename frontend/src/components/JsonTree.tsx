import { useState } from 'react'

interface Props {
  data: unknown
  depth?: number
}

export function JsonTree({ data, depth = 0 }: Props) {
  if (data === null || data === undefined) {
    return <span className="text-zinc-500">null</span>
  }

  if (typeof data === 'string') {
    return <span className="text-emerald-400">"{data}"</span>
  }

  if (typeof data === 'number') {
    return <span className="text-amber-400">{data}</span>
  }

  if (typeof data === 'boolean') {
    return <span className="text-blue-400">{String(data)}</span>
  }

  if (Array.isArray(data)) {
    return <CollapsibleArray data={data} depth={depth} />
  }

  if (typeof data === 'object') {
    return <CollapsibleObject data={data as Record<string, unknown>} depth={depth} />
  }

  return <span className="text-zinc-400">{String(data)}</span>
}

function CollapsibleObject({ data, depth }: { data: Record<string, unknown>; depth: number }) {
  const [isOpen, setIsOpen] = useState(depth < 2)
  const keys = Object.keys(data)

  if (keys.length === 0) return <span className="text-zinc-500">{'{}'}</span>

  return (
    <span>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="text-zinc-500 hover:text-zinc-300"
      >
        {isOpen ? '▼' : '▶'} {'{'}{!isOpen && `${keys.length} keys}`}
      </button>
      {isOpen && (
        <div className="ml-4 border-l border-zinc-800 pl-2">
          {keys.map((key) => (
            <div key={key} className="my-0.5">
              <span className="text-violet-400">"{key}"</span>
              <span className="text-zinc-500">: </span>
              <JsonTree data={data[key]} depth={depth + 1} />
            </div>
          ))}
        </div>
      )}
      {isOpen && <span className="text-zinc-500">{'}'}</span>}
    </span>
  )
}

function CollapsibleArray({ data, depth }: { data: unknown[]; depth: number }) {
  const [isOpen, setIsOpen] = useState(depth < 2)

  if (data.length === 0) return <span className="text-zinc-500">[]</span>

  return (
    <span>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="text-zinc-500 hover:text-zinc-300"
      >
        {isOpen ? '▼' : '▶'} [{!isOpen && `${data.length} items]`}
      </button>
      {isOpen && (
        <div className="ml-4 border-l border-zinc-800 pl-2">
          {data.map((item, i) => (
            <div key={i} className="my-0.5">
              <span className="text-zinc-600 text-[10px] mr-1">{i}</span>
              <JsonTree data={item} depth={depth + 1} />
            </div>
          ))}
        </div>
      )}
      {isOpen && <span className="text-zinc-500">]</span>}
    </span>
  )
}
