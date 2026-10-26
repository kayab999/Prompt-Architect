<script lang="ts">
  import { onMount } from "svelte";
  import { app } from "$lib/stores/app";
  import { history, showHistory, loadHistory } from "$lib/stores/history";
  import {
    initializeBackend,
    reconnectBackend,
    connectionState,
  } from "$lib/services/api";
  import { initializeTauri } from "$lib/services/tauri";

  import Header from "$lib/components/Header.svelte";
  import InputPanel from "$lib/components/InputPanel.svelte";
  import OutputPanel from "$lib/components/OutputPanel.svelte";
  import HistorySidebar from "$lib/components/HistorySidebar.svelte";
  import Message from "$lib/components/common/Message.svelte";
  import { loadModels } from "$lib/stores/prompt";
  import VisualBuilder from "$lib/components/VisualBuilder.svelte";

  // Toggle State
  let mode: "text" | "visual" = "text";

  onMount(async () => {
    await initializeBackend();
    await loadModels();
    initializeTauri();
    loadHistory();
  });

  async function handleRetryConnection() {
    app.setLoading(true);
    app.clearMessages();
    try {
      await reconnectBackend();
      await loadModels();
    } catch (error: any) {
      app.setError(`Failed to reconnect: ${error.message}`, true);
    } finally {
      app.setLoading(false);
    }
  }
</script>

<div class="min-h-screen bg-[#0b0d0f] text-slate-200 flex flex-col p-4 md:p-8 space-y-6 max-w-[1600px] mx-auto">
  <Header />

  <!-- MODE TOGGLE -->
  <div class="flex justify-center">
    <div class="bg-slate-900/50 p-1 rounded-2xl flex gap-1 border border-slate-800 backdrop-blur-sm">
      <button
        class="px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all duration-300 {mode === 'text'
          ? 'bg-indigo-600 text-white shadow-xl shadow-indigo-600/20'
          : 'text-slate-500 hover:text-slate-300'}"
        on:click={() => (mode = "text")}
      >
        Architect
      </button>
      <button
        class="px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all duration-300 {mode === 'visual'
          ? 'bg-indigo-600 text-white shadow-xl shadow-indigo-600/20'
          : 'text-slate-500 hover:text-slate-300'}"
        on:click={() => (mode = "visual")}
      >
        Visualizer
      </button>
    </div>
  </div>

  <main class="flex-grow flex flex-col">
    {#if mode === "text"}
      <section class="grid lg:grid-cols-2 gap-8 flex-grow">
        <InputPanel />
        <OutputPanel />
      </section>
    {:else}
      <VisualBuilder />
    {/if}
  </main>

  <!-- Notification Layer -->
  <div class="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 w-full max-w-md px-4 pointer-events-none">
    {#if $app.errorMessage}
      <Message
        type="error"
        message={$app.errorMessage}
        persistent={$app.isErrorPersistent}
      >
        {#if $connectionState.status === "error"}
          <button
            class="bg-rose-600 hover:bg-rose-500 text-white px-3 py-1 rounded-lg text-[10px] font-bold uppercase ml-3 transition-colors pointer-events-auto"
            on:click={handleRetryConnection}
          >
            Retry
          </button>
        {/if}
      </Message>
    {/if}
    {#if $app.successMessage}
      <Message type="success" message={$app.successMessage} />
    {/if}
  </div>

  <!-- History Sidebar Toggle -->
  <button
    class="history-toggle fixed left-0 top-1/2 -translate-y-1/2 bg-slate-800/80 hover:bg-indigo-600 backdrop-blur-md text-white py-6 px-1.5 rounded-r-2xl text-[10px] font-black uppercase tracking-widest z-40 transition-all border border-slate-700/50 hover:border-indigo-400"
    class:active={$showHistory}
    on:click={() => showHistory.update((s) => !s)}
    title="Toggle history"
  >
    <div class="vertical-text">
        {$showHistory ? 'Close History' : `History [${$history.length}]`}
    </div>
  </button>

  {#if $showHistory}
    <HistorySidebar />
  {/if}
</div>

<style lang="postcss">
  .vertical-text {
    writing-mode: vertical-lr;
    text-orientation: mixed;
    transform: rotate(180deg);
  }
</style>
