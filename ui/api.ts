import axios from "axios";

const TOKEN_KEY = "stabx.access_token";
const REFRESH_KEY = "stabx.refresh_token";

export function getAccessToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export const http = axios.create();

http.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes("/api/auth/login")) {
      clearTokens();
      if (location.pathname !== "/login") {
        location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export async function login(username: string, password: string) {
  const { data } = await http.post("/api/auth/login", { username, password });
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function fetchMe() {
  const { data } = await http.get("/api/auth/me");
  return data;
}
