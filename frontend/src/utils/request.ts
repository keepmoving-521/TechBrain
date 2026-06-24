import axios, { type AxiosRequestConfig } from "axios";
import { ElMessage } from "element-plus";

import { getErrorMessage } from "@/utils/errors";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

function createRequestId(): string {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID().replace(/-/g, "");
  }

  return `${Date.now()}${Math.random().toString(16).slice(2)}`;
}

const http = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    Accept: "application/json",
  },
});

http.interceptors.request.use((config) => {
  config.headers.set("X-Request-ID", createRequestId());
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    ElMessage.error(getErrorMessage(error));
    return Promise.reject(error);
  },
);

export const request = {
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await http.get<T>(url, config);
    return response.data;
  },
  async post<T, D = unknown>(url: string, data?: D, config?: AxiosRequestConfig): Promise<T> {
    const response = await http.post<T>(url, data, config);
    return response.data;
  },
};
