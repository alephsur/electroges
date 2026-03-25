// ------------------------------------------------------------------ supplier

export interface Supplier {
  id: string;
  name: string;
  tax_id: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  contact_person: string | null;
  payment_terms: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SupplierListResponse {
  items: Supplier[];
  total: number;
  skip: number;
  limit: number;
}

export interface SupplierCreatePayload {
  name: string;
  tax_id?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  contact_person?: string | null;
  payment_terms?: string | null;
  notes?: string | null;
}

export type SupplierUpdatePayload = Partial<SupplierCreatePayload>;

// ------------------------------------------------------------------ inventory item

export interface InventoryItem {
  id: string;
  name: string;
  description: string | null;
  unit: string;
  unit_cost: string;
  unit_price: string;
  stock_current: string;
  stock_min: string;
  supplier_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryItemListResponse {
  items: InventoryItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface InventoryItemCreatePayload {
  name: string;
  description?: string | null;
  unit?: string;
  unit_cost?: string | number;
  unit_price?: string | number;
  stock_current?: string | number;
  stock_min?: string | number;
}

// ------------------------------------------------------------------ purchase order

export type PurchaseOrderStatus = "pending" | "received" | "cancelled";

export interface PurchaseOrderLine {
  id: string;
  purchase_order_id: string;
  inventory_item_id: string | null;
  description: string | null;
  quantity: string;
  unit_cost: string;
  subtotal: string;
  inventory_item: InventoryItem | null;
  created_at: string;
  updated_at: string;
}

export interface PurchaseOrderSummary {
  id: string;
  supplier_id: string;
  order_number: string;
  status: PurchaseOrderStatus;
  order_date: string;
  expected_date: string | null;
  received_date: string | null;
  total: string;
  created_at: string;
  updated_at: string;
}

export interface PurchaseOrder extends PurchaseOrderSummary {
  notes: string | null;
  lines: PurchaseOrderLine[];
  total: string;
}

export interface PurchaseOrderListResponse {
  items: PurchaseOrderSummary[];
  total: number;
  skip: number;
  limit: number;
}

export interface PurchaseOrderLineCreatePayload {
  inventory_item_id?: string | null;
  description?: string | null;
  quantity: string | number;
  unit_cost: string | number;
}

export interface PurchaseOrderCreatePayload {
  supplier_id: string;
  order_date: string;
  expected_date?: string | null;
  notes?: string | null;
  lines: PurchaseOrderLineCreatePayload[];
}

export interface PurchaseOrderUpdatePayload {
  expected_date?: string | null;
  notes?: string | null;
}
