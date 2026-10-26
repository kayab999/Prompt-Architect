import { writable, get } from 'svelte/store';
import type { HistoryItem } from '$lib/types';
import { originalPrompt, refinedPrompt, model, selectedProfileKey } from './prompt';

const MAX_HISTORY_ITEMS = 10;

export const history = writable<HistoryItem[]>([]);
export const showHistory = writable(false);

export function loadHistory() {
  try {
    const saved = localStorage.getItem('promptArchitectHistory');
    if (saved) {
      history.set(JSON.parse(saved));
    }
  } catch (err) {
    console.warn('Failed to load history:', err);
    history.set([]);
  }
}

export function addToHistory(original: string, refined: string, model: string, profileKey: string) {
  const newEntry: HistoryItem = {
    id: Date.now(),
    timestamp: new Date().toLocaleString(),
    original,
    refined,
    model,
    profileKey,
    characters: refined.length
  };

  history.update(items => {
    const updated = [newEntry, ...items].slice(0, MAX_HISTORY_ITEMS);
    try {
      localStorage.setItem('promptArchitectHistory', JSON.stringify(updated));
    } catch (err) {
      console.warn('Failed to save history:', err);
    }
    return updated;
  });
}

export function loadFromHistory(entry: HistoryItem) {
  originalPrompt.set(entry.original);
  refinedPrompt.set(entry.refined);
  model.set(entry.model);
  selectedProfileKey.set(entry.profileKey);
  showHistory.set(false);
}

export function clearHistory() {
  history.set([]);
  try {
    localStorage.removeItem('promptArchitectHistory');
  } catch (err) {
    console.warn('Failed to clear history:', err);
  }
}
