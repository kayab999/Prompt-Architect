<script lang="ts">
    import { onMount } from 'svelte';
    import { connectionState } from '../services/mcpAdapter';
    import { app } from '../stores/app';

    onMount(async () => {
        if (window.__TAURI__) {
            const { listen } = await import('@tauri-apps/api/event');
            
            // Listen for sidecar errors emitted from Rust
            const unlisten = await listen<string>('backend-error', (event) => {
                console.error('[Sidecar Error]:', event.payload);
                app.setError(`Backend Error: ${event.payload}`, true);
            });

            return () => {
                unlisten();
            };
        }
    });

    $: status = $connectionState.status;
    $: activeClient = $connectionState.activeClient;
    $: lastError = $connectionState.lastError;

    function getStatusColor(s: string) {
        switch (s) {
            case 'connected': return 'bg-green-500';
            case 'connecting': return 'bg-yellow-500 animate-pulse';
            case 'error': return 'bg-red-500';
            default: return 'bg-gray-500';
        }
    }
</script>

<div class="fixed bottom-4 right-4 flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-800/80 backdrop-blur-md border border-gray-700 text-xs font-medium text-white shadow-lg pointer-events-none transition-all duration-300">
    <div class="w-2 h-2 rounded-full {getStatusColor(status)}"></div>
    <span>
        {#if status === 'connected'}
            {activeClient} Connected
        {:else if status === 'connecting'}
            Connecting to {activeClient || 'Backend'}...
        {:else if status === 'error'}
            Connection Error
        {:else}
            Disconnected
        {/if}
    </span>
</div>

{#if lastError && status === 'error'}
    <div class="fixed bottom-14 right-4 max-w-sm p-3 rounded-lg bg-red-900/90 border border-red-700 text-red-100 text-xs shadow-xl animate-bounce-subtle">
        <p class="font-bold mb-1">Backend Connection Failed</p>
        <p class="opacity-90">{lastError}</p>
    </div>
{/if}

<style>
    @keyframes bounce-subtle {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-3px); }
    }
    .animate-bounce-subtle {
        animation: bounce-subtle 3s ease-in-out infinite;
    }
</style>
