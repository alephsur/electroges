"""Repository for Budget and BudgetLine models."""

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.budget import Budget, BudgetLine
from app.repositories.base import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    def __init__(self, session: AsyncSession):
        super().__init__(Budget, session)

    async def get_next_budget_number(self) -> str:
        """
        Generates the next sequential number: PRES-YYYY-NNNN.
        Counts existing budgets for the current year (including versions).
        """
        year = datetime.now().year
        result = await self.session.execute(
            select(func.count(Budget.id)).where(
                Budget.budget_number.like(f"PRES-{year}-%")
            )
        )
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
        )
        count_stmt = select(func.count()).select_from(Budget)

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
        """Eager-loads customer (with addresses), site_visit, lines with inventory_item, and child_budgets."""
        from app.models.customer import Customer, CustomerAddress

        result = await self.session.execute(
            select(Budget)
            .options(
                selectinload(Budget.customer).selectinload(Customer.addresses),
                selectinload(Budget.site_visit),
                selectinload(Budget.lines).selectinload(BudgetLine.inventory_item),
                selectinload(Budget.child_budgets),
                selectinload(Budget.parent_budget),
            )
            .where(Budget.id == budget_id)
        )
        return result.scalar_one_or_none()

    async def get_version_chain(self, budget_id: uuid.UUID) -> list[Budget]:
        """
        Returns all versions in the chain for this budget,
        ordered by version ASC.
        """
        # First, resolve the root of the chain
        budget = await self.get_by_id(budget_id)
        if not budget:
            return []
        root_id = budget.parent_budget_id or budget.id

        # Get all budgets that share this root (either are the root or have it as parent)
        result = await self.session.execute(
            select(Budget)
            .options(selectinload(Budget.lines))
            .where(
                or_(
                    Budget.id == root_id,
                    Budget.parent_budget_id == root_id,
                )
            )
            .order_by(Budget.version.asc())
        )
        return list(result.scalars().all())

    async def get_by_customer(
        self, customer_id: uuid.UUID, latest_only: bool = True
    ) -> list[Budget]:
        """For customer timeline — eager-loads lines for total calculation."""
        stmt = (
            select(Budget)
            .options(selectinload(Budget.lines))
            .where(Budget.customer_id == customer_id)
        )
        if latest_only:
            stmt = stmt.where(Budget.is_latest_version.is_(True))
        stmt = stmt.order_by(Budget.issue_date.desc())
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
    def __init__(self, session: AsyncSession):
        super().__init__(BudgetLine, session)
