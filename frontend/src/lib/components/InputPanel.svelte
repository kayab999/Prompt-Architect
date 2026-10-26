<script lang="ts">
  import ProfileSelector from "./ProfileSelector.svelte";
  import { isTauriRuntime } from "../services/tauri";
  import {
    originalPrompt,
    model,
    provider,
    allModelData,
    availableModels,
    selectedProfileKey,
    activeTemplate,
    templateVariables,
    refinedPrompt,
  } from "$lib/stores/prompt";
  import { onMount } from "svelte";
  import { app } from "$lib/stores/app";
  import { backendFetch } from "$lib/services/backendUrl";

  let textarea: HTMLTextAreaElement;

  function handleProfileSelected(event: CustomEvent<{ key: string }>) {
    $selectedProfileKey = event.detail.key;
  }

  function clearTemplate() {
    activeTemplate.set(null);
    templateVariables.set({});
  }

  // Auto-resize logic for the prompt area
  $: if (textarea && $originalPrompt !== undefined) {
    textarea.style.height = "auto";
    const newHeight = Math.max(160, textarea.scrollHeight);
    textarea.style.height = `${newHeight}px`;
  }

  async function generateContent() {
    const currentOriginal = $originalPrompt;
    const currentProfileKey = $selectedProfileKey;
    const currentModel = $model;

    if (!currentOriginal) {
      app.setError("Please enter a prompt.", false);
      return;
    }
    if (!currentProfileKey) {
      app.setError("Please select a persona profile.", false);
      return;
    }

    app.setLoading(true);
    app.clearMessages();

    try {
      // Dynamic check for Groq based on model name pattern
      const isGroqModel = currentModel.startsWith("llama-3") || 
                         currentModel.startsWith("mixtral") || 
                         currentModel.startsWith("gemma") || 
                         currentModel.startsWith("qwen-2.5");

      let groqApiKey: string | undefined;
      if (isGroqModel) {
        if (isTauriRuntime()) {
          const { Store } = await import("@tauri-apps/plugin-store");
          const store = await Store.load("app-settings.dat");
          groqApiKey = (await store.get("GROQ_API_KEY")) as string;
        } else {
          app.setError("Groq models require the desktop app.", true);
          return;
        }
        if (!groqApiKey) {
          app.setError("Groq API Key not found in settings.", true);
          return;
        }
      }

      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (groqApiKey) headers["X-Groq-Api-Key"] = groqApiKey;

      const res = await backendFetch("/generate", {
        method: "POST",
        headers,
        body: JSON.stringify({
          user_input: currentOriginal,
          profile_key: currentProfileKey,
          model: currentModel,
        }),
      });

      if (!res.ok) {
        let detail = "Server error";
        try {
          const errorData = await res.json();
          detail =
            typeof errorData.detail === "string"
              ? errorData.detail
              : JSON.stringify(errorData.detail || errorData);
        } catch {
          /* ignore parse errors */
        }
        throw new Error(detail);
      }

      const data = await res.json();
      refinedPrompt.set(data.response || "");
      if (data.success === false) {
        app.setError(
          data.reason
            ? `Partial refinement: ${data.reason}`
            : "Refinement completed with warnings.",
          false
        );
      } else {
        app.setSuccess("Refinement complete!");
      }
    } catch (err: any) {
      app.setError(err.message, true);
    } finally {
      app.setLoading(false);
    }
  }
</script>

<div class="premium-panel flex flex-col h-full transition-all duration-300">
  <div class="px-6 py-4 bg-[#1c2127]/50 border-b border-slate-800 flex justify-between items-center">
    <h2 class="text-sm font-bold tracking-widest text-slate-400 uppercase flex items-center gap-2">
      <span class="text-indigo-400">
        {#if $activeTemplate}🧩{:else}✏️{/if}
      </span>
      {$activeTemplate ? `Template: ${$activeTemplate.category}` : "Original Prompt"}
    </h2>
    {#if $activeTemplate}
      <button 
        class="text-xs bg-slate-800 hover:bg-red-500/10 hover:text-red-400 border border-slate-700 px-3 py-1 rounded-full transition-all"
        on:click={clearTemplate}
      >
        Clear Template
      </button>
    {/if}
  </div>

  <div class="p-6 space-y-6">
    <!-- Configuration Grid -->
    <div class="grid grid-cols-2 gap-4">
      <div class="space-y-2">
        <label for="provider-select" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Provider</label>
        <select 
          id="provider-select" 
          bind:value={$provider} 
          class="w-full premium-input bg-[#1c2127] border-slate-800 focus:ring-indigo-500/30 text-sm cursor-pointer"
        >
          {#each $allModelData.providers as p}
            <option value={p}>{p}</option>
          {/each}
        </select>
      </div>

      <div class="space-y-2">
        <label for="model-select" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Model</label>
        <select 
          id="model-select" 
          bind:value={$model} 
          class="w-full premium-input bg-[#1c2127] border-slate-800 focus:ring-indigo-500/30 text-sm cursor-pointer"
        >
          {#each $availableModels as m}
            <option value={m}>{m}</option>
          {/each}
        </select>
      </div>

      <div class="col-span-2 space-y-2">
        <label for="persona-select" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Persona Profile</label>
        <ProfileSelector
          id="persona-select"
          on:profileSelected={handleProfileSelected}
        />
      </div>
    </div>

    <!-- Template Variables -->
    {#if $activeTemplate}
      <div class="space-y-4 pt-2">
        <h3 class="text-xs font-bold text-indigo-400 uppercase tracking-wider">Template Variables</h3>
        <div class="grid gap-3">
          {#each $activeTemplate.variables as variable}
            <div class="space-y-1">
              <label class="text-[10px] font-semibold text-slate-500 px-1" for="var-{variable}">{variable}</label>
              <input
                id="var-{variable}"
                type="text"
                class="w-full premium-input py-2 text-sm"
                bind:value={$templateVariables[variable]}
                placeholder="Value for {variable}..."
              />
            </div>
          {/each}
        </div>
        {#if $activeTemplate.guidelines}
          <div class="bg-indigo-500/5 border-l-2 border-indigo-500 p-3 rounded-r-lg text-xs text-slate-400 italic">
            <strong>Tip:</strong> {$activeTemplate.guidelines}
          </div>
        {/if}
      </div>
    {/if}

    <!-- Prompt Area -->
    <div class="relative group pt-2">
      <textarea
        bind:this={textarea}
        bind:value={$originalPrompt}
        placeholder="Enter your instructions here... Use XML-style tags for better results."
        readonly={$activeTemplate !== null}
        class="w-full bg-transparent border-none focus:ring-0 text-slate-100 placeholder-slate-600 font-mono text-sm leading-relaxed resize-none p-0 transition-all"
        class:opacity-60={$activeTemplate !== null}
      ></textarea>
      
      {#if $originalPrompt.length > 0}
        <div class="absolute bottom-[-1.5rem] right-0 flex items-center gap-4 text-[10px] font-medium text-slate-500">
          <span class:text-orange-400={$originalPrompt.length >= 1001}>
            {$originalPrompt.length} chars
          </span>
          {#if $originalPrompt.length >= 1001}
            <span class="flex items-center gap-1 text-orange-400 animate-pulse">
              ⚠️ Long prompt
            </span>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Contextual Action -->
    <div class="pt-6 flex justify-end">
      <button
        disabled={!$originalPrompt || !$selectedProfileKey || $app.loading}
        class="group relative flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-bold px-8 py-3 rounded-xl transition-all shadow-xl shadow-indigo-600/20 active:scale-95 overflow-hidden"
        on:click={generateContent}
      >
        {#if $app.loading}
          <span class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          <span>Architecting...</span>
        {:else}
          <span class="text-lg group-hover:scale-110 transition-transform">⚡</span>
          <span>Generate Refined Prompt</span>
        {/if}
      </button>
    </div>
  </div>
</div>

<style>
  textarea::-webkit-scrollbar {
    display: none;
  }
  textarea {
    -ms-overflow-style: none;
    scrollbar-width: none;
    min-height: 160px;
  }
</style>
