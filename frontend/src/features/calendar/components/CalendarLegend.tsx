const LEGEND = [
  { color: '#3b82f6', label: 'Visitas técnicas' },
  { color: '#10b981', label: 'Presupuestos' },
  { color: '#f97316', label: 'Obras' },
  { color: '#8b5cf6', label: 'Eventos personalizados' },
]

export function CalendarLegend() {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1">
      {LEGEND.map(({ color, label }) => (
        <div key={label} className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
          <span className="text-xs text-gray-500">{label}</span>
        </div>
      ))}
    </div>
  )
}
