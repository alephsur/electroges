export type WorkOrderStatus =
  | 'draft'
  | 'active'
  | 'pending_closure'
  | 'closed'
  | 'cancelled'

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled'
export type CertificationStatus = 'draft' | 'issued' | 'invoiced'

export interface TaskMaterial {
  id: string
  task_id: string
  inventory_item_id: string
  inventory_item_name: string
  inventory_item_unit: string
  estimated_quantity: number
  consumed_quantity: number
  pending_quantity: number
  unit_cost: number
  estimated_cost: number
  actual_cost: number
}

export interface Task {
  id: string
  work_order_id: string
  origin_budget_line_id: string | null
  name: string
  description: string | null
  status: TaskStatus
  sort_order: number
  unit_price: number | null
  estimated_hours: number | null
  actual_hours: number | null
  materials: TaskMaterial[]
  estimated_cost: number
  actual_cost: number
  is_certified: boolean
  certification_id: string | null
  created_at: string
}

export interface LinkedPOLine {
  inventory_item_name: string | null
  description: string | null
  quantity: number
  unit_cost: number
  subtotal: number
}

export interface LinkedPurchaseOrder {
  id: string
  purchase_order_id: string
  supplier_id: string
  order_number: string
  supplier_name: string
  supplier_email: string | null
  supplier_phone: string | null
  status: string
  order_date: string
  expected_date: string | null
  total_amount: number
  notes: string | null
  lines: LinkedPOLine[]
}

export interface CertificationItem {
  id: string
  task_id: string
  task_name: string
  task_status: string
  amount: number
  notes: string | null
}

export interface Certification {
  id: string
  work_order_id: string
  certification_number: string
  status: CertificationStatus
  notes: string | null
  invoice_id: string | null
  items: CertificationItem[]
  total_amount: number
  created_at: string
  updated_at: string
}

export interface WorkOrderKPIs {
  total_tasks: number
  completed_tasks: number
  progress_pct: number
  estimated_hours: number
  actual_hours: number
  hours_deviation_pct: number
  budget_cost: number
  actual_cost: number
  cost_deviation_pct: number
  total_task_materials: number
  fully_consumed_materials: number
  pending_materials: number
  budget_total: number
  total_certified: number
  total_invoiced: number
  pending_to_certify: number
  margin_real_pct: number
  total_purchase_orders: number
  pending_purchase_orders: number
}

export interface WorkOrderSummary {
  id: string
  work_order_number: string
  customer_id: string
  customer_name: string
  customer_email: string | null
  customer_phone: string | null
  origin_budget_id: string | null
  budget_number: string | null
  status: WorkOrderStatus
  address: string | null
  total_tasks: number
  completed_tasks: number
  progress_pct: number
  budget_total: number
  total_certified: number
  actual_cost: number
  created_at: string
}

export interface WorkOrder extends WorkOrderSummary {
  other_lines_notes: string | null
  notes: string | null
  assigned_to: string | null
  tasks: Task[]
  certifications: Certification[]
  purchase_order_links: LinkedPurchaseOrder[]
  delivery_notes: DeliveryNote[]
  kpis: WorkOrderKPIs
  updated_at: string
}

export interface WorkOrderListResponse {
  items: WorkOrderSummary[]
  total: number
  skip: number
  limit: number
}

export interface WorkOrderFilters {
  q?: string
  customer_id?: string
  status?: WorkOrderStatus
  skip?: number
  limit?: number
}

export type DeliveryNoteStatus = 'draft' | 'issued'
export type DeliveryNoteLineType = 'material' | 'labor' | 'other'

export interface DeliveryNoteItem {
  id: string
  delivery_note_id: string
  line_type: DeliveryNoteLineType
  description: string
  inventory_item_id: string | null
  inventory_item_name: string | null
  quantity: number
  unit: string
  unit_price: number
  subtotal: number
  sort_order: number
}

export interface DeliveryNote {
  id: string
  work_order_id: string
  delivery_note_number: string
  status: DeliveryNoteStatus
  delivery_date: string
  requested_by: string | null
  notes: string | null
  items: DeliveryNoteItem[]
  total_amount: number
  created_at: string
  updated_at: string
}

export interface DeliveryNoteItemCreate {
  line_type: DeliveryNoteLineType
  description: string
  inventory_item_id?: string | null
  quantity: number
  unit: string
  unit_price: number
  sort_order?: number
}

export interface DeliveryNoteCreate {
  delivery_date: string
  requested_by?: string | null
  notes?: string | null
  items: DeliveryNoteItemCreate[]
}

export interface DeliveryNoteUpdate {
  delivery_date?: string
  requested_by?: string | null
  notes?: string | null
  items?: DeliveryNoteItemCreate[]
}
