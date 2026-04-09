import { create } from "zustand";
import { persist } from "zustand/middleware";
import { apiClient } from "@/lib/api-client";

export type UserRole = "superadmin" | "admin" | "user";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  tenant_id: string | null;
}

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;

  login: (email: string, password: string) => Promise<void>;
  refreshSession: () => Promise<void>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      login: async (email, password) => {
        // Backend sets HttpOnly cookies; the response body contains user info.
        const { data: user } = await apiClient.post("/api/v1/auth/token", { email, password });
        set({ user, isAuthenticated: true });
      },

      refreshSession: async () => {
        // Refresh cookie is sent automatically by the browser.
        // Backend rotates both cookies and returns updated user info.
        const { data: user } = await apiClient.post("/api/v1/auth/refresh");
        set({ user, isAuthenticated: true });
      },

      logout: async () => {
        // Ask the backend to clear the HttpOnly cookies.
        try {
          await apiClient.post("/api/v1/auth/logout");
        } finally {
          set({ user: null, isAuthenticated: false });
        }
      },

      changePassword: async (currentPassword, newPassword) => {
        await apiClient.post("/api/v1/auth/change-password", {
          current_password: currentPassword,
          new_password: newPassword,
        });
      },
    }),
    {
      name: "electroges-auth",
      // Only persist non-sensitive UI state. Tokens live exclusively in HttpOnly
      // cookies managed by the browser — never in localStorage.
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
