import { useState } from 'react'
import dayjs from 'dayjs'
import type { DatePreset, DateRange } from '../types'

interface Props {
  value: DateRange
  onChange: (range: DateRange) => void
}

const PRESETS: { label: string; value: DatePreset }[] = [
  { label: 'Este mes', value: 'this_month' },
  { label: 'Últimos 3 meses', value: 'last_3_months' },
  { label: 'Este año', value: 'this_year' },
  { label: 'Últimos 12 meses', value: 'last_12_months' },
  { label: 'Personalizado', value: 'custom' },
]

function presetToRange(preset: DatePreset): DateRange {
  const today = dayjs()
  switch (preset) {
    case 'this_month':
      return { from: today.startOf('month').format('YYYY-MM-DD'), to: today.format('YYYY-MM-DD') }
    case 'last_3_months':
      return { from: today.subtract(3, 'month').format('YYYY-MM-DD'), to: today.format('YYYY-MM-DD') }
    case 'this_year':
      return { from: today.startOf('year').format('YYYY-MM-DD'), to: today.format('YYYY-MM-DD') }
    case 'last_12_months':
      return { from: today.subtract(12, 'month').format('YYYY-MM-DD'), to: today.format('YYYY-MM-DD') }
    default:
      return { from: today.startOf('year').format('YYYY-MM-DD'), to: today.format('YYYY-MM-DD') }
  }
}

function detectPreset(range: DateRange): DatePreset {
  const today = dayjs()
  if (
    range.from === today.startOf('month').format('YYYY-MM-DD') &&
    range.to === today.format('YYYY-MM-DD')
  ) return 'this_month'
  if (
    range.from === today.subtract(3, 'month').format('YYYY-MM-DD') &&
    range.to === today.format('YYYY-MM-DD')
  ) return 'last_3_months'
  if (
    range.from === today.startOf('year').format('YYYY-MM-DD') &&
    range.to === today.format('YYYY-MM-DD')
  ) return 'this_year'
  if (
    range.from === today.subtract(12, 'month').format('YYYY-MM-DD') &&
    range.to === today.format('YYYY-MM-DD')
  ) return 'last_12_months'
  return 'custom'
}

export function DateRangeFilter({ value, onChange }: Props) {
  const activePreset = detectPreset(value)
  const [showCustom, setShowCustom] = useState(activePreset === 'custom')

  function handlePreset(preset: DatePreset) {
    if (preset === 'custom') {
      setShowCustom(true)
    } else {
      setShowCustom(false)
      onChange(presetToRange(preset))
    }
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <div className="flex rounded-lg border border-gray-200 overflow-hidden">
        {PRESETS.filter((p) => p.value !== 'custom').map((p) => (
          <button
            key={p.value}
            onClick={() => handlePreset(p.value)}
            className={`px-3 py-1.5 text-xs font-medium transition-colors ${
              activePreset === p.value && !showCustom
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            {p.label}
          </button>
        ))}
        <button
          onClick={() => handlePreset('custom')}
          className={`px-3 py-1.5 text-xs font-medium transition-colors border-l border-gray-200 ${
            showCustom
              ? 'bg-blue-600 text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          Personalizado
        </button>
      </div>

      {showCustom && (
        <div className="flex items-center gap-1.5">
          <input
            type="date"
            value={value.from}
            max={value.to}
            onChange={(e) => onChange({ ...value, from: e.target.value })}
            className="rounded border border-gray-200 px-2 py-1 text-xs outline-none focus:border-blue-400"
          />
          <span className="text-xs text-gray-400">—</span>
          <input
            type="date"
            value={value.to}
            min={value.from}
            max={dayjs().format('YYYY-MM-DD')}
            onChange={(e) => onChange({ ...value, to: e.target.value })}
            className="rounded border border-gray-200 px-2 py-1 text-xs outline-none focus:border-blue-400"
          />
        </div>
      )}
    </div>
  )
}
