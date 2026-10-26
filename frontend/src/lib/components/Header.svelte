<script lang="ts">
  import { connectionState } from '$lib/services/api';
  import { isTauri } from '$lib/services/tauri';
  import { clearAll } from '$lib/stores/prompt';
</script>

<header class="flex justify-between items-center px-2 py-4 bg-transparent border-b border-slate-800/50 mb-6">
  <div class="flex items-center gap-4">
    <div class="w-12 h-12 bg-gradient-to-br from-indigo-600 to-violet-700 rounded-2xl flex items-center justify-center shadow-2xl shadow-indigo-500/20 rotate-3 hover:rotate-0 transition-transform duration-300">
      <span class="text-2xl">📐</span>
    </div>
    <div>
      <h1 class="text-xl font-black text-white tracking-tighter italic">PROMPT ARCHITECT <span class="text-xs font-normal not-italic text-slate-500 ml-1">v1.0.2-rc.1</span></h1>
      <div class="flex items-center gap-2">
        <div class="relative flex items-center justify-center">
            <span class="absolute w-2 h-2 rounded-full animate-ping opacity-75"
                class:bg-emerald-500={$connectionState.status === 'connected'} 
                class:bg-rose-500={$connectionState.status === 'error'} 
                class:bg-amber-500={$connectionState.status === 'connecting'}
            ></span>
            <span class="relative w-2 h-2 rounded-full" 
                class:bg-emerald-500={$connectionState.status === 'connected'} 
                class:bg-rose-500={$connectionState.status === 'error'} 
                class:bg-amber-500={$connectionState.status === 'connecting'}
            ></span>
        </div>
        <span class="text-[9px] font-black text-slate-500 uppercase tracking-[0.2em]">
          {$connectionState.status === 'connected' ? 'Core Stable' : 'Link Failure'}
        </span>
      </div>
    </div>
  </div>

  <div class="flex items-center gap-4">
    <button 
      class="text-[10px] font-black text-slate-500 hover:text-rose-400 uppercase tracking-widest transition-colors"
      on:click={clearAll}
    >
      Purge All
    </button>
    
    <a 
      href="/settings" 
      class="bg-slate-800/50 hover:bg-slate-800 text-white p-2.5 rounded-xl border border-slate-700 transition-all hover:scale-105 active:scale-95"
      title="Settings"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
        <circle cx="12" cy="12" r="3"></circle>
      </svg>
    </a>
  </div>
</header>