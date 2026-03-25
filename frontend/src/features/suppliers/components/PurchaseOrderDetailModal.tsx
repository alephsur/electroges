import { X, CheckCircle, XCircle, Clock } from "lucide-react";
import { usePurchaseOrder } from "../hooks/use-purchase-orders";
import { getApiErrorMessage } from "@/shared/hooks/use-api-error";
import { cn } from "@/shared/utils/cn";

// ------------------------------------------------------------------ status config

const STATUS_CONFIG: Record<string, { label: string; icon: React.ElementType; className: string }> =
  {
    pending: { label: "Pendiente", icon: Clock, className: "text-amber-700 bg-amber-50" },
    received: { label: "Recibido", icon: CheckCircle, className: "text-green-700 bg-green-50" },
    cancelled: { label: "Cancelado", icon: XCircle, className: "text-gray-500 bg-gray-100" },
  };

// ------------------------------------------------------------------ component

interface PurchaseOrderDetailModalProps {
  supplierId: string;
  orderId: string;
  onClose: () => void;
}

export function PurchaseOrderDetailModal({
  supplierId,
  orderId,
  onClose,
}: PurchaseOrderDetailModalProps) {
  const { data: order, isLoading, error } = usePurchaseOrder(supplierId, orderId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900">
              {order ? order.order_number : "Detalle del pedido"}
            </h2>
            {order && <StatusBadge status={order.status} />}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {isLoading && (
            <div className="py-12 text-center text-sm text-gray-400">Cargando pedido...</div>
          )}

          {(error || (!isLoading && !order)) && (
            <p className="text-sm text-red-500">{getApiErrorMessage(error)}</p>
          )}

          {order && (
            <div className="space-y-5">
              {/* Dates */}
              <div className="grid grid-cols-3 gap-4">
                <InfoField label="Fecha del pedido" value={formatDate(order.order_date)} />
                <InfoField
                  label="Entrega prevista"
                  value={order.expected_date ? formatDate(order.expected_date) : "—"}
                />
                <InfoField
                  label="Fecha de recepción"
                  value={order.received_date ? formatDate(order.received_date) : "—"}
                />
              </div>

              {/* Notes */}
              {order.notes && (
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">
                    Notas
                  </p>
                  <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap">
                    {order.notes}
                  </p>
                </div>
              )}

              {/* Lines */}
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
                  Líneas del pedido
                </p>
                <div className="border border-gray-200 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-100 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">
                        <th className="px-4 py-2.5">Artículo / Descripción</th>
                        <th className="px-4 py-2.5 text-right">Cantidad</th>
                        <th className="px-4 py-2.5 text-right">Coste unit.</th>
                        <th className="px-4 py-2.5 text-right">Subtotal</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {order.lines.map((line) => (
                        <tr key={line.id}>
                          <td className="px-4 py-3 text-gray-800">
                            {line.inventory_item?.name ?? line.description ?? "—"}
                            {line.inventory_item && line.description && (
                              <span className="ml-1 text-xs text-gray-400">
                                ({line.description})
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-600">
                            {Number(line.quantity).toLocaleString("es-ES", {
                              minimumFractionDigits: 0,
                              maximumFractionDigits: 3,
                            })}
                            {line.inventory_item && (
                              <span className="ml-1 text-xs text-gray-400">
                                {line.inventory_item.unit}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-600">
                            {Number(line.unit_cost).toLocaleString("es-ES", {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 4,
                            })}{" "}
                            €
                          </td>
                          <td className="px-4 py-3 text-right font-medium text-gray-800">
                            {Number(line.subtotal).toLocaleString("es-ES", {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })}{" "}
                            €
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    {/* Total row */}
                    <tfoot>
                      <tr className="border-t border-gray-200 bg-gray-50">
                        <td
                          colSpan={3}
                          className="px-4 py-3 text-right text-sm font-semibold text-gray-700"
                        >
                          Total
                        </td>
                        <td className="px-4 py-3 text-right text-base font-bold text-gray-900">
                          {Number(order.total).toLocaleString("es-ES", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}{" "}
                          €
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end px-6 py-4 border-t border-gray-100">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ helpers

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  const Icon = cfg.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
        cfg.className
      )}
    >
      <Icon size={11} />
      {cfg.label}
    </span>
  );
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className="text-sm font-medium text-gray-800">{value}</p>
    </div>
  );
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}
