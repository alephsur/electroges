import { isAxiosError } from "axios";

export function getApiErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    return error.response?.data?.detail ?? "Ha ocurrido un error inesperado";
  }
  return "Ha ocurrido un error inesperado";
}
