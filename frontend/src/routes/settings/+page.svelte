<script lang="ts">
  import { onMount } from "svelte";
  import { Store } from "@tauri-apps/plugin-store";
  import Button from "$lib/components/common/Button.svelte";
  import { app } from "$lib/stores/app";

  let groqApiKey: string = "";
  let store: Store | null = null;
  let isLoading = true;

  onMount(async () => {
    try {
        if (window.__TAURI__) {
            store = await Store.load("app-settings.dat");
            if (store) {
                groqApiKey = ((await store.get("GROQ_API_KEY")) as string) || "";
            }
        }
    } catch (e) {
        console.error("Store initialization failed:", e);
    } finally {
        isLoading = false;
    }
  });

  async function saveApiKey() {
    if (!store) {
        app.setError("Configuration store unavailable (Tauri required).", false);
        return;
    }
    
    try {
      if (groqApiKey) {
        await store.set("GROQ_API_KEY", groqApiKey);
        await store.save();
        app.setSuccess("Groq API Key secured successfully.");
      } else {
        await store.delete("GROQ_API_KEY");
        await store.save();
        app.setSuccess("Groq API Key cleared.");
      }
    } catch (e: any) {
      app.setError(`Failed to save configuration: ${e.message}`, true);
    }
  }
</script>

<div class="premium-panel max-w-2xl mx-auto w-full p-8 space-y-8 animate-in fade-in duration-500">
  <div class="border-b border-slate-800 pb-6 text-center">
    <h2 class="text-xl font-black text-white tracking-tighter uppercase">
      Infrastructure <span class="text-indigo-500">Control</span>
    </h2>
    <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">Environment & Secrets Management</p>
  </div>

  <div class="space-y-6">
    <div class="space-y-2">
      <div class="flex justify-between items-end px-1">
          <label for="groqApiKey" class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Groq Cloud API Key</label>
          <a href="https://console.groq.com/keys" target="_blank" class="text-[9px] font-bold text-indigo-400 hover:text-indigo-300 uppercase underline">Get Key</a>
      </div>
      <input
        type="password"
        id="groqApiKey"
        class="w-full premium-input bg-[#1c2127] border-slate-800 text-sm font-mono tracking-widest"
        bind:value={groqApiKey}
        placeholder="gsk_********************************"
      />
      <div class="bg-indigo-500/5 border-l-2 border-indigo-500 p-4 rounded-r-xl">
          <p class="text-[10px] font-bold text-slate-400 leading-relaxed uppercase tracking-wider">
            🔐 Local Isolation Protocol:
          </p>
          <p class="text-[10px] font-medium text-slate-500 mt-1">
            Your keys are stored within the Tauri isolation layer and never leave this node except to authorized provider endpoints.
          </p>
      </div>
    </div>
  </div>

  <div class="flex justify-end pt-4">
    <Button on:click={saveApiKey} primary disabled={isLoading}>
      {#if isLoading}
        Synchronizing...
      {:else}
        Commit Configuration
      {/if}
    </Button>
  </div>
</div>

<div class="max-w-2xl mx-auto mt-8 px-4 text-center">
    <a href="/" class="text-[10px] font-black text-slate-600 hover:text-indigo-400 uppercase tracking-widest transition-colors flex items-center justify-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
        Return to Architect
    </a>
</div>
