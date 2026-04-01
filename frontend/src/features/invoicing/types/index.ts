export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'cancelled'
export type InvoiceEffectiveStatus =
  | InvoiceStatus
  | 'overdue'
  | 'partially_paid'
export type InvoiceLineOrigin = 'certification' | 'task' | 'manual'
export type PaymentMethod = 'transfer' | 'cash' | 'card' | 'direct_debit'

export interface InvoiceLine {
  id: string
  invoice_id: string
  origin_type: InvoiceLineOrigin
  origin_id: string | null
  sort_order: number
  description: string
  quantity: number
  unit: string | null
  unit_price: number
  line_discount_pct: number
  subtotal: number
}

export interface Payment {
  id: string
  invoice_id: string
  amount: number
  payment_date: string
  method: PaymentMethod
  reference: string | null
  notes: string | null
  created_at: string
}

export interface InvoiceTotals {
  subtotal_before_discount: number
  discount_amount: number
  taxable_base: number
  tax_amount: number
  total: number
  total_paid: number
  pending_amount: number
  is_fully_paid: boolean
}

export interface InvoiceSummary {
  id: string
  invoice_number: string
  is_rectification: boolean
  rectifies_invoice_id: string | null
  customer_id: string
  customer_name: string
  work_order_id: string | null
  work_order_number: string | null
  status: InvoiceStatus
  effective_status: InvoiceEffectiveStatus
  issue_date: string
  due_date: string
  total: number
  total_paid: number
  pending_amount: number
  days_overdue: number
  has_pdf: boolean
  created_at: string
}

export interface Invoice extends InvoiceSummary {
  discount_pct: number
  tax_rate: number
  notes: string | null
  client_notes: string | null
  lines: InvoiceLine[]
  payments: Payment[]
  totals: InvoiceTotals
  updated_at: string
}

export interface InvoiceListResponse {
  items: InvoiceSummary[]
  total: number
}

export interface InvoiceFilters {
  q?: string
  customer_id?: string
  work_order_id?: string
  status?: string
  overdue_only?: boolean
  date_from?: string
  date_to?: string
  skip?: number
  limit?: number
}

export interface InvoiceLineCreatePayload {
  origin_type?: InvoiceLineOrigin
  origin_id?: string | null
  description: string
  quantity: number
  unit?: string | null
  unit_price: number
  line_discount_pct?: number
  sort_order?: number
}

export interface InvoiceCreatePayload {
  customer_id: string
  work_order_id?: string | null
  issue_date?: string | null
  due_date?: string | null
  tax_rate?: number | null
  discount_pct?: number
  notes?: string | null
  client_notes?: string | null
  lines?: InvoiceLineCreatePayload[]
}

export interface InvoiceFromWorkOrderPayload {
  work_order_id: string
  certification_ids?: string[]
  task_ids?: string[]
  extra_lines?: InvoiceLineCreatePayload[]
  issue_date?: string | null
  due_date?: string | null
  tax_rate?: number | null
  discount_pct?: number
  notes?: string | null
  client_notes?: string | null
}

export interface InvoiceUpdatePayload {
  issue_date?: string | null
  due_date?: string | null
  tax_rate?: number | null
  discount_pct?: number | null
  notes?: string | null
  client_notes?: string | null
}

export interface RectificationPayload {
  reason: string
  notes?: string | null
}

export interface PaymentCreatePayload {
  amount: number
  payment_date: string
  method: PaymentMethod
  reference?: string | null
  notes?: string | null
}

export interface PaymentReminderResponse {
  invoice_number: string
  customer_name: string
  pending_amount: number
  days_overdue: number
  reminder_text: string
}
