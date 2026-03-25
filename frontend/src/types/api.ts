// Generic API response types

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface ApiError {
  detail: string;
}

// Shared enums across modules
export type WorkOrderStatus = "draft" | "in_progress" | "pending_closure" | "closed";
export type TaskStatus = "pending" | "in_progress" | "completed";
export type BudgetStatus = "draft" | "sent" | "accepted" | "rejected" | "expired";
export type SiteVisitStatus = "scheduled" | "completed" | "cancelled";
export type InvoiceStatus = "draft" | "sent" | "paid" | "overdue";
export type BudgetLineType = "labor" | "material" | "other";
export type StockMovementType = "entry" | "exit";
