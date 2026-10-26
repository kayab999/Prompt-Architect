<script lang="ts">
  import { app } from '$lib/stores/app';
  import { fly } from 'svelte/transition';
  import { onMount } from 'svelte';

  export let type: 'error' | 'success';
  export let message: string;
  export let persistent = false;

  function dismiss() {
    app.clearMessages();
  }

  onMount(() => {
    if (!persistent && type === 'success') {
      const timer = setTimeout(() => {
        dismiss();
      }, 4000);
      return () => clearTimeout(timer);
    }
  });
</script>

{#if message}
  <div 
    class="flex items-center gap-4 px-6 py-4 rounded-2xl shadow-2xl border backdrop-blur-xl transition-all w-full pointer-events-auto {type === 'error' ? 'bg-rose-500/10 border-rose-500/30 text-rose-400' : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'}"
    role={type === 'error' ? 'alert' : 'status'} 
    transition:fly={{ y: 50, duration: 400 }}
  >
    <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm {type === 'error' ? 'bg-rose-500/20' : 'bg-emerald-500/20'}">
      {type === 'error' ? '✕' : '✓'}
    </div>

    <div class="flex-grow">
      <h4 class="text-[10px] font-black uppercase tracking-[0.2em] opacity-50 mb-0.5">
        {type === 'error' ? 'System Warning' : 'Operation Success'}
      </h4>
      <p class="text-xs font-bold leading-tight">{message}</p>
    </div>

    <slot />

    {#if persistent}
      <button 
        class="ml-2 p-1 hover:bg-white/10 rounded-lg transition-colors" 
        on:click={dismiss} 
        aria-label="Dismiss"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    {/if}
  </div>
{/if}
