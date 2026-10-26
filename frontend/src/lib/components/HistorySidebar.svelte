<script lang="ts">
  import { history, clearHistory, loadFromHistory } from '$lib/stores/history';
  import { fly } from 'svelte/transition';
</script>

<div class="fixed right-0 top-0 w-80 h-screen bg-slate-900/95 backdrop-blur-xl border-l border-slate-800 shadow-2xl z-[100] flex flex-col" transition:fly={{ x: 320, duration: 300 }}>
  <div class="px-6 py-8 border-b border-slate-800/50 flex justify-between items-center bg-slate-950/20">
    <div>
        <h3 class="text-sm font-black text-white uppercase tracking-[0.2em]">Archive</h3>
        <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">Prompt Execution History</p>
    </div>
    <button 
        class="p-2 hover:bg-rose-500/10 text-slate-500 hover:text-rose-500 rounded-xl transition-all disabled:opacity-30 disabled:pointer-events-none" 
        on:click={clearHistory} 
        title="Clear history" 
        disabled={$history.length === 0}
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path></svg>
    </button>
  </div>
  
  <div class="flex-grow overflow-y-auto px-4 py-6 space-y-3 custom-scrollbar">
    {#if $history.length === 0}
      <div class="h-full flex flex-col items-center justify-center text-center opacity-40 px-6">
        <div class="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center mb-4 rotate-12">
            <span class="text-2xl">📁</span>
        </div>
        <p class="text-xs font-black uppercase tracking-widest text-slate-400">Vault Empty</p>
        <p class="text-[10px] font-bold text-slate-600 mt-2 uppercase tracking-tighter">Your architectural designs will persist here once generated.</p>
      </div>
    {:else}
      {#each $history as entry (entry.id)}
        <button 
          class="w-full text-left bg-slate-800/30 hover:bg-slate-800/80 border border-slate-800/50 hover:border-indigo-500/30 rounded-2xl p-4 transition-all group active:scale-[0.98]" 
          on:click={() => loadFromHistory(entry)} 
        >
          <div class="text-[11px] font-medium text-slate-400 line-clamp-3 mb-4 group-hover:text-slate-200 transition-colors leading-relaxed">
            {entry.original}
          </div>
          <div class="flex justify-between items-center pt-3 border-t border-slate-800/50">
            <span class="text-[9px] font-black text-indigo-400 uppercase tracking-widest bg-indigo-500/10 px-2 py-0.5 rounded-md">{entry.profileKey}</span>
            <span class="text-[9px] font-bold text-slate-600 uppercase tracking-tighter">{entry.timestamp}</span>
          </div>
        </button>
      {/each}
    {/if}
  </div>
</div>

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    @apply bg-slate-800 rounded-full;
  }
</style>
