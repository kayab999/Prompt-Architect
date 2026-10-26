import { writable, get, derived } from 'svelte/store';
import { app } from './app';
import { addToHistory } from './history';

// Hierarchical model selection stores
export const provider = writable('');
export const family = writable('');
export const model = writable('');

// Prompt and persona stores
export const originalPrompt = writable('');
export const refinedPrompt = writable('');
export const selectedProfileKey = writable<string>('');

// --- Dynamic Template Engine ---
export interface PromptTemplate {
  category: string;
  template: string;
  variables: string[];
  guidelines: string;
  prompt: string;
  version?: number;
  timestamp?: string;
}

export const activeTemplate = writable<PromptTemplate | null>(null);
export const templateVariables = writable<Record<string, string>>({});

export const interpolatedPrompt = derived(
  [activeTemplate, templateVariables],
  ([$template, $vars]) => {
    if (!$template) return '';

    let finalText = $template.template;

    $template.variables.forEach(variable => {
      const value = $vars[variable] || `{${variable}}`;
      const regex = new RegExp(`{${variable}}`, 'g');
      finalText = finalText.replace(regex, value);
    });

    return finalText;
  }
);

// Sincronizar el editor con la interpolación reactiva
interpolatedPrompt.subscribe(value => {
  if (value) originalPrompt.set(value);
});

// Stores for dynamic model data
interface ModelData {
  providers: string[];
  families: { [provider: string]: string[] };
  models: { [family: string]: string[] };
}
export const allModelData = writable<ModelData>({ providers: [], families: {}, models: {} });

// Derived stores for dropdown options
export const availableFamilies = derived([provider, allModelData], ([$provider, $allModelData]) => {
  return $provider ? $allModelData.families[$provider] || [] : [];
});

export const availableModels = derived([family, allModelData], ([$family, $allModelData]) => {
  return $family ? $allModelData.models[$family] || [] : [];
});

// Function to load models from API
export async function loadModels() {
  try {
    const { backendFetch } = await import("$lib/services/backendUrl");
    const res = await backendFetch("/models");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const all_models_raw: {
      id: string;
      provider: string;
      requires_api_key: boolean;
    }[] = data.models || [];

    const newModelData: ModelData = {
      providers: [],
      families: {},
      models: {},
    };

    all_models_raw.forEach((m) => {
      const p = m.provider === "ollama" ? "Ollama Local" : "Groq Cloud";
      if (!newModelData.providers.includes(p)) {
        newModelData.providers.push(p);
        newModelData.families[p] = ["General"];
      }
      const familyKey = "General";
      if (!newModelData.models[familyKey]) {
        newModelData.models[familyKey] = [];
      }
      newModelData.models[familyKey].push(m.id);
    });

    allModelData.set(newModelData);

    // Set initial selections if not already set
    if (!get(provider)) provider.set("Ollama Local");
    if (!get(family)) family.set("General");

    // Smart default: Prefer deepseek-r1:1.5b or tinyllama if available
    const currentModel = get(model);
    const flattenedModels = all_models_raw.map((m) => m.id);

    if (!currentModel && flattenedModels.length > 0) {
      if (flattenedModels.includes("deepseek-r1:1.5b")) {
        model.set("deepseek-r1:1.5b");
      } else if (flattenedModels.includes("tinyllama:latest")) {
        model.set("tinyllama:latest");
      } else {
        model.set(flattenedModels[0]);
      }
    }
  } catch (error) {
    app.setError(`Failed to load models: ${error.message}`, true);
  }
}

// REMOVED: old refinePrompt function
/*
export async function refinePrompt() {
  const currentOriginal = get(originalPrompt);
  const currentModel = get(model); // Use the new 'model' store
  const currentIntent = get(selectedIntent);

  if (!currentOriginal || !currentModel) {
    app.setError('Please enter a prompt and select a model.', false);
    return;
  }

  app.setLoading(true);
  app.clearMessages();

  try {
    const refined = await apiRefinePrompt(currentModel, currentOriginal, { intent: currentIntent });
    refinedPrompt.set(refined);
    addToHistory(currentOriginal, refined, currentModel, currentIntent);
    app.setSuccess('Prompt refined successfully!');
  } catch (err) {
    app.setError(err.message, true);
  } finally {
    app.setLoading(false);
  }
}
*/

export function clearAll() {
  originalPrompt.set('');
  refinedPrompt.set('');
  app.clearMessages();
  selectedProfileKey.set(''); // NEW: Clear selected profile too
}

// Reset family and model when provider changes
provider.subscribe($provider => {
  family.set('');
  model.set('');
});

// Reset model when family changes
family.subscribe($family => {
  model.set('');
});