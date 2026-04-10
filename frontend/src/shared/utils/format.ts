/**
 * Shared formatting utilities for numbers, currency, and quantities.
 *
 * Applies thousands separators manually via regex to avoid depending on
 * minimumGroupingDigits (Chrome 99+ / Firefox 98+). The es-ES CLDR default
 * (minimumGroupingDigits: 2) silently skips the separator for 4-digit numbers,
 * so Intl.NumberFormat alone is unreliable for values like 7.116 or 9.367.
 */

/** Insert dot every 3 digits from the right: 7116 → "7.116" */
function addThousandsDots(integer: string): string {
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

/** Format decimal part with comma separator: 0.85 → ",85" | 0 → "" */
function decimalPart(value: number, minDecimals: number, maxDecimals: number): string {
  if (maxDecimals === 0) return ''
  const factor = Math.pow(10, maxDecimals)
  const decimals = Math.round(Math.abs(value) * factor) % factor
  if (decimals === 0 && minDecimals === 0) return ''
  const raw = decimals.toString().padStart(maxDecimals, '0')
  // Trim trailing zeros down to minDecimals
  const trimmed = raw.replace(/0+$/, '').padEnd(minDecimals, '0')
  return trimmed ? `,${trimmed}` : ''
}

/** Format as euros without decimal places: 9366.85 → "9.367 €" */
export function formatEur(value: number): string {
  const rounded = Math.round(value)
  return `${addThousandsDots(rounded.toString())}\u00A0€`
}

/** Format as euros with exactly 2 decimal places: 9366.85 → "9.366,85 €" */
export function formatEurDecimals(value: number): string {
  const integer = Math.trunc(value).toString()
  const dec = decimalPart(value, 2, 2)
  return `${addThousandsDots(integer)}${dec}\u00A0€`
}

/** Format as euros with 2–4 decimal places (for unit prices): 2.6 → "2,60 €" */
export function formatEurFlexible(value: number): string {
  const integer = Math.trunc(value).toString()
  const dec = decimalPart(value, 2, 4)
  return `${addThousandsDots(integer)}${dec}\u00A0€`
}

/** Format as a plain number with 2 decimal places: 9366.85 → "9.366,85" */
export function formatNumber(value: number): string {
  const integer = Math.trunc(value).toString()
  const dec = decimalPart(value, 2, 2)
  return `${addThousandsDots(integer)}${dec}`
}

/** Format as a quantity with up to N decimal places, no trailing zeros: 9.5 → "9,5" */
export function formatQty(value: number, maxDecimals = 3): string {
  const integer = Math.trunc(value).toString()
  const dec = decimalPart(value, 0, maxDecimals)
  return `${addThousandsDots(integer)}${dec}`
}
