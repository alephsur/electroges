"""Repository for the Dashboard module — aggregates metrics across all entities."""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.budget import Budget, BudgetLineType, BudgetStatus
from app.models.inventory_item import InventoryItem
from app.models.invoice import Invoice, InvoiceStatus
from app.models.purchase_order import PurchaseOrder
from app.models.site_visit import SiteVisit
from app.models.work_order import Task, WorkOrder, WorkOrderStatus
from app.schemas.dashboard import (
    BudgetStats,
    CashFlowBucket,
    DashboardSummary,
    InvoiceStats,
    MonthlyRevenue,
    OverdueInvoiceItem,
    PendingBudgetItem,
    PurchaseOrderStats,
    RecentActivityItem,
    RecentActivityPage,
    SiteVisitStats,
    TopCustomer,
    TopDebtorCustomer,
    WorkOrderProfitabilityItem,
    WorkOrderStats,
)

_MONTH_LABELS_ES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}


def _budget_total(budget: Budget) -> Decimal:
    subtotal = sum(
        line.quantity * line.unit_price * (1 - line.line_discount_pct / 100)
        for line in budget.lines
    )
    taxable = subtotal * (1 - budget.discount_pct / 100)
    return taxable * (1 + budget.tax_rate / 100)


def _invoice_total(invoice: Invoice) -> Decimal:
    subtotal = sum(
        line.quantity * line.unit_price * (1 - line.line_discount_pct / 100)
        for line in invoice.lines
    )
    taxable = subtotal * (1 - invoice.discount_pct / 100)
    return taxable * (1 + invoice.tax_rate / 100)


def _invoice_collected(invoice: Invoice) -> Decimal:
    return sum(p.amount for p in invoice.payments)


class DashboardRepository:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        self.session = session
        self.tenant_id = tenant_id

    async def get_summary(self, date_from: date, date_to: date) -> DashboardSummary:
        today = date.today()

        budgets = await self._load_budgets(date_from, date_to)
        work_orders = await self._load_work_orders(date_from, date_to)
        invoices = await self._load_invoices(date_from, date_to)
        purchase_orders = await self._load_purchase_orders(date_from, date_to)
        site_visits = await self._load_site_visits(date_from, date_to)
        all_overdue_invoices = await self._load_all_overdue_invoices(today)
        all_pending_budgets = await self._load_all_pending_budgets(today)
        low_stock_count = await self._count_low_stock_items()
        recent_activity = await self._load_recent_activity()
        closed_work_orders = await self._load_closed_work_orders_for_profitability()
        pending_invoices = await self._load_pending_invoices_for_cashflow(today)

        return DashboardSummary(
            date_from=date_from,
            date_to=date_to,
            budgets=self._compute_budget_stats(budgets, today),
            work_orders=self._compute_work_order_stats(work_orders),
            invoices=self._compute_invoice_stats(invoices, today),
            purchase_orders=self._compute_purchase_order_stats(purchase_orders),
            site_visits=self._compute_site_visit_stats(site_visits),
            monthly_revenue=self._compute_monthly_revenue(invoices, date_from, date_to),
            top_customers=self._compute_top_customers(invoices),
            overdue_invoices=self._build_overdue_items(all_overdue_invoices, today),
            pending_budgets=self._build_pending_items(all_pending_budgets, today),
            low_stock_items_count=low_stock_count,
            recent_activity=recent_activity,
            work_order_profitability=self._compute_work_order_profitability(closed_work_orders),
            cash_flow_buckets=self._compute_cash_flow_buckets(pending_invoices, today),
            top_debtors=self._compute_top_debtors(all_overdue_invoices, today),
        )

    # ── Data loaders ──────────────────────────────────────────────────────────

    def _tf(self, model, stmt):
        """Apply tenant filter if tenant_id is set."""
        if self.tenant_id is not None and hasattr(model, "tenant_id"):
            stmt = stmt.where(model.tenant_id == self.tenant_id)
        return stmt

    async def _load_budgets(self, date_from: date, date_to: date) -> list[Budget]:
        stmt = (
            select(Budget)
            .options(selectinload(Budget.lines), selectinload(Budget.customer))
            .where(
                Budget.issue_date >= date_from,
                Budget.issue_date <= date_to,
                Budget.is_latest_version.is_(True),
            )
        )
        result = await self.session.execute(self._tf(Budget, stmt))
        return list(result.scalars().all())

    async def _load_work_orders(self, date_from: date, date_to: date) -> list[WorkOrder]:
        from_dt = datetime.combine(date_from, datetime.min.time())
        to_dt = datetime.combine(date_to, datetime.max.time())
        stmt = select(WorkOrder).where(
            WorkOrder.created_at >= from_dt,
            WorkOrder.created_at <= to_dt,
        )
        result = await self.session.execute(self._tf(WorkOrder, stmt))
        return list(result.scalars().all())

    async def _load_invoices(self, date_from: date, date_to: date) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
                selectinload(Invoice.customer),
            )
            .where(
                Invoice.issue_date >= date_from,
                Invoice.issue_date <= date_to,
                Invoice.is_rectification.is_(False),
            )
        )
        result = await self.session.execute(self._tf(Invoice, stmt))
        return list(result.scalars().all())

    async def _load_purchase_orders(self, date_from: date, date_to: date) -> list[PurchaseOrder]:
        stmt = select(PurchaseOrder).where(
            PurchaseOrder.order_date >= date_from,
            PurchaseOrder.order_date <= date_to,
        )
        result = await self.session.execute(self._tf(PurchaseOrder, stmt))
        return list(result.scalars().all())

    async def _load_site_visits(self, date_from: date, date_to: date) -> list[SiteVisit]:
        stmt = select(SiteVisit).where(
            func.date(SiteVisit.visit_date) >= date_from,
            func.date(SiteVisit.visit_date) <= date_to,
        )
        result = await self.session.execute(self._tf(SiteVisit, stmt))
        return list(result.scalars().all())

    async def _load_all_overdue_invoices(self, today: date) -> list[Invoice]:
        """Load ALL overdue invoices regardless of date filter (actionable alerts)."""
        stmt = (
            select(Invoice)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
                selectinload(Invoice.customer),
            )
            .where(
                Invoice.status == InvoiceStatus.SENT,
                Invoice.due_date < today,
                Invoice.is_rectification.is_(False),
            )
            .order_by(Invoice.due_date.asc())
            .limit(20)
        )
        result = await self.session.execute(self._tf(Invoice, stmt))
        return list(result.scalars().all())

    async def _load_all_pending_budgets(self, today: date) -> list[Budget]:
        """Load ALL sent budgets awaiting response (actionable alerts)."""
        stmt = (
            select(Budget)
            .options(selectinload(Budget.lines), selectinload(Budget.customer))
            .where(
                Budget.status == literal(BudgetStatus.SENT.value, String()),
                Budget.valid_until >= today,
                Budget.is_latest_version.is_(True),
            )
            .order_by(Budget.issue_date.asc())
            .limit(20)
        )
        result = await self.session.execute(self._tf(Budget, stmt))
        return list(result.scalars().all())

    async def _load_recent_activity(self, limit: int = 20) -> list[RecentActivityItem]:
        """Merge the most recent records from all main entities, sorted by date desc."""
        n = limit // 5 + 4  # fetch a bit more from each to guarantee top N after merge

        inv_stmt = self._tf(Invoice, select(Invoice).options(selectinload(Invoice.customer)).where(Invoice.is_rectification.is_(False)).order_by(Invoice.created_at.desc()).limit(n))
        wo_stmt = self._tf(WorkOrder, select(WorkOrder).options(selectinload(WorkOrder.customer)).order_by(WorkOrder.created_at.desc()).limit(n))
        b_stmt = self._tf(Budget, select(Budget).options(selectinload(Budget.customer)).where(Budget.is_latest_version.is_(True)).order_by(Budget.created_at.desc()).limit(n))
        sv_stmt = self._tf(SiteVisit, select(SiteVisit).options(selectinload(SiteVisit.customer)).order_by(SiteVisit.created_at.desc()).limit(n))
        po_stmt = self._tf(PurchaseOrder, select(PurchaseOrder).options(selectinload(PurchaseOrder.supplier)).order_by(PurchaseOrder.created_at.desc()).limit(n))

        invoices_res = await self.session.execute(inv_stmt)
        work_orders_res = await self.session.execute(wo_stmt)
        budgets_res = await self.session.execute(b_stmt)
        site_visits_res = await self.session.execute(sv_stmt)
        po_res = await self.session.execute(po_stmt)

        items: list[RecentActivityItem] = []

        for inv in invoices_res.scalars().all():
            items.append(RecentActivityItem(
                id=str(inv.id),
                entity_type="invoice",
                entity_number=inv.invoice_number,
                customer_name=inv.customer.name if inv.customer else None,
                status=inv.status.value if hasattr(inv.status, "value") else str(inv.status),
                date=inv.created_at,
            ))

        for wo in work_orders_res.scalars().all():
            items.append(RecentActivityItem(
                id=str(wo.id),
                entity_type="work_order",
                entity_number=wo.work_order_number,
                customer_name=wo.customer.name if wo.customer else None,
                status=wo.status.value if hasattr(wo.status, "value") else str(wo.status),
                date=wo.created_at,
            ))

        for b in budgets_res.scalars().all():
            items.append(RecentActivityItem(
                id=str(b.id),
                entity_type="budget",
                entity_number=b.budget_number,
                customer_name=b.customer.name if b.customer else None,
                status=b.status.value if hasattr(b.status, "value") else str(b.status),
                date=b.created_at,
            ))

        for sv in site_visits_res.scalars().all():
            items.append(RecentActivityItem(
                id=str(sv.id),
                entity_type="site_visit",
                entity_number=f"Visita {sv.created_at.strftime('%d/%m/%Y')}",
                customer_name=sv.customer.name if sv.customer else None,
                status=sv.status.value if hasattr(sv.status, "value") else str(sv.status),
                date=sv.created_at,
            ))

        for po in po_res.scalars().all():
            items.append(RecentActivityItem(
                id=str(po.id),
                entity_type="purchase_order",
                entity_number=po.order_number,
                customer_name=po.supplier.name if po.supplier else None,
                status=po.status,
                date=po.created_at,
            ))

        items.sort(key=lambda x: x.date, reverse=True)
        return items[:limit]

    async def get_recent_activity_page(
        self, page: int, page_size: int
    ) -> RecentActivityPage:
        """Return a paginated slice of the global recent activity feed."""
        offset = (page - 1) * page_size
        # Load enough items from each source to guarantee we can cover offset + page_size
        per_source = offset + page_size

        inv_stmt = self._tf(
            Invoice,
            select(Invoice)
            .options(selectinload(Invoice.customer))
            .where(Invoice.is_rectification.is_(False))
            .order_by(Invoice.created_at.desc())
            .limit(per_source),
        )
        wo_stmt = self._tf(
            WorkOrder,
            select(WorkOrder)
            .options(selectinload(WorkOrder.customer))
            .order_by(WorkOrder.created_at.desc())
            .limit(per_source),
        )
        b_stmt = self._tf(
            Budget,
            select(Budget)
            .options(selectinload(Budget.customer))
            .where(Budget.is_latest_version.is_(True))
            .order_by(Budget.created_at.desc())
            .limit(per_source),
        )
        sv_stmt = self._tf(
            SiteVisit,
            select(SiteVisit)
            .options(selectinload(SiteVisit.customer))
            .order_by(SiteVisit.created_at.desc())
            .limit(per_source),
        )
        po_stmt = self._tf(
            PurchaseOrder,
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.supplier))
            .order_by(PurchaseOrder.created_at.desc())
            .limit(per_source),
        )

        invoices_res, wo_res, budgets_res, sv_res, po_res = await asyncio.gather(
            self.session.execute(inv_stmt),
            self.session.execute(wo_stmt),
            self.session.execute(b_stmt),
            self.session.execute(sv_stmt),
            self.session.execute(po_stmt),
        )
        total = await self._count_recent_activity_total()

        items: list[RecentActivityItem] = []

        for inv in invoices_res.scalars().all():
            items.append(RecentActivityItem(
                id=str(inv.id),
                entity_type="invoice",
                entity_number=inv.invoice_number,
                customer_name=inv.customer.name if inv.customer else None,
                status=inv.status.value if hasattr(inv.status, "value") else str(inv.status),
                date=inv.created_at,
            ))

        for wo in wo_res.scalars().all():
            items.append(RecentActivityItem(
                id=str(wo.id),
                entity_type="work_order",
                entity_number=wo.work_order_number,
                customer_name=wo.customer.name if wo.customer else None,
                status=wo.status.value if hasattr(wo.status, "value") else str(wo.status),
                date=wo.created_at,
            ))

        for b in budgets_res.scalars().all():
            items.append(RecentActivityItem(
                id=str(b.id),
                entity_type="budget",
                entity_number=b.budget_number,
                customer_name=b.customer.name if b.customer else None,
                status=b.status.value if hasattr(b.status, "value") else str(b.status),
                date=b.created_at,
            ))

        for sv in sv_res.scalars().all():
            items.append(RecentActivityItem(
                id=str(sv.id),
                entity_type="site_visit",
                entity_number=f"Visita {sv.created_at.strftime('%d/%m/%Y')}",
                customer_name=sv.customer.name if sv.customer else None,
                status=sv.status.value if hasattr(sv.status, "value") else str(sv.status),
                date=sv.created_at,
            ))

        for po in po_res.scalars().all():
            items.append(RecentActivityItem(
                id=str(po.id),
                entity_type="purchase_order",
                entity_number=po.order_number,
                customer_name=po.supplier.name if po.supplier else None,
                status=po.status,
                date=po.created_at,
            ))

        items.sort(key=lambda x: x.date, reverse=True)
        page_items = items[offset : offset + page_size]
        total_pages = max(1, (total + page_size - 1) // page_size)

        return RecentActivityPage(
            items=page_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def _count_recent_activity_total(self) -> int:
        """Count total items across all entity sources for the activity feed."""
        inv_count_stmt = self._tf(
            Invoice,
            select(func.count()).select_from(Invoice).where(Invoice.is_rectification.is_(False)),
        )
        wo_count_stmt = self._tf(WorkOrder, select(func.count()).select_from(WorkOrder))
        b_count_stmt = self._tf(
            Budget,
            select(func.count()).select_from(Budget).where(Budget.is_latest_version.is_(True)),
        )
        sv_count_stmt = self._tf(SiteVisit, select(func.count()).select_from(SiteVisit))
        po_count_stmt = self._tf(PurchaseOrder, select(func.count()).select_from(PurchaseOrder))

        results = await asyncio.gather(
            self.session.execute(inv_count_stmt),
            self.session.execute(wo_count_stmt),
            self.session.execute(b_count_stmt),
            self.session.execute(sv_count_stmt),
            self.session.execute(po_count_stmt),
        )
        return sum(r.scalar() or 0 for r in results)

    async def _count_low_stock_items(self) -> int:
        """Count inventory items where stock_current <= stock_min."""
        stmt = select(func.count()).select_from(InventoryItem).where(
            InventoryItem.stock_current <= InventoryItem.stock_min,
            InventoryItem.stock_min > 0,
        )
        stmt = self._tf(InventoryItem, stmt)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _load_closed_work_orders_for_profitability(self, limit: int = 15) -> list[WorkOrder]:
        """Load recently closed work orders with tasks, materials, certifications and budget."""
        from sqlalchemy.orm import selectinload as sl
        from app.models.work_order import Certification, CertificationItem

        stmt = (
            select(WorkOrder)
            .options(
                sl(WorkOrder.customer),
                sl(WorkOrder.origin_budget).selectinload(Budget.lines),
                sl(WorkOrder.tasks).selectinload(Task.materials),
                sl(WorkOrder.certifications).selectinload(Certification.items),
            )
            .where(WorkOrder.status == WorkOrderStatus.CLOSED)
            .order_by(WorkOrder.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(self._tf(WorkOrder, stmt))
        return list(result.scalars().all())

    async def _load_pending_invoices_for_cashflow(self, today: date) -> list[Invoice]:
        """Load all SENT non-overdue invoices for cash-flow projection."""
        stmt = (
            select(Invoice)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
            )
            .where(
                Invoice.status == InvoiceStatus.SENT,
                Invoice.due_date >= today,
                Invoice.is_rectification.is_(False),
            )
        )
        result = await self.session.execute(self._tf(Invoice, stmt))
        return list(result.scalars().all())

    # ── Stats builders ────────────────────────────────────────────────────────

    def _compute_budget_stats(self, budgets: list[Budget], today: date) -> BudgetStats:
        counts: dict[str, int] = defaultdict(int)
        total_amount = Decimal("0")
        accepted_amount = Decimal("0")

        for b in budgets:
            # status may be a BudgetStatus enum or a plain str depending on DB column type
            status = b.status.value if isinstance(b.status, BudgetStatus) else str(b.status)
            if status == BudgetStatus.SENT.value and b.valid_until < today:
                status = "expired"
            counts[status] += 1
            amount = _budget_total(b)
            total_amount += amount
            if status == BudgetStatus.ACCEPTED.value:
                accepted_amount += amount

        decided = counts["accepted"] + counts["rejected"]
        conversion_rate = (counts["accepted"] / decided * 100) if decided > 0 else 0.0

        return BudgetStats(
            total=len(budgets),
            draft=counts["draft"],
            sent=counts["sent"],
            accepted=counts["accepted"],
            rejected=counts["rejected"],
            expired=counts["expired"],
            total_amount=total_amount.quantize(Decimal("0.01")),
            accepted_amount=accepted_amount.quantize(Decimal("0.01")),
            conversion_rate=round(conversion_rate, 1),
        )

    def _compute_work_order_stats(self, work_orders: list[WorkOrder]) -> WorkOrderStats:
        counts: dict[str, int] = defaultdict(int)
        for wo in work_orders:
            counts[wo.status.value] += 1

        return WorkOrderStats(
            total=len(work_orders),
            draft=counts["draft"],
            active=counts["active"],
            pending_closure=counts["pending_closure"],
            closed=counts["closed"],
            cancelled=counts["cancelled"],
            active_count=counts["draft"] + counts["active"] + counts["pending_closure"],
        )

    def _compute_invoice_stats(self, invoices: list[Invoice], today: date) -> InvoiceStats:
        counts: dict[str, int] = defaultdict(int)
        total_invoiced = Decimal("0")
        total_collected = Decimal("0")
        overdue_amount = Decimal("0")
        collection_days: list[float] = []

        for inv in invoices:
            total = _invoice_total(inv)
            collected = _invoice_collected(inv)
            total_invoiced += total
            total_collected += collected

            if inv.status == InvoiceStatus.PAID:
                counts["paid"] += 1
                if inv.payments:
                    last_pay = max(p.payment_date for p in inv.payments)
                    collection_days.append((last_pay - inv.issue_date).days)
            elif inv.status == InvoiceStatus.SENT and inv.due_date < today:
                counts["overdue"] += 1
                pending = total - collected
                overdue_amount += pending
            elif inv.status == InvoiceStatus.SENT:
                counts["sent"] += 1
            elif inv.status == InvoiceStatus.DRAFT:
                counts["draft"] += 1
            elif inv.status == InvoiceStatus.CANCELLED:
                counts["cancelled"] += 1

        avg_days = (
            round(sum(collection_days) / len(collection_days), 1)
            if collection_days
            else None
        )

        return InvoiceStats(
            total=len(invoices),
            draft=counts["draft"],
            sent=counts["sent"],
            paid=counts["paid"],
            cancelled=counts["cancelled"],
            overdue_count=counts["overdue"],
            total_invoiced=total_invoiced.quantize(Decimal("0.01")),
            total_collected=total_collected.quantize(Decimal("0.01")),
            total_pending=(total_invoiced - total_collected).quantize(Decimal("0.01")),
            overdue_amount=overdue_amount.quantize(Decimal("0.01")),
            avg_collection_days=avg_days,
        )

    def _compute_purchase_order_stats(self, pos: list[PurchaseOrder]) -> PurchaseOrderStats:
        counts: dict[str, int] = defaultdict(int)
        for po in pos:
            counts[po.status] += 1
        return PurchaseOrderStats(
            total=len(pos),
            pending=counts["pending"],
            received=counts["received"],
            cancelled=counts["cancelled"],
        )

    def _compute_site_visit_stats(self, site_visits: list[SiteVisit]) -> SiteVisitStats:
        counts: dict[str, int] = defaultdict(int)
        for sv in site_visits:
            counts[sv.status.value] += 1
        return SiteVisitStats(
            total=len(site_visits),
            scheduled=counts["scheduled"],
            in_progress=counts["in_progress"],
            completed=counts["completed"],
            cancelled=counts["cancelled"],
            no_show=counts["no_show"],
        )

    def _compute_monthly_revenue(
        self, invoices: list[Invoice], date_from: date, date_to: date
    ) -> list[MonthlyRevenue]:
        monthly: dict[tuple[int, int], dict] = {}

        current = date(date_from.year, date_from.month, 1)
        end = date(date_to.year, date_to.month, 1)
        while current <= end:
            key = (current.year, current.month)
            monthly[key] = {"invoiced": Decimal("0"), "collected": Decimal("0")}
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

        for inv in invoices:
            if inv.status == InvoiceStatus.CANCELLED:
                continue
            key = (inv.issue_date.year, inv.issue_date.month)
            if key in monthly:
                monthly[key]["invoiced"] += _invoice_total(inv)
                monthly[key]["collected"] += _invoice_collected(inv)

        return [
            MonthlyRevenue(
                month=f"{year}-{month:02d}",
                label=f"{_MONTH_LABELS_ES[month]} {str(year)[2:]}",
                invoiced=data["invoiced"].quantize(Decimal("0.01")),
                collected=data["collected"].quantize(Decimal("0.01")),
            )
            for (year, month), data in sorted(monthly.items())
        ]

    def _compute_top_customers(self, invoices: list[Invoice]) -> list[TopCustomer]:
        by_customer: dict[str, dict] = {}
        for inv in invoices:
            if inv.status == InvoiceStatus.CANCELLED:
                continue
            cid = str(inv.customer_id)
            if cid not in by_customer:
                by_customer[cid] = {
                    "name": inv.customer.name,
                    "invoiced": Decimal("0"),
                    "count": 0,
                }
            by_customer[cid]["invoiced"] += _invoice_total(inv)
            by_customer[cid]["count"] += 1

        top = sorted(by_customer.items(), key=lambda x: x[1]["invoiced"], reverse=True)[:5]
        return [
            TopCustomer(
                customer_id=cid,
                customer_name=data["name"],
                invoiced=data["invoiced"].quantize(Decimal("0.01")),
                invoice_count=data["count"],
            )
            for cid, data in top
        ]

    def _build_overdue_items(
        self, invoices: list[Invoice], today: date
    ) -> list[OverdueInvoiceItem]:
        items = []
        for inv in invoices:
            total = _invoice_total(inv)
            collected = _invoice_collected(inv)
            pending = total - collected
            items.append(
                OverdueInvoiceItem(
                    id=str(inv.id),
                    invoice_number=inv.invoice_number,
                    customer_name=inv.customer.name,
                    total=total.quantize(Decimal("0.01")),
                    pending_amount=pending.quantize(Decimal("0.01")),
                    days_overdue=(today - inv.due_date).days,
                )
            )
        return sorted(items, key=lambda x: x.days_overdue, reverse=True)

    def _build_pending_items(
        self, budgets: list[Budget], today: date
    ) -> list[PendingBudgetItem]:
        items = []
        for b in budgets:
            total = _budget_total(b)
            items.append(
                PendingBudgetItem(
                    id=str(b.id),
                    budget_number=b.budget_number,
                    customer_name=b.customer.name,
                    total=total.quantize(Decimal("0.01")),
                    days_since_sent=(today - b.issue_date).days,
                )
            )
        return sorted(items, key=lambda x: x.days_since_sent, reverse=True)

    def _compute_work_order_profitability(
        self, work_orders: list[WorkOrder]
    ) -> list[WorkOrderProfitabilityItem]:
        items = []
        for wo in work_orders:
            budget = wo.origin_budget
            budgeted_hours = Decimal("0")
            budgeted_material_cost = Decimal("0")
            budgeted_revenue = Decimal("0")

            if budget and budget.lines:
                budgeted_revenue = _budget_total(budget)
                for line in budget.lines:
                    effective_qty = line.quantity * (1 - line.line_discount_pct / 100)
                    if line.line_type == BudgetLineType.LABOR:
                        budgeted_hours += line.quantity
                    elif line.line_type == BudgetLineType.MATERIAL:
                        budgeted_material_cost += effective_qty * line.unit_cost

            actual_hours: Decimal = sum(
                ((t.actual_hours or Decimal("0")) for t in wo.tasks),
                Decimal("0"),
            )
            actual_material_cost: Decimal = sum(
                (tm.consumed_quantity * tm.unit_cost
                 for t in wo.tasks
                 for tm in t.materials),
                Decimal("0"),
            )

            total_certified: Decimal = sum(
                (
                    ci.amount
                    for c in wo.certifications
                    if c.status.value in ("issued", "invoiced")
                    for ci in c.items
                ),
                Decimal("0"),
            )

            revenue_base = total_certified if total_certified > 0 else budgeted_revenue
            margin_pct: float | None = None
            if revenue_base > 0:
                margin_pct = round(
                    float((revenue_base - actual_material_cost) / revenue_base * 100), 1
                )

            items.append(
                WorkOrderProfitabilityItem(
                    work_order_id=str(wo.id),
                    work_order_number=wo.work_order_number,
                    customer_name=wo.customer.name if wo.customer else "—",
                    budgeted_hours=float(budgeted_hours.quantize(Decimal("0.01"))),
                    actual_hours=float(Decimal(str(actual_hours)).quantize(Decimal("0.01"))),
                    budgeted_material_cost=float(budgeted_material_cost.quantize(Decimal("0.01"))),
                    actual_material_cost=float(actual_material_cost.quantize(Decimal("0.01"))),
                    budgeted_revenue=float(budgeted_revenue.quantize(Decimal("0.01"))),
                    total_certified=float(total_certified.quantize(Decimal("0.01"))),
                    revenue_base=float(revenue_base.quantize(Decimal("0.01"))),
                    margin_pct=margin_pct,
                )
            )
        return items

    def _compute_cash_flow_buckets(
        self, invoices: list[Invoice], today: date
    ) -> list[CashFlowBucket]:
        buckets: dict[str, dict] = {
            "0_30":    {"label": "0–30 días",  "amount": Decimal("0"), "count": 0},
            "31_60":   {"label": "31–60 días", "amount": Decimal("0"), "count": 0},
            "61_90":   {"label": "61–90 días", "amount": Decimal("0"), "count": 0},
            "91_plus": {"label": "+90 días",   "amount": Decimal("0"), "count": 0},
        }
        for inv in invoices:
            total = _invoice_total(inv)
            collected = _invoice_collected(inv)
            pending = total - collected
            if pending <= 0:
                continue
            days = (inv.due_date - today).days
            if days <= 30:
                key = "0_30"
            elif days <= 60:
                key = "31_60"
            elif days <= 90:
                key = "61_90"
            else:
                key = "91_plus"
            buckets[key]["amount"] += pending
            buckets[key]["count"] += 1

        return [
            CashFlowBucket(
                bucket=key,
                label=data["label"],
                amount=float(data["amount"].quantize(Decimal("0.01"))),
                invoice_count=data["count"],
            )
            for key, data in buckets.items()
        ]

    def _compute_top_debtors(
        self, overdue_invoices: list[Invoice], today: date
    ) -> list[TopDebtorCustomer]:
        by_customer: dict[str, dict] = {}
        for inv in overdue_invoices:
            total = _invoice_total(inv)
            collected = _invoice_collected(inv)
            pending = total - collected
            if pending <= 0:
                continue
            cid = str(inv.customer_id)
            days_overdue = (today - inv.due_date).days
            if cid not in by_customer:
                by_customer[cid] = {
                    "name": inv.customer.name if inv.customer else "—",
                    "total_overdue": Decimal("0"),
                    "count": 0,
                    "days_list": [],
                }
            by_customer[cid]["total_overdue"] += pending
            by_customer[cid]["count"] += 1
            by_customer[cid]["days_list"].append(days_overdue)

        result = []
        for cid, data in by_customer.items():
            avg_days = sum(data["days_list"]) / len(data["days_list"])
            result.append(
                TopDebtorCustomer(
                    customer_id=cid,
                    customer_name=data["name"],
                    total_overdue=float(data["total_overdue"].quantize(Decimal("0.01"))),
                    invoice_count=data["count"],
                    avg_days_overdue=round(avg_days, 1),
                )
            )
        return sorted(result, key=lambda x: x.total_overdue, reverse=True)[:10]
