<script lang="ts">
  import { onMount } from "svelte";
  import { Store } from "@tauri-apps/plugin-store";
  import Button from "$lib/components/common/Button.svelte";
  import { app } from "$lib/stores/app";
  import { isTauriRuntime } from "$lib/services/tauri";
  import { backendFetch } from "$lib/services/backendUrl";

  // The key is stored backend-side in a 0600 file inside the OS data dir.
  // The input is always empty: the UI never displays or round-trips the key.
  let groqApiKeyInput: string = "";
  let isLoading = true;
  let groqConfigured = false;
  let groqSource: string = "unset";
  let legacyMigrated = false;

  async function refreshStatus() {
    try {
      const res = await backendFetch("/settings/groq");
      if (res.ok) {
        const data = await res.json();
        groqConfigured = Boolean(data.groq_configured);
        groqSource = String(data.source || "unset");
      }
    } catch {
      // backend unreachable — leave defaults
    }
  }

  // One-time migration: old versions stored the key in the Tauri store
  // (plaintext file) and round-tripped it on every generate. Push it to the
  // backend once, then delete it from the store.
  async function migrateLegacyStoreKey() {
    if (!isTauriRuntime()) return;
    try {
      const store = await Store.load("app-settings.dat");
      const legacyKey = (await store.get("GROQ_API_KEY")) as string | undefined;
      if (!legacyKey || !legacyKey.trim()) return;
      const res = await backendFetch("/settings/groq", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: legacyKey.trim() }),
      });
      if (res.ok) {
        await store.delete("GROQ_API_KEY");
        await store.save();
        legacyMigrated = true;
      } else {
        app.setError(
          "A previously stored Groq key was found but could not be migrated. Please re-enter it.",
          false
        );
      }
    } catch (e) {
      console.error("Legacy key migration failed:", e);
    }
  }

  onMount(async () => {
    try {
      await migrateLegacyStoreKey();
      await refreshStatus();
    } catch (e) {
      console.error("Settings initialization failed:", e);
    } finally {
      isLoading = false;
    }
  });

  async function saveApiKey() {
    if (!groqApiKeyInput.trim()) {
      app.setError(
        "Enter the API key, or clear it with the button below.",
        false
      );
      return;
    }
    try {
      const res = await backendFetch("/settings/groq", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: groqApiKeyInput.trim() }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || `HTTP ${res.status}`);
      }
      groqApiKeyInput = "";
      app.setSuccess("Groq API key stored backend-side (0600).");
      await refreshStatus();
    } catch (e: any) {
      app.setError(`Failed to save configuration: ${e.message}`, true);
    }
  }

  async function clearApiKey() {
    try {
      const res = await backendFetch("/settings/groq", { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      groqApiKeyInput = "";
      app.setSuccess("Groq API key cleared.");
      await refreshStatus();
    } catch (e: any) {
      app.setError(`Failed to clear key: ${e.message}`, true);
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

      {#if !isLoading}
        <div class="flex items-center gap-2 px-1 text-[10px] font-bold uppercase tracking-wider">
          {#if groqConfigured}
            <span class="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
            <span class="text-emerald-500">
              Key configured (source: {groqSource === "env" ? "environment" : "backend store (0600)"})
            </span>
          {:else}
            <span class="w-1.5 h-1.5 bg-slate-600 rounded-full"></span>
            <span class="text-slate-500">No key configured</span>
          {/if}
          {#if legacyMigrated}
            <span class="text-indigo-400">· Legacy UI-store key migrated</span>
          {/if}
        </div>
      {/if}

      <input
        type="password"
        id="groqApiKey"
        class="w-full premium-input bg-[#1c2127] border-slate-800 text-sm font-mono tracking-widest"
        bind:value={groqApiKeyInput}
        placeholder={groqConfigured ? "Stored (hidden — enter a new key to replace)" : "gsk_********************************"}
      />

      <div class="bg-indigo-500/5 border-l-2 border-indigo-500 p-4 rounded-r-xl">
          <p class="text-[10px] font-bold text-slate-400 leading-relaxed uppercase tracking-wider">
            🔐 Local Isolation Protocol:
          </p>
          <p class="text-[10px] font-medium text-slate-500 mt-1">
            The key is stored backend-side in a permissions-tightened (0600) file within the OS data directory. The UI never displays it and generation requests never carry it — the backend attaches it to authorized provider calls.
          </p>
      </div>
    </div>
  </div>

  <div class="flex justify-end gap-3 pt-4">
    {#if groqConfigured}
      <button
        class="text-xs bg-slate-800 hover:bg-red-500/10 hover:text-red-400 border border-slate-700 px-3 py-1 rounded-full transition-all uppercase font-bold tracking-wider"
        on:click={clearApiKey}
        disabled={isLoading}
      >
        Clear Key
      </button>
    {/if}
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
