import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Mail,
  Phone,
  MapPin,
  User,
  CreditCard,
  FileText,
  Pencil,
  PowerOff,
  Package,
  ShoppingCart,
  LayoutDashboard,
  Plus,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";
import { useSupplier, useDeactivateSupplier } from "../hooks/use-suppliers";
import { useInventoryItems } from "@/features/inventory/hooks/use-inventory-items";
import {
  usePurchaseOrders,
  useReceivePurchaseOrder,
  useCancelPurchaseOrder,
} from "../hooks/use-purchase-orders";
import { SupplierForm } from "./SupplierForm";
import { InventoryItemForm } from "./InventoryItemForm";
import { PurchaseOrderForm } from "./PurchaseOrderForm";
import { PurchaseOrderDetailModal } from "./PurchaseOrderDetailModal";
import { getApiErrorMessage } from "@/shared/hooks/use-api-error";
import { cn } from "@/shared/utils/cn";
import type { PurchaseOrderSummary } from "../types";

type Tab = "ficha" | "materiales" | "pedidos" | "resumen";

// ------------------------------------------------------------------ component

interface SupplierDetailProps {
  supplierId: string;
}

export function SupplierDetail({ supplierId }: SupplierDetailProps) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("ficha");
  const [showEditForm, setShowEditForm] = useState(false);
  const [showItemForm, setShowItemForm] = useState(false);
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);

  const { data: supplier, isLoading, error } = useSupplier(supplierId);
  const { data: itemsData } = useInventoryItems({ supplier_id: supplierId, limit: 200 });
  const { data: ordersData } = usePurchaseOrders(supplierId);
  const deactivateMutation = useDeactivateSupplier();

  const handleDeactivate = async () => {
    await deactivateMutation.mutateAsync(supplierId, {
      onSuccess: () => navigate("/proveedores"),
    });
  };

  if (isLoading) {
    return (
      <PageShell>
        <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
          Cargando proveedor...
        </div>
      </PageShell>
    );
  }

  if (error || !supplier) {
    return (
      <PageShell>
        <p className="text-sm text-red-500 p-6">{getApiErrorMessage(error)}</p>
      </PageShell>
    );
  }

  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: "ficha", label: "Ficha", icon: User },
    { key: "materiales", label: "Materiales", icon: Package },
    { key: "pedidos", label: "Pedidos", icon: ShoppingCart },
    { key: "resumen", label: "Resumen", icon: LayoutDashboard },
  ];

  return (
    <PageShell>
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/proveedores")}
            className="text-gray-400 hover:text-gray-600 transition-colors lg:hidden"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{supplier.name}</h2>
            {supplier.tax_id && (
              <p className="text-xs text-gray-500">{supplier.tax_id}</p>
            )}
          </div>
          <span
            className={cn(
              "text-xs font-medium px-2 py-0.5 rounded-full",
              supplier.is_active
                ? "bg-green-100 text-green-700"
                : "bg-gray-100 text-gray-500"
            )}
          >
            {supplier.is_active ? "Activo" : "Inactivo"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowEditForm(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-brand-700 border border-brand-200 rounded-lg hover:bg-brand-50 transition-colors"
          >
            <Pencil size={14} />
            Editar
          </button>
          {supplier.is_active && !confirmDeactivate && (
            <button
              onClick={() => setConfirmDeactivate(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
            >
              <PowerOff size={14} />
              Desactivar
            </button>
          )}
          {supplier.is_active && confirmDeactivate && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-1.5">
              <span className="text-xs text-red-700">¿Confirmar desactivación?</span>
              <button
                onClick={() => setConfirmDeactivate(false)}
                className="text-xs text-gray-600 hover:text-gray-800"
              >
                No
              </button>
              <button
                onClick={handleDeactivate}
                disabled={deactivateMutation.isPending}
                className="text-xs font-medium text-red-700 hover:text-red-900 disabled:opacity-50"
              >
                {deactivateMutation.isPending ? "..." : "Sí, desactivar"}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-100 px-6">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={cn(
              "flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors",
              activeTab === key
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "ficha" && (
          <FichaTab supplier={supplier} />
        )}
        {activeTab === "materiales" && (
          <MaterialesTab
            supplierId={supplierId}
            onNew={() => setShowItemForm(true)}
          />
        )}
        {activeTab === "pedidos" && (
          <PedidosTab
            supplierId={supplierId}
            onNew={() => setShowOrderForm(true)}
          />
        )}
        {activeTab === "resumen" && (
          <ResumenTab
            itemsTotal={itemsData?.total ?? 0}
            ordersData={ordersData?.items ?? []}
          />
        )}
      </div>

      {/* Modals */}
      {showEditForm && (
        <SupplierForm supplier={supplier} onClose={() => setShowEditForm(false)} />
      )}
      {showItemForm && (
        <InventoryItemForm supplierId={supplierId} onClose={() => setShowItemForm(false)} />
      )}
      {showOrderForm && (
        <PurchaseOrderForm supplierId={supplierId} onClose={() => setShowOrderForm(false)} />
      )}
    </PageShell>
  );
}

// ------------------------------------------------------------------ tab: ficha

function FichaTab({ supplier }: { supplier: NonNullable<ReturnType<typeof useSupplier>["data"]> }) {
  return (
    <div className="max-w-lg space-y-4">
      <DetailRow icon={Mail} label="Email" value={supplier.email} />
      <DetailRow icon={Phone} label="Teléfono" value={supplier.phone} />
      <DetailRow icon={MapPin} label="Dirección" value={supplier.address} />
      <DetailRow icon={User} label="Persona de contacto" value={supplier.contact_person} />
      <DetailRow icon={CreditCard} label="Condiciones de pago" value={supplier.payment_terms} />
      {supplier.notes && (
        <div>
          <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-1">
            <FileText size={13} />
            <span>Notas</span>
          </div>
          <p className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 rounded-lg p-3">
            {supplier.notes}
          </p>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ tab: materiales

function MaterialesTab({
  supplierId,
  onNew,
}: {
  supplierId: string;
  onNew: () => void;
}) {
  const { data, isLoading } = useInventoryItems({ supplier_id: supplierId, limit: 200 });
  const items = data?.items ?? [];
  const navigate = useNavigate();

  const handleItemDetail = (itemId: string) => {
    navigate(`/inventario/${itemId}`);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">
          {data ? `${data.total} artículo${data.total !== 1 ? "s" : ""}` : "Cargando..."}
        </p>
        <button
          onClick={onNew}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
        >
          <Plus size={14} />
          Nuevo artículo
        </button>
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-sm text-gray-400">Cargando artículos...</div>
      ) : items.length === 0 ? (
        <div className="py-12 text-center text-sm text-gray-400">
          Este proveedor no tiene artículos de inventario
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Unidad</th>
                <th className="px-4 py-3 text-right">Coste proveedor</th>
                <th className="px-4 py-3 text-right">P. coste medio (PMP)</th>
                <th className="px-4 py-3 text-right">Precio venta</th>
                <th className="px-4 py-3 text-right">Stock</th>
                <th className="px-4 py-3 text-right">Stock mín.</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{item.name}</td>
                  <td className="px-4 py-3 text-gray-500">{item.unit}</td>
                  <td className="px-4 py-3 text-right text-gray-700">
                    {Number(item.unit_cost).toFixed(4)} €
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500 text-xs font-mono">
                    {Number((item as any).unit_cost_avg ?? 0).toFixed(4)} €
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700">
                    {Number(item.unit_price).toFixed(2)} €
                  </td>
                  <td
                    className={cn(
                      "px-4 py-3 text-right font-medium",
                      Number(item.stock_current) <= Number(item.stock_min)
                        ? "text-amber-600"
                        : "text-gray-700"
                    )}
                  >
                    {Number(item.stock_current).toFixed(3)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500">
                    {Number(item.stock_min).toFixed(3)}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleItemDetail(item.id)}
                      className="text-xs text-brand-600 hover:text-brand-800 hover:underline whitespace-nowrap"
                    >
                      Ver detalle →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ tab: pedidos

const STATUS_CONFIG: Record<
  string,
  { label: string; icon: React.ElementType; className: string }
> = {
  pending: { label: "Pendiente", icon: Clock, className: "text-amber-700 bg-amber-50" },
  received: { label: "Recibido", icon: CheckCircle, className: "text-green-700 bg-green-50" },
  cancelled: { label: "Cancelado", icon: XCircle, className: "text-gray-500 bg-gray-100" },
};

function PedidosTab({
  supplierId,
  onNew,
}: {
  supplierId: string;
  onNew: () => void;
}) {
  const { data, isLoading } = usePurchaseOrders(supplierId);
  const receiveMutation = useReceivePurchaseOrder(supplierId);
  const cancelMutation = useCancelPurchaseOrder(supplierId);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const orders = data?.items ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">
          {data ? `${data.total} pedido${data.total !== 1 ? "s" : ""}` : "Cargando..."}
        </p>
        <button
          onClick={onNew}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
        >
          <Plus size={14} />
          Nuevo pedido
        </button>
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-sm text-gray-400">Cargando pedidos...</div>
      ) : orders.length === 0 ? (
        <div className="py-12 text-center text-sm text-gray-400">
          Este proveedor no tiene pedidos
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden divide-y divide-gray-50">
          {orders.map((order) => {
            const cfg = STATUS_CONFIG[order.status] ?? STATUS_CONFIG.pending;
            const StatusIcon = cfg.icon;
            return (
              <div key={order.id} className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50">
                {/* Number + date */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={() => setSelectedOrderId(order.id)}
                      className="font-mono text-sm font-medium text-brand-700 hover:text-brand-900 hover:underline whitespace-nowrap"
                    >
                      {order.order_number}
                    </button>
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap",
                        cfg.className
                      )}
                    >
                      <StatusIcon size={10} />
                      {cfg.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-400 flex-wrap">
                    <span>Pedido: {formatDate(order.order_date)}</span>
                    {order.expected_date && (
                      <span>Entrega: {formatDate(order.expected_date)}</span>
                    )}
                  </div>
                </div>

                {/* Total */}
                <div className="shrink-0 text-sm font-semibold text-gray-800 whitespace-nowrap">
                  {Number(order.total).toLocaleString("es-ES", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}{" "}€
                </div>

                {/* Actions */}
                {order.status === "pending" && (
                  <div className="flex items-center gap-1.5 shrink-0">
                    <ActionButton
                      onClick={() => receiveMutation.mutate(order.id)}
                      disabled={receiveMutation.isPending}
                      variant="success"
                    >
                      Recibir
                    </ActionButton>
                    <ActionButton
                      onClick={() => cancelMutation.mutate(order.id)}
                      disabled={cancelMutation.isPending}
                      variant="danger"
                    >
                      Cancelar
                    </ActionButton>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {selectedOrderId && (
        <PurchaseOrderDetailModal
          supplierId={supplierId}
          orderId={selectedOrderId}
          onClose={() => setSelectedOrderId(null)}
        />
      )}
    </div>
  );
}

// ------------------------------------------------------------------ tab: resumen

function ResumenTab({
  itemsTotal,
  ordersData,
}: {
  itemsTotal: number;
  ordersData: PurchaseOrderSummary[];
}) {
  const pending = ordersData.filter((o) => o.status === "pending").length;
  const received = ordersData.filter((o) => o.status === "received").length;
  const cancelled = ordersData.filter((o) => o.status === "cancelled").length;

  const stats = [
    { label: "Artículos en inventario", value: itemsTotal, color: "text-brand-700" },
    { label: "Pedidos totales", value: ordersData.length, color: "text-gray-700" },
    { label: "Pedidos pendientes", value: pending, color: "text-amber-700" },
    { label: "Pedidos recibidos", value: received, color: "text-green-700" },
    { label: "Pedidos cancelados", value: cancelled, color: "text-gray-400" },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 max-w-lg">
      {stats.map(({ label, value, color }) => (
        <div key={label} className="bg-white border border-gray-200 rounded-xl p-4">
          <p className="text-xs text-gray-400 mb-1">{label}</p>
          <p className={cn("text-3xl font-bold", color)}>{value}</p>
        </div>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------ helpers

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col bg-white border border-gray-200 rounded-xl overflow-hidden h-full">
      {children}
    </div>
  );
}

function DetailRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string | null | undefined;
}) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-2">
      <Icon size={14} className="text-gray-400 mt-0.5 shrink-0" />
      <div>
        <p className="text-xs text-gray-400">{label}</p>
        <p className="text-sm text-gray-800">{value}</p>
      </div>
    </div>
  );
}

function ActionButton({
  onClick,
  disabled,
  variant,
  children,
}: {
  onClick: () => void;
  disabled: boolean;
  variant: "success" | "danger";
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "px-2 py-1 text-xs font-medium rounded-md transition-colors disabled:opacity-50",
        variant === "success"
          ? "text-green-700 bg-green-50 hover:bg-green-100"
          : "text-red-600 bg-red-50 hover:bg-red-100"
      )}
    >
      {children}
    </button>
  );
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}
