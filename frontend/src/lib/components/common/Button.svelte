<script lang="ts">
  export let primary = false;
  export let disabled = false;
</script>

<button 
  class="relative flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl font-semibold transition-all duration-200 active:scale-[0.98] disabled:opacity-50 disabled:grayscale disabled:pointer-events-none group whitespace-nowrap {primary ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'}"
  {disabled} 
  on:click
>
  <slot />
</button>

<style>
  /* Keep only what Tailwind doesn't handle easily or for specific micro-interactions */
  button:hover:not(:disabled) {
    @apply -translate-y-0.5;
  }
</style>
