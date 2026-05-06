"""Repository for Budget and BudgetLine models."""

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.budget import Budget, BudgetLine, BudgetSection
from app.repositories.base import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(Budget, session, tenant_id)

    async def get_next_budget_number(self) -> str:
        """
        Generates the next sequential number: PRES-YYYY-NNNN (per tenant).
        """
        year = datetime.now().year
        stmt = select(func.count(Budget.id)).where(
            Budget.budget_number.like(f"PRES-{year}-%")
        )
        if self.tenant_id is not None:
            stmt = stmt.where(Budget.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        return f"PRES-{year}-{(count + 1):04d}"

    async def search(
        self,
        query: str | None,
        customer_id: uuid.UUID | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        latest_only: bool,
        skip: int,
        limit: int,
    ) -> tuple[list[Budget], int]:
        """Search with filters. Eager-loads customer and lines."""
        from app.models.customer import Customer

        stmt = select(Budget).options(
            selectinload(Budget.customer),
            selectinload(Budget.lines),
            selectinload(Budget.sections),
        )
        count_stmt = select(func.count()).select_from(Budget)

        if self.tenant_id is not None:
            stmt = stmt.where(Budget.tenant_id == self.tenant_id)
            count_stmt = count_stmt.where(Budget.tenant_id == self.tenant_id)

        if latest_only:
            stmt = stmt.where(Budget.is_latest_version.is_(True))
            count_stmt = count_stmt.where(Budget.is_latest_version.is_(True))

        if customer_id is not None:
            stmt = stmt.where(Budget.customer_id == customer_id)
            count_stmt = count_stmt.where(Budget.customer_id == customer_id)

        if status is not None:
            stmt = stmt.where(Budget.status == status)
            count_stmt = count_stmt.where(Budget.status == status)

        if date_from is not None:
            stmt = stmt.where(Budget.issue_date >= date_from)
            count_stmt = count_stmt.where(Budget.issue_date >= date_from)

        if date_to is not None:
            stmt = stmt.where(Budget.issue_date <= date_to)
            count_stmt = count_stmt.where(Budget.issue_date <= date_to)

        if query:
            pattern = f"%{query}%"
            stmt = stmt.outerjoin(Customer, Budget.customer_id == Customer.id)
            count_stmt = count_stmt.outerjoin(Customer, Budget.customer_id == Customer.id)
            search_filter = or_(
                Budget.budget_number.ilike(pattern),
                Customer.name.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        stmt = stmt.order_by(Budget.created_at.desc()).offset(skip).limit(limit)

        rows = await self.session.execute(stmt)
        total_result = await self.session.execute(count_stmt)
        return list(rows.scalars().all()), total_result.scalar_one()

    async def get_with_full_detail(self, budget_id: uuid.UUID) -> Budget | None:
        """Eager-loads customer (with addresses), site_visit, sections, lines with inventory_item, and child_budgets."""
        from app.models.customer import Customer

        stmt = (
            select(Budget)
            .options(
                selectinload(Budget.customer).selectinload(Customer.addresses),
                selectinload(Budget.site_visit),
                selectinload(Budget.sections),
                selectinload(Budget.lines).selectinload(BudgetLine.inventory_item),
                selectinload(Budget.child_budgets),
                selectinload(Budget.parent_budget),
            )
            .where(Budget.id == budget_id)
        )
        stmt = self._tenant_filter(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_version_chain(self, budget_id: uuid.UUID) -> list[Budget]:
        """
        Returns all versions in the chain for this budget,
        ordered by version ASC.
        """
        # First, resolve the root of the chain (get_by_id already applies tenant filter)
        budget = await self.get_by_id(budget_id)
        if not budget:
            return []
        root_id = budget.parent_budget_id or budget.id

        # Get all budgets that share this root (either are the root or have it as parent)
        stmt = (
            select(Budget)
            .options(
                selectinload(Budget.lines),
                selectinload(Budget.sections),
            )
            .where(
                or_(
                    Budget.id == root_id,
                    Budget.parent_budget_id == root_id,
                )
            )
            .order_by(Budget.version.asc())
        )
        stmt = self._tenant_filter(stmt)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_customer(
        self, customer_id: uuid.UUID, latest_only: bool = True
    ) -> list[Budget]:
        """For customer timeline — eager-loads lines for total calculation."""
        stmt = (
            select(Budget)
            .options(
                selectinload(Budget.lines),
                selectinload(Budget.sections),
            )
            .where(Budget.customer_id == customer_id)
        )
        if latest_only:
            stmt = stmt.where(Budget.is_latest_version.is_(True))
        stmt = stmt.order_by(Budget.issue_date.desc())
        stmt = self._tenant_filter(stmt)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_previous_versions_outdated(self, budget_id: uuid.UUID) -> None:
        """Mark all previous versions in a chain as is_latest_version=False."""
        await self.session.execute(
            update(Budget)
            .where(Budget.id == budget_id)
            .values(is_latest_version=False)
        )

    async def count_by_visit(self, site_visit_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(Budget.id)).where(Budget.site_visit_id == site_visit_id)
        )
        return result.scalar() or 0


class BudgetLineRepository(BaseRepository[BudgetLine]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(BudgetLine, session, tenant_id)


class BudgetSectionRepository(BaseRepository[BudgetSection]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(BudgetSection, session, tenant_id)

    async def list_by_budget(self, budget_id: uuid.UUID) -> list[BudgetSection]:
        stmt = (
            select(BudgetSection)
            .where(BudgetSection.budget_id == budget_id)
            .order_by(BudgetSection.sort_order.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def next_sort_order(self, budget_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(BudgetSection.sort_order), -1)).where(
            BudgetSection.budget_id == budget_id
        )
        result = await self.session.execute(stmt)
        current_max = result.scalar() or -1
        return int(current_max) + 1
