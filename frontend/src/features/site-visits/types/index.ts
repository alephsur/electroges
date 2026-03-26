export type SiteVisitStatus =
  | 'scheduled'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'no_show'

export interface SiteVisitMaterial {
  id: string
  site_visit_id: string
  inventory_item_id: string | null
  inventory_item_name: string | null
  description: string | null
  estimated_qty: number
  unit: string | null
  unit_cost: number | null
  subtotal: number | null
  created_at: string
}

export interface SiteVisitPhoto {
  id: string
  site_visit_id: string
  file_path: string
  file_size_bytes: number | null
  caption: string | null
  sort_order: number
  created_at: string
}

export interface SiteVisitDocument {
  id: string
  site_visit_id: string
  name: string
  file_path: string
  file_size_bytes: number | null
  document_type: string
  created_at: string
}

export interface SiteVisitSummary {
  id: string
  customer_id: string | null
  customer_name: string | null
  customer_type: string | null
  address_display: string
  contact_name: string | null
  visit_date: string
  status: SiteVisitStatus
  description: string | null
  estimated_budget: number | null
  has_photos: boolean
  has_documents: boolean
  materials_count: number
  budgets_count: number
  created_at: string
}

export interface SiteVisit extends SiteVisitSummary {
  customer_address_id: string | null
  address_text: string | null
  contact_phone: string | null
  estimated_duration_hours: number | null
  work_scope: string | null
  technical_notes: string | null
  estimated_hours: number | null
  materials: SiteVisitMaterial[]
  photos: SiteVisitPhoto[]
  documents: SiteVisitDocument[]
  updated_at: string
}

export interface SiteVisitListResponse {
  items: SiteVisitSummary[]
  total: number
  skip: number
  limit: number
}

export interface SiteVisitFilters {
  q?: string
  customer_id?: string
  status?: SiteVisitStatus
  date_from?: string
  date_to?: string
  skip?: number
  limit?: number
}

export interface SiteVisitCreatePayload {
  customer_id?: string | null
  customer_address_id?: string | null
  address_text?: string | null
  contact_name?: string | null
  contact_phone?: string | null
  visit_date: string
  estimated_duration_hours?: number | null
  description?: string | null
  work_scope?: string | null
  technical_notes?: string | null
  estimated_hours?: number | null
  estimated_budget?: number | null
}

export type SiteVisitUpdatePayload = Partial<SiteVisitCreatePayload>

export interface SiteVisitMaterialCreatePayload {
  inventory_item_id?: string | null
  description?: string | null
  estimated_qty: number
  unit?: string | null
  unit_cost?: number | null
}

export interface SiteVisitMaterialUpdatePayload {
  description?: string | null
  estimated_qty?: number
  unit?: string | null
  unit_cost?: number | null
}
