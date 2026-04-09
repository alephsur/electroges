import axios, { type AxiosError } from "axios";
import { useAuthStore } from "@/features/auth/store/auth-store";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  // Required so the browser includes HttpOnly cookies in every cross-origin
  // request. With the Vite proxy (/api → backend) requests are same-origin in
  // development, but this flag is needed in production behind nginx as well.
  withCredentials: true,
});

// Handle 401: attempt a silent token refresh, logout on failure.
// No tokens are read from or written to localStorage — the browser manages
// the HttpOnly cookies transparently.
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as typeof error.config & { _retry?: boolean };

    // Avoid infinite loops if the refresh endpoint itself returns 401.
    const isRefreshCall = originalRequest.url?.includes("/auth/refresh");

    if (error.response?.status === 401 && !originalRequest._retry && !isRefreshCall) {
      originalRequest._retry = true;
      try {
        await useAuthStore.getState().refreshSession();
        return apiClient(originalRequest);
      } catch {
        await useAuthStore.getState().logout();
      }
    }
    return Promise.reject(error);
  }
);
