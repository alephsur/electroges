export interface BudgetStats {
  total: number
  draft: number
  sent: number
  accepted: number
  rejected: number
  expired: number
  total_amount: number
  accepted_amount: number
  conversion_rate: number
}

export interface WorkOrderStats {
  total: number
  draft: number
  active: number
  pending_closure: number
  closed: number
  cancelled: number
  active_count: number
}

export interface InvoiceStats {
  total: number
  draft: number
  sent: number
  paid: number
  cancelled: number
  overdue_count: number
  total_invoiced: number
  total_collected: number
  total_pending: number
  overdue_amount: number
  avg_collection_days: number | null
}

export interface PurchaseOrderStats {
  total: number
  pending: number
  received: number
  cancelled: number
}

export interface SiteVisitStats {
  total: number
  scheduled: number
  in_progress: number
  completed: number
  cancelled: number
  no_show: number
}

export interface MonthlyRevenue {
  month: string
  label: string
  invoiced: number
  collected: number
}

export interface TopCustomer {
  customer_id: string
  customer_name: string
  invoiced: number
  invoice_count: number
}

export interface OverdueInvoiceItem {
  id: string
  invoice_number: string
  customer_name: string
  total: number
  pending_amount: number
  days_overdue: number
}

export interface PendingBudgetItem {
  id: string
  budget_number: string
  customer_name: string
  total: number
  days_since_sent: number
}

export interface WorkOrderProfitabilityItem {
  work_order_id: string
  work_order_number: string
  customer_name: string
  budgeted_hours: number
  actual_hours: number
  budgeted_material_cost: number
  actual_material_cost: number
  budgeted_revenue: number
  total_certified: number
  revenue_base: number
  margin_pct: number | null
}

export interface CashFlowBucket {
  bucket: string
  label: string
  amount: number
  invoice_count: number
}

export interface TopDebtorCustomer {
  customer_id: string
  customer_name: string
  total_overdue: number
  invoice_count: number
  avg_days_overdue: number
}

export interface DashboardSummary {
  date_from: string
  date_to: string
  budgets: BudgetStats
  work_orders: WorkOrderStats
  invoices: InvoiceStats
  purchase_orders: PurchaseOrderStats
  site_visits: SiteVisitStats
  monthly_revenue: MonthlyRevenue[]
  top_customers: TopCustomer[]
  overdue_invoices: OverdueInvoiceItem[]
  pending_budgets: PendingBudgetItem[]
  low_stock_items_count: number
  recent_activity: RecentActivityItem[]
  work_order_profitability: WorkOrderProfitabilityItem[]
  cash_flow_buckets: CashFlowBucket[]
  top_debtors: TopDebtorCustomer[]
}

export interface RecentActivityItem {
  id: string
  entity_type: 'invoice' | 'work_order' | 'budget' | 'site_visit' | 'purchase_order'
  entity_number: string
  customer_name: string | null
  status: string
  date: string
}

export interface RecentActivityPage {
  items: RecentActivityItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DateRange {
  from: string
  to: string
}

export type DatePreset = 'this_month' | 'last_3_months' | 'this_year' | 'last_12_months' | 'custom'
