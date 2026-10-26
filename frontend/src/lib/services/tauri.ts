import { writable } from 'svelte/store';
import { writeText } from '@tauri-apps/plugin-clipboard-manager';

export const isTauri = writable(false);

export async function initializeTauri() {
  if (window.__TAURI__) {
    isTauri.set(true);
    const { appWindow } = await import('@tauri-apps/api/window');

    document.getElementById('minimize-btn')?.addEventListener('click', () => appWindow.minimize());
    document.getElementById('maximize-btn')?.addEventListener('click', () => appWindow.toggleMaximize());
    document.getElementById('close-btn')?.addEventListener('click', () => appWindow.close());
  }
}

export async function copyToClipboard(text: string) {
    if (window.__TAURI__) {
        await writeText(text);
    } else {
        await navigator.clipboard.writeText(text);
    }
}
