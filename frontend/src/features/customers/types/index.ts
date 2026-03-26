export type CustomerType = 'individual' | 'company' | 'community'
export type AddressType = 'fiscal' | 'service'
export type DocumentType = 'contract' | 'id_document' | 'authorization' | 'other'

export interface CustomerAddress {
  id: string
  customer_id: string
  address_type: AddressType
  label: string | null
  street: string
  city: string
  postal_code: string
  province: string | null
  is_default: boolean
  created_at: string
}

export interface CustomerDocument {
  id: string
  customer_id: string
  name: string
  file_path: string
  file_size_bytes: number | null
  document_type: DocumentType
  created_at: string
}

export interface CustomerSummary {
  id: string
  customer_type: CustomerType
  name: string
  tax_id: string | null
  email: string | null
  phone: string | null
  contact_person: string | null
  is_active: boolean
  active_work_orders: number
  total_billed: number
  pending_amount: number
  last_activity_at: string | null
  primary_address: CustomerAddress | null
  created_at: string
}

export interface Customer extends CustomerSummary {
  phone_secondary: string | null
  notes: string | null
  addresses: CustomerAddress[]
  documents: CustomerDocument[]
  updated_at: string
}

export interface CustomerListResponse {
  items: CustomerSummary[]
  total: number
  skip: number
  limit: number
}

export type TimelineEventType =
  | 'site_visit'
  | 'budget_created'
  | 'budget_sent'
  | 'budget_accepted'
  | 'budget_rejected'
  | 'work_order_created'
  | 'work_order_closed'
  | 'invoice_issued'
  | 'invoice_paid'

export interface TimelineEvent {
  event_type: TimelineEventType
  event_date: string
  title: string
  subtitle: string | null
  reference_id: string
  reference_type: string
  amount: number | null
  status: string | null
}

export interface CustomerTimeline {
  customer_id: string
  events: TimelineEvent[]
  total_site_visits: number
  total_budgets: number
  total_work_orders: number
  total_invoiced: number
  total_pending: number
}

export interface CustomerFilters {
  q?: string
  customer_type?: CustomerType
  is_active?: boolean
  skip?: number
  limit?: number
}

export interface CustomerAddressCreatePayload {
  address_type: AddressType
  label?: string | null
  street: string
  city: string
  postal_code: string
  province?: string | null
  is_default?: boolean
}

export interface CustomerAddressUpdatePayload {
  address_type?: AddressType
  label?: string | null
  street?: string
  city?: string
  postal_code?: string
  province?: string | null
  is_default?: boolean
}

export interface CustomerCreatePayload {
  customer_type: CustomerType
  name: string
  tax_id?: string | null
  email?: string | null
  phone?: string | null
  phone_secondary?: string | null
  contact_person?: string | null
  notes?: string | null
  initial_address?: CustomerAddressCreatePayload | null
}

export interface CustomerUpdatePayload {
  customer_type?: CustomerType
  name?: string
  tax_id?: string | null
  email?: string | null
  phone?: string | null
  phone_secondary?: string | null
  contact_person?: string | null
  notes?: string | null
  is_active?: boolean
}
