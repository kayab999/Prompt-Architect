<script lang="ts">
  import { onMount } from "svelte";
  import { writable, get } from "svelte/store";
  import { originalPrompt } from "$lib/stores/prompt";

  interface Challenge {
    id: number;
    task: string;
    explanation: string;
  }

  const challenges = writable<Challenge[]>([]);
  const currentChallenge = writable<Challenge | null>(null);
  const showExplanation = writable(false);

  async function loadChallenges() {
    try {
      const res = await fetch("/challenges.json");
      const data = await res.json();
      challenges.set(data);
      if (data.length > 0) {
        currentChallenge.set(data[0]);
      }
    } catch (err) {
      console.error("Error loading challenges:", err);
    }
  }

  function selectChallenge(challenge: Challenge) {
    currentChallenge.set(challenge);
    showExplanation.set(false);
  }

  function loadChallengePrompt() {
    const challenge = get(currentChallenge);
    if (challenge) {
      originalPrompt.set(challenge.task);
    }
  }

  onMount(loadChallenges);
</script>

<div class="premium-panel p-8 space-y-8 max-w-4xl mx-auto">
  <div class="border-b border-slate-800 pb-6">
    <h2 class="text-xl font-black text-white tracking-tight flex items-center gap-2">
      <span class="text-indigo-500"></span>
      ACADEMY: INTERACTIVE CHALLENGES
    </h2>
    <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">Master the art of Prompt Architecture</p>
  </div>

  <div class="grid md:grid-cols-3 gap-8">
    <div class="space-y-4">
      <h3 class="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Curriculum</h3>
      <div class="space-y-2">
        {#each $challenges as challenge}
          <button
            class="w-full text-left px-4 py-3 rounded-xl border transition-all text-xs font-bold uppercase tracking-tight {get(currentChallenge)?.id === challenge.id 
                ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-600/20' 
                : 'bg-slate-800/50 border-slate-800 text-slate-400 hover:border-slate-600'}"
            on:click={() => selectChallenge(challenge)}
          >
            Level {challenge.id}
          </button>
        {/each}
      </div>
    </div>

    <div class="md:col-span-2 space-y-6">
      {#if $currentChallenge}
        <div class="bg-slate-950/50 rounded-2xl border border-slate-800 p-6 space-y-6">
          <div class="space-y-2">
            <h3 class="text-[10px] font-black text-indigo-400 uppercase tracking-widest">The Mission</h3>
            <p class="text-sm font-medium leading-relaxed text-slate-200">{$currentChallenge.task}</p>
          </div>

          <div class="flex flex-wrap gap-3">
            <button 
                class="bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-black uppercase tracking-widest px-6 py-2.5 rounded-xl shadow-lg shadow-indigo-600/20 active:scale-95 transition-all"
                on:click={loadChallengePrompt}
            >
              Inject to Architect
            </button>
            <button 
                class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-black uppercase tracking-widest px-6 py-2.5 rounded-xl border border-slate-700 active:scale-95 transition-all"
                on:click={() => showExplanation.set(!$showExplanation)}
            >
              {#if $showExplanation}Hide Intel{:else}Reveal Intel{/if}
            </button>
          </div>

          {#if $showExplanation}
            <div class="bg-indigo-500/5 border-l-2 border-indigo-500 p-4 rounded-r-xl space-y-2 animate-in fade-in slide-in-from-top-2 duration-300">
              <h4 class="text-[9px] font-black text-indigo-400 uppercase tracking-widest">Architectural Insight</h4>
              <p class="text-xs text-slate-400 leading-relaxed italic">{$currentChallenge.explanation}</p>
            </div>
          {/if}
        </div>
      {:else}
        <div class="h-full flex flex-col items-center justify-center opacity-40 py-20">
            <div class="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center mb-4">
                <span class="text-2xl"></span>
            </div>
            <p class="text-xs font-black uppercase tracking-widest">Awaiting Uplink</p>
        </div>
      {/if}
    </div>
  </div>
</div>
