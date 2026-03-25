from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier import Supplier
from app.repositories.base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    def __init__(self, session: AsyncSession):
        super().__init__(Supplier, session)

    async def search(
        self,
        query: str | None = None,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Supplier], int]:
        stmt = select(Supplier)
        count_stmt = select(func.count()).select_from(Supplier)

        if is_active is not None:
            stmt = stmt.where(Supplier.is_active == is_active)
            count_stmt = count_stmt.where(Supplier.is_active == is_active)

        if query:
            pattern = f"%{query}%"
            search_filter = or_(
                Supplier.name.ilike(pattern),
                Supplier.tax_id.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        stmt = stmt.order_by(Supplier.name).offset(skip).limit(limit)

        rows = await self.session.execute(stmt)
        total = await self.session.execute(count_stmt)

        return list(rows.scalars().all()), total.scalar_one()

    async def get_by_tax_id(self, tax_id: str) -> Supplier | None:
        result = await self.session.execute(
            select(Supplier).where(Supplier.tax_id == tax_id)
        )
        return result.scalar_one_or_none()
