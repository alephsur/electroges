export type BudgetStatus = 'draft' | 'sent' | 'accepted' | 'rejected' | 'expired'
export type BudgetLineType = 'labor' | 'material' | 'other'
export type MarginStatus = 'red' | 'amber' | 'green'

export interface BudgetLine {
  id: string
  budget_id: string
  line_type: BudgetLineType
  sort_order: number
  description: string
  inventory_item_id: string | null
  inventory_item_name: string | null
  quantity: number
  unit: string | null
  unit_price: number
  unit_cost: number
  line_discount_pct: number
  subtotal: number
  margin_pct: number
  margin_amount: number
}

export interface BudgetTotals {
  subtotal_before_discount: number
  discount_amount: number
  taxable_base: number
  tax_amount: number
  total: number
  total_cost: number
  gross_margin: number
  gross_margin_pct: number
  margin_status: MarginStatus
}

export interface BudgetVersionInfo {
  id: string
  version: number
  budget_number: string
  status: string
  effective_status: string
  issue_date: string
  total: number
  is_latest_version: boolean
}

export interface BudgetSummary {
  id: string
  budget_number: string
  version: number
  is_latest_version: boolean
  customer_id: string | null
  customer_name: string | null
  site_visit_id: string | null
  status: BudgetStatus
  effective_status: string
  issue_date: string
  valid_until: string
  discount_pct: number
  tax_rate: number
  total: number
  gross_margin_pct: number
  margin_status: MarginStatus
  lines_count: number
  has_pdf: boolean
  created_at: string
}

export interface Budget extends BudgetSummary {
  parent_budget_id: string | null
  work_order_id: string | null
  notes: string | null
  client_notes: string | null
  lines: BudgetLine[]
  totals: BudgetTotals
  versions: BudgetVersionInfo[]
  updated_at: string
}

export interface BudgetListResponse {
  items: BudgetSummary[]
  total: number
  skip: number
  limit: number
}

export interface WorkOrderPreview {
  budget_id: string
  budget_number: string
  customer_name: string
  tasks_to_create: Array<{
    name: string
    estimated_hours: number
    description: string
  }>
  materials_to_reserve: Array<{
    name: string
    quantity: number
    unit: string
    stock_available: number
    enough_stock: boolean
    inventory_item_id: string | null
  }>
  warnings: string[]
  total_estimated_cost: number
}

export interface BudgetFilters {
  q?: string
  customer_id?: string
  status?: BudgetStatus
  date_from?: string
  date_to?: string
  latest_only?: boolean
  skip?: number
  limit?: number
}

export interface BudgetLineCreatePayload {
  line_type: BudgetLineType
  description: string
  inventory_item_id?: string | null
  quantity: number
  unit?: string | null
  unit_price: number
  unit_cost?: number
  line_discount_pct?: number
  sort_order?: number
}

export interface BudgetLineUpdatePayload {
  description?: string
  quantity?: number
  unit?: string | null
  unit_price?: number
  unit_cost?: number
  line_discount_pct?: number
  sort_order?: number
}

export interface BudgetCreatePayload {
  customer_id?: string | null
  site_visit_id?: string | null
  issue_date?: string | null
  valid_until?: string | null
  tax_rate?: number | null
  discount_pct?: number
  notes?: string | null
  client_notes?: string | null
  lines?: BudgetLineCreatePayload[]
}

export interface BudgetFromVisitPayload {
  site_visit_id: string
  lines_override?: BudgetLineCreatePayload[] | null
  tax_rate?: number | null
  discount_pct?: number
  valid_until?: string | null
  notes?: string | null
  client_notes?: string | null
}

export interface BudgetUpdatePayload {
  issue_date?: string | null
  valid_until?: string | null
  tax_rate?: number | null
  discount_pct?: number | null
  notes?: string | null
  client_notes?: string | null
}
