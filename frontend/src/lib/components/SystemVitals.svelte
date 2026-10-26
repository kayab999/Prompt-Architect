<script lang="ts">
  import { onMount } from "svelte";

  type HostVitals = {
    cpu_percent: number;
    ram_percent: number;
    temperature: number | null;
    gpu_load: number | null;
    tier_id: number;
    tier_name: string;
    ollama_online: boolean;
    groq_configured: boolean;
  };

  let vitals: HostVitals = {
    cpu_percent: 0,
    ram_percent: 0,
    temperature: null,
    gpu_load: null,
    tier_id: 0,
    tier_name: "unknown",
    ollama_online: false,
    groq_configured: false,
  };
  let error_state = false;

  async function fetchVitals() {
    try {
      const { backendFetch } = await import("$lib/services/backendUrl");
      const res = await backendFetch("/vital-signs");
      if (res.ok) {
        const data = await res.json();
        vitals = {
          cpu_percent: Number(data.cpu_percent ?? 0),
          ram_percent: Number(data.ram_percent ?? 0),
          temperature:
            data.temperature === null || data.temperature === undefined
              ? null
              : Number(data.temperature),
          gpu_load:
            data.gpu_load === null || data.gpu_load === undefined
              ? null
              : Number(data.gpu_load),
          tier_id: Number(data.tier_id ?? 0),
          tier_name: data.tier_name || "unknown",
          ollama_online: Boolean(data.ollama_online),
          groq_configured: Boolean(data.groq_configured),
        };
        error_state = false;
      } else {
        error_state = true;
      }
    } catch {
      error_state = true;
    }
  }

  onMount(() => {
    fetchVitals();
    const interval = setInterval(fetchVitals, 2000);
    return () => clearInterval(interval);
  });
</script>

<div
  class="p-4 bg-black text-xs font-mono border border-gray-800 rounded shadow-md w-72"
>
  <div class="flex justify-between items-center mb-2">
    <h3 class="text-gray-500 uppercase tracking-wider">Host Vitals</h3>
    {#if error_state}
      <span
        class="w-2 h-2 rounded-full bg-red-900 animate-pulse"
        title="Offline"
      ></span>
    {:else}
      <span
        class="w-2 h-2 rounded-full bg-green-500 animate-pulse"
        title="Online"
      ></span>
    {/if}
  </div>

  <div class="space-y-3">
    <div>
      <div class="flex justify-between text-gray-400">
        <span>CPU</span>
        <span>{vitals.cpu_percent.toFixed(1)}%</span>
      </div>
      <div class="w-full bg-gray-900 h-1.5 rounded-sm overflow-hidden">
        <div
          class="bg-red-500 h-full transition-all duration-500 ease-out"
          style="width: {Math.min(100, vitals.cpu_percent)}%"
        ></div>
      </div>
    </div>

    <div>
      <div class="flex justify-between text-gray-400">
        <span>RAM</span>
        <span>{vitals.ram_percent.toFixed(1)}%</span>
      </div>
      <div class="w-full bg-gray-900 h-1.5 rounded-sm overflow-hidden">
        <div
          class="bg-blue-500 h-full transition-all duration-500 ease-out"
          style="width: {Math.min(100, vitals.ram_percent)}%"
        ></div>
      </div>
    </div>

    <div>
      <div class="flex justify-between text-gray-400">
        <span>GPU load</span>
        <span
          >{vitals.gpu_load === null
            ? "n/a"
            : `${Number(vitals.gpu_load).toFixed(1)}%`}</span
        >
      </div>
      <div class="w-full bg-gray-900 h-1.5 rounded-sm overflow-hidden">
        <div
          class="bg-green-500 h-full transition-all duration-500 ease-out"
          style="width: {vitals.gpu_load === null
            ? 0
            : Math.min(100, Number(vitals.gpu_load))}%"
        ></div>
      </div>
    </div>

    <div
      class="text-[10px] text-gray-600 pt-1 border-t border-gray-900 mt-2 space-y-1"
    >
      <div class="flex justify-between">
        <span>Temp</span>
        <span
          >{vitals.temperature === null
            ? "n/a"
            : `${vitals.temperature.toFixed(0)}°C`}</span
        >
      </div>
      <div class="flex justify-between">
        <span>Tier</span>
        <span class="text-gray-400"
          >{vitals.tier_name} (#{vitals.tier_id})</span
        >
      </div>
      <div class="flex justify-between">
        <span>Ollama</span>
        <span class={vitals.ollama_online ? "text-emerald-500" : "text-rose-500"}
          >{vitals.ollama_online ? "online" : "offline"}</span
        >
      </div>
      <div class="flex justify-between">
        <span>Groq key</span>
        <span
          class={vitals.groq_configured ? "text-emerald-500" : "text-slate-500"}
          >{vitals.groq_configured ? "set" : "unset"}</span
        >
      </div>
    </div>
  </div>
</div>
