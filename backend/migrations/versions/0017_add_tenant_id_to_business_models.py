"""Add tenant_id to all business models and convert company_settings to per-tenant.

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-07 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Create a default tenant for existing data (if any)
    # -------------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO tenants (id, name, is_active, created_at, updated_at)
        VALUES (
            '00000000-0000-0000-0000-000000000001'::uuid,
            'Default Tenant',
            true,
            now(),
            now()
        )
        ON CONFLICT DO NOTHING
        """
    )

    # -------------------------------------------------------------------------
    # 2. customers
    # -------------------------------------------------------------------------
    op.add_column("customers", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE customers SET tenant_id = '00000000-0000-0000-0000-000000000001'::uuid")
    op.alter_column("customers", "tenant_id", nullable=False)
    op.create_foreign_key("fk_customers_tenant_id", "customers", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_customers_tenant_id", "customers", ["tenant_id"])
    # Drop global unique on tax_id, replace with composite per-tenant unique
    op.drop_index("customers_tax_id_key", table_name="customers", if_exists=True)
    op.execute("ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_tax_id_key")
    op.create_unique_constraint("uq_customers_tenant_tax_id", "customers", ["tenant_id", "tax_id"])

    # -------------------------------------------------------------------------
    # 3. suppliers
    # -------------------------------------------------------------------------
    op.add_column("suppliers", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE suppliers SET tenant_id = '00000000-0000-0000-0000-000000000001'::uuid")
    op.alter_column("suppliers", "tenant_id", nullable=False)
    op.create_foreign_key("fk_suppliers_tenant_id", "suppliers", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_suppliers_tenant_id", "suppliers", ["tenant_id"])
    op.execute("ALTER TABLE suppliers DROP CONSTRAINT IF EXISTS suppliers_tax_id_key")
    op.create_unique_constraint("uq_suppliers_tenant_tax_id", "suppliers", ["tenant_id", "tax_id"])

    # -------------------------------------------------------------------------
    # 4. inventory_items
    # -------------------------------------------------------------------------
    op.add_column("inventory_items", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE inventory_items SET tenant_id = '00000000-0000-0000-0000-000000000001'::uuid")
    op.alter_column("inventory_items", "tenant_id", nullable=False)
    op.create_foreign_key("fk_inventory_items_tenant_id", "inventory_items", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_inventory_items_tenant_id", "inventory_items", ["tenant_id"])

    # -------------------------------------------------------------------------
    # 5. stock_movements
    # -------------------------------------------------------------------------
    op.add_column("stock_movements", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE stock_movements SET tenant_id = '00000000-0000-0000-0000-000000000001'::uuid")
    op.alter_column("stock_movements", "tenant_id", nullable=False)
    op.create_foreign_key("fk_stock_movements_tenant_id", "stock_movements", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_stock_movements_tenant_id", "stock_movements", ["tenant_id"])

    # -------------------------------------------------------------------------
    # 6. site_visits
    # -------------------------------------------------------------------------
    op.add_column("site_visits", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE site_visits SET tenant_id = '00000000-0000-0000-0000-000000000001'::uuid")
    op.alter_column("site_visits", "tenant_id", nullable=False)
    op.create_foreign_key("fk_site_visits_tenant_id", "site_visits", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_site_visits_tenant_id", "site_visits", ["tenant_id"])

    # -------------------------------------------------------------------------
    # 7. budgets
    # -------------------------------------------------------------------------
    op.add_column("budgets", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE budgets SET tenant_id = '00000000-0000-0000-0000-000000000001'::uuid")
    op.alter_column("budgets", "tenant_id", nullable=False)
    op.create_foreign_key("fk_budgets_tenant_id", "budgets", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_budgets_tenant_id", "budgets", ["tenant_id"])
    # Replace global unique on budget_number with per-tenant unique
    op.execute("ALTER TABLE budgets DROP CONSTRAINT IF EXISTS budgets_budget_number_key")
    op.create_unique_constraint("uq_budgets_tenant_number", "budgets", ["tenant_id", "budget_number"])

    # -------------------------------------------------------------------------
    # 8. work_orders
    # -------------------------------------------------------------------------
    op.add_column("work_orders", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE work_orders SET tenant_id = '00000000-0000-0000-0000-000000000001'::uuid")
    op.alter_column("work_orders", "tenant_id", nullable=False)
    op.create_foreign_key("fk_work_orders_tenant_id", "work_orders", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_work_orders_tenant_id", "work_orders", ["tenant_id"])
    op.execute("ALTER TABLE work_orders DROP CONSTRAINT IF EXISTS work_orders_work_order_number_key")
    op.create_unique_constraint("uq_work_orders_tenant_number", "work_orders", ["tenant_id", "work_order_number"])

    # -------------------------------------------------------------------------
    # 9. invoices
    # -------------------------------------------------------------------------
    op.add_column("invoices", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE invoices SET tenant_id = '00000000-0000-0000-0000-000000000001'::uuid")
    op.alter_column("invoices", "tenant_id", nullable=False)
    op.create_foreign_key("fk_invoices_tenant_id", "invoices", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
    op.execute("ALTER TABLE invoices DROP CONSTRAINT IF EXISTS invoices_invoice_number_key")
    op.create_unique_constraint("uq_invoices_tenant_number", "invoices", ["tenant_id", "invoice_number"])

    # -------------------------------------------------------------------------
    # 10. purchase_orders
    # -------------------------------------------------------------------------
    op.add_column("purchase_orders", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE purchase_orders SET tenant_id = '00000000-0000-0000-0000-000000000001'::uuid")
    op.alter_column("purchase_orders", "tenant_id", nullable=False)
    op.create_foreign_key("fk_purchase_orders_tenant_id", "purchase_orders", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_purchase_orders_tenant_id", "purchase_orders", ["tenant_id"])
    op.execute("ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS purchase_orders_order_number_key")
    op.create_unique_constraint("uq_purchase_orders_tenant_number", "purchase_orders", ["tenant_id", "order_number"])

    # -------------------------------------------------------------------------
    # 11. company_settings — convert singleton to per-tenant UUID model
    # -------------------------------------------------------------------------
    # Drop old integer-PK table and recreate with UUID PK + tenant_id
    op.execute("DROP TABLE IF EXISTS company_settings")
    op.create_table(
        "company_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("tax_id", sa.String(20), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(10), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("bank_account", sa.String(50), nullable=True),
        sa.Column("logo_path", sa.String(500), nullable=True),
        sa.Column("general_conditions", sa.Text, nullable=True),
        sa.Column("default_tax_rate", sa.Numeric(5, 2), nullable=False, server_default="21.00"),
        sa.Column("default_validity_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("default_payment_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", name="uq_company_settings_tenant_id"),
    )
    op.create_index("ix_company_settings_tenant_id", "company_settings", ["tenant_id"])

    # Create default company_settings for default tenant
    op.execute(
        """
        INSERT INTO company_settings (id, tenant_id, company_name, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            '00000000-0000-0000-0000-000000000001'::uuid,
            'Default Tenant',
            now(),
            now()
        )
        """
    )


def downgrade() -> None:
    # company_settings
    op.drop_table("company_settings")
    op.create_table(
        "company_settings",
        sa.Column("id", sa.Integer, primary_key=True, server_default="1"),
        sa.Column("company_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("tax_id", sa.String(20), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(10), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("bank_account", sa.String(50), nullable=True),
        sa.Column("logo_path", sa.String(500), nullable=True),
        sa.Column("general_conditions", sa.Text, nullable=True),
        sa.Column("default_tax_rate", sa.Numeric(5, 2), nullable=False, server_default="21.00"),
        sa.Column("default_validity_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("default_payment_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    for table, col, constraint in [
        ("purchase_orders", "tenant_id", "uq_purchase_orders_tenant_number"),
        ("invoices", "tenant_id", "uq_invoices_tenant_number"),
        ("work_orders", "tenant_id", "uq_work_orders_tenant_number"),
        ("budgets", "tenant_id", "uq_budgets_tenant_number"),
        ("site_visits", "tenant_id", None),
        ("stock_movements", "tenant_id", None),
        ("inventory_items", "tenant_id", None),
        ("suppliers", "tenant_id", "uq_suppliers_tenant_tax_id"),
        ("customers", "tenant_id", "uq_customers_tenant_tax_id"),
    ]:
        if constraint:
            op.drop_constraint(constraint, table, type_="unique")
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, col)

    op.execute("ALTER TABLE customers ADD CONSTRAINT customers_tax_id_key UNIQUE (tax_id)")
    op.execute("ALTER TABLE suppliers ADD CONSTRAINT suppliers_tax_id_key UNIQUE (tax_id)")
    op.execute("ALTER TABLE budgets ADD CONSTRAINT budgets_budget_number_key UNIQUE (budget_number)")
    op.execute("ALTER TABLE work_orders ADD CONSTRAINT work_orders_work_order_number_key UNIQUE (work_order_number)")
    op.execute("ALTER TABLE invoices ADD CONSTRAINT invoices_invoice_number_key UNIQUE (invoice_number)")
    op.execute("ALTER TABLE purchase_orders ADD CONSTRAINT purchase_orders_order_number_key UNIQUE (order_number)")
