/**
 * Single source of truth for the FastAPI backend base URL.
 * Resolves Tauri dynamic port when running in the desktop shell.
 */

import { isTauriRuntime } from "./tauri";

let cachedBaseUrl: string | null = null;
let resolvePromise: Promise<string> | null = null;

const DEFAULT_URL = "http://127.0.0.1:8000";

function envDefault(): string {
  return (
    (import.meta.env.VITE_HTTP_BACKEND_ENDPOINT as string | undefined) ||
    (import.meta.env.VITE_API_URL as string | undefined) ||
    DEFAULT_URL
  );
}

export async function resolveBackendBaseUrl(force = false): Promise<string> {
  if (cachedBaseUrl && !force) return cachedBaseUrl;
  if (resolvePromise && !force) return resolvePromise;

  resolvePromise = (async () => {
    // Prefer Tauri-discovered sidecar port
    if (isTauriRuntime()) {
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        const port = await invoke<number>("get_backend_port");
        if (port && Number(port) > 0) {
          cachedBaseUrl = `http://127.0.0.1:${port}`;
          return cachedBaseUrl;
        }
      } catch (err) {
        console.warn("[backendUrl] Tauri port discovery failed:", err);
      }
    }

    cachedBaseUrl = envDefault();
    return cachedBaseUrl;
  })();

  try {
    return await resolvePromise;
  } finally {
    resolvePromise = null;
  }
}

export function getCachedBackendBaseUrl(): string {
  return cachedBaseUrl || envDefault();
}

export function setBackendBaseUrl(url: string): void {
  cachedBaseUrl = url.replace(/\/$/, "");
}

export async function backendFetch(
  path: string,
  init?: RequestInit
): Promise<Response> {
  const base = await resolveBackendBaseUrl();
  const url = path.startsWith("http")
    ? path
    : `${base}${path.startsWith("/") ? path : `/${path}`}`;
  return fetch(url, init);
}
