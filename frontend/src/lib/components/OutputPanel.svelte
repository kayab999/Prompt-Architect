<script lang="ts">
  import { refinedPrompt } from "$lib/stores/prompt";
  import { app } from "$lib/stores/app";
  import { copyToClipboard } from "$lib/services/tauri";

  async function handleCopy() {
    if (!$refinedPrompt) return;
    await copyToClipboard($refinedPrompt);
    app.setSuccess(" Copied to clipboard!");
  }
</script>

<div class="premium-panel flex flex-col h-full relative group">
  <div class="px-6 py-4 bg-[#1c2127]/50 border-b border-slate-800 flex justify-between items-center">
    <h2 class="text-sm font-bold tracking-widest text-slate-400 uppercase flex items-center gap-2">
      <span class="text-indigo-400"></span>
      Refined Prompt
    </h2>
    
    {#if $refinedPrompt}
      <button 
        class="text-xs bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-4 py-1.5 rounded-full transition-all shadow-lg shadow-indigo-600/20 active:scale-95"
        on:click={handleCopy}
      >
        Copy
      </button>
    {/if}
  </div>
  
  <div class="flex-grow flex flex-col p-6 bg-[#0e1013]">
    <textarea 
      readonly 
      bind:value={$refinedPrompt}
      placeholder="Your architectural masterpiece will appear here..."
      class="flex-grow bg-transparent border-none focus:ring-0 text-indigo-100 placeholder-slate-700 font-mono text-sm leading-relaxed resize-none p-0"
    ></textarea>
  </div>
  
  <div class="px-6 py-3 bg-[#1c2127]/30 border-t border-slate-800 flex justify-between items-center text-[10px] font-bold uppercase tracking-wider text-slate-600">
    <span>{$refinedPrompt ? $refinedPrompt.length + ' characters' : 'Standby'}</span>
    {#if $refinedPrompt}
      <span class="text-emerald-500 flex items-center gap-1">
        <span class="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
        Ready to deploy
      </span>
    {/if}
  </div>
</div>

<style>
  textarea::-webkit-scrollbar {
    display: none;
  }
  textarea {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
</style>
