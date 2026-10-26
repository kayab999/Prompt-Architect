import { writable } from 'svelte/store';

export const themes = ['dark', 'light', 'system', 'high-contrast'];
export const currentTheme = writable('dark');

export function applyTheme(theme: string) {
    document.body.classList.remove('light-theme', 'high-contrast-theme');
    if (theme === 'light') {
        document.body.classList.add('light-theme');
    } else if (theme === 'high-contrast') {
        document.body.classList.add('high-contrast-theme');
    } else if (theme === 'system') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (!prefersDark) {
            document.body.classList.add('light-theme');
        }
    }
}
