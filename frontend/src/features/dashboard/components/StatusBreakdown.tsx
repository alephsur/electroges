interface Segment {
  label: string
  value: number
  color: string
}

interface Props {
  title: string
  total: number
  segments: Segment[]
}

export function StatusBreakdown({ title, total, segments }: Props) {
  const nonZero = segments.filter((s) => s.value > 0)

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        <span className="text-xs text-gray-400 font-medium">{total} total</span>
      </div>

      {total === 0 ? (
        <p className="text-xs text-gray-400 py-4 text-center">Sin datos en el período</p>
      ) : (
        <>
          {/* Stacked bar */}
          <div className="h-2 rounded-full overflow-hidden flex gap-px mb-3">
            {nonZero.map((seg) => (
              <div
                key={seg.label}
                style={{
                  width: `${(seg.value / total) * 100}%`,
                  backgroundColor: seg.color,
                }}
              />
            ))}
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
            {segments.map((seg) => (
              <div key={seg.label} className="flex items-center justify-between gap-1">
                <div className="flex items-center gap-1.5 min-w-0">
                  <div
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: seg.color }}
                  />
                  <span className="text-xs text-gray-500 truncate">{seg.label}</span>
                </div>
                <span className="text-xs font-semibold text-gray-700 shrink-0">{seg.value}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
