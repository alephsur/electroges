export interface SupplierItem {
  id: string
  supplier_id: string
  supplier_name: string
  inventory_item_id: string
  supplier_ref: string | null
  unit_cost: number
  last_purchase_cost: number | null
  last_purchase_date: string | null
  lead_time_days: number | null
  is_preferred: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface StockMovement {
  id: string
  inventory_item_id: string
  inventory_item_name: string
  movement_type: 'entry' | 'exit'
  quantity: number
  unit_cost: number
  reference_type: 'purchase_order' | 'work_order' | 'manual_adjustment'
  reference_id: string | null
  notes: string | null
  created_at: string
}

export interface InventoryItem {
  id: string
  name: string
  description: string | null
  unit: string
  unit_cost: number
  unit_cost_avg: number
  unit_price: number
  stock_current: number
  stock_reserved: number
  stock_available: number
  stock_min: number
  low_stock_alert: boolean
  last_movement_at: string | null
  supplier_items: SupplierItem[]
  preferred_supplier: SupplierItem | null
  supplier_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface InventoryItemListResponse {
  items: InventoryItem[]
  total: number
  skip: number
  limit: number
}

export interface InventoryFilters {
  q?: string
  supplier_id?: string
  low_stock_only?: boolean
  skip?: number
  limit?: number
}

export interface InventoryItemCreatePayload {
  name: string
  description?: string | null
  unit?: string
  unit_price?: number
  stock_min?: number
  is_active?: boolean
  supplier_id?: string | null
  unit_cost?: number
  supplier_ref?: string | null
  is_preferred?: boolean
}

export interface InventoryItemUpdatePayload {
  name?: string
  description?: string | null
  unit?: string
  unit_cost?: number
  unit_price?: number
  stock_min?: number
  is_active?: boolean
}

export interface SupplierItemCreatePayload {
  supplier_id: string
  inventory_item_id: string
  unit_cost: number
  supplier_ref?: string | null
  lead_time_days?: number | null
  is_preferred?: boolean
}

export interface SupplierItemUpdatePayload {
  unit_cost?: number
  supplier_ref?: string | null
  lead_time_days?: number | null
  is_preferred?: boolean
  is_active?: boolean
}

export interface ManualAdjustmentPayload {
  quantity: number
  unit_cost: number
  notes: string
}
