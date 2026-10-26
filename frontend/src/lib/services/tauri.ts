import { writable } from 'svelte/store';
import { writeText } from '@tauri-apps/plugin-clipboard-manager';

export const isTauri = writable(false);

/**
 * Tauri v2 runtime detection.
 *
 * Tauri v2 injects `window.__TAURI_INTERNALS__` always, but `window.__TAURI__`
 * only when `app.withGlobalTauri` is enabled (it is NOT in this project) —
 * so legacy `__TAURI__` checks silently evaluate false in the packaged app
 * and break dynamic PA_PORT discovery, store access, and event listeners.
 */
export function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && !!(window as any).__TAURI_INTERNALS__;
}

export async function initializeTauri() {
  if (isTauriRuntime()) {
    isTauri.set(true);
    const { appWindow } = await import('@tauri-apps/api/window');

    document.getElementById('minimize-btn')?.addEventListener('click', () => appWindow.minimize());
    document.getElementById('maximize-btn')?.addEventListener('click', () => appWindow.toggleMaximize());
    document.getElementById('close-btn')?.addEventListener('click', () => appWindow.close());
  }
}

export async function copyToClipboard(text: string) {
    if (isTauriRuntime()) {
        await writeText(text);
    } else {
        await navigator.clipboard.writeText(text);
    }
}
