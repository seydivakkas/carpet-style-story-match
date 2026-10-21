import { API_BASE_URL } from "../constants";
import { ApiErrorDetail } from "../types/api";

export class ApiClientError extends Error {
  code: string;
  status: number;
  rawDetail: unknown;

  constructor(status: number, code: string, message: string, rawDetail?: unknown) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.rawDetail = rawDetail;
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = endpoint.startsWith("http")
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  const headers = new Headers(options?.headers);
  if (options?.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
      cache: "no-store",
    });

    if (!res.ok) {
      let errorCode = `HTTP_${res.status}`;
      let errorMessage = `API error (${res.status})`;
      let rawDetail: unknown = null;

      try {
        const errorJson = await res.json();
        rawDetail = errorJson.detail;

        if (typeof errorJson.detail === "object" && errorJson.detail !== null) {
          const detailObj = errorJson.detail as ApiErrorDetail;
          if (detailObj.code) errorCode = detailObj.code;
          if (detailObj.message) errorMessage = detailObj.message;
        } else if (typeof errorJson.detail === "string") {
          errorMessage = errorJson.detail;
        }
      } catch {
        // JSON parse fallback
      }

      throw new ApiClientError(res.status, errorCode, errorMessage, rawDetail);
    }

    if (res.status === 204) {
      return {} as T;
    }

    return res.json();
  } catch (err) {
    if (err instanceof ApiClientError) {
      throw err;
    }
    const isNetworkError =
      err instanceof TypeError &&
      (err.message.includes("fetch") || err.message.includes("NetworkError") || err.message.includes("Failed"));
    const code = isNetworkError ? "API_UNREACHABLE" : "UNKNOWN_ERROR";
    const message = isNetworkError
      ? `Backend API servisine (${API_BASE_URL}) ulaşılamıyor. Lütfen API sunucusunun çalıştığından ve ağ erişiminden emin olun.`
      : err instanceof Error
      ? err.message
      : "Bilinmeyen bir ağ hatası oluştu.";

    throw new ApiClientError(0, code, message, err);
  }
}
