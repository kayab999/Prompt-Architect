<script lang="ts">
    import { onMount } from "svelte";
    import SystemVitals from "./SystemVitals.svelte";
    import { app } from "$lib/stores/app";

    interface Preset {
        id: string;
        name: string;
        values: Record<string, string>;
    }

    interface ModelTarget {
        name: string;
        presets: Preset[];
    }

    let targets: Record<string, ModelTarget> = {};
    let selectedModel = "nano-banana-pro";
    let selectedPresetId = "";

    let formData: Record<string, string> = {
        subject: "",
        text_content: "",
        environment: "",
        lighting: "",
        camera: "",
        render_style: "",
        model_id: selectedModel,
    };

    $: formData.model_id = selectedModel;

    let compiledPrompt = "";
    let isLoading = false;

    onMount(async () => {
        try {
            const { backendFetch } = await import("$lib/services/backendUrl");
            const response = await backendFetch("/presets");
            const data = await response.json();
            targets = {
                [data.model_id]: {
                    name: data.model_id,
                    presets: data.presets || []
                }
            };
        } catch (error) {
            console.error("Error fetching presets:", error);
        }
    });

    let presets: Preset[] = [];
    $: presets = targets[selectedModel]?.presets || [];

    function applyPreset() {
        if (!selectedPresetId) {
            formData = {
                subject: formData.subject,
                text_content: "",
                environment: "",
                lighting: "",
                camera: "",
                render_style: "",
                model_id: selectedModel
            };
            return;
        }

        const preset = presets.find((p: Preset) => p.id === selectedPresetId);
        if (preset) {
            formData = {
                subject: formData.subject,
                text_content: preset.values.text_content || "",
                environment: preset.values.environment || "",
                lighting: preset.values.lighting || "",
                camera: preset.values.camera || "",
                render_style: preset.values.render_style || "",
                model_id: selectedModel
            };
        }
    }

    async function compile() {
        if (!formData.subject) return;
        isLoading = true;
        try {
            const { backendFetch } = await import("$lib/services/backendUrl");
            const response = await backendFetch("/compile-visual", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(formData),
            });
            const result = await response.json();
            compiledPrompt = result.compiled_prompt;
            app.setSuccess("Visual prompt compiled!");
        } catch (error) {
            app.setError("Compilation failed.", false);
        } finally {
            isLoading = false;
        }
    }

    function copyToClipboard() {
        navigator.clipboard.writeText(compiledPrompt);
        app.setSuccess("Copied to clipboard!");
    }
</script>

<div class="premium-panel max-w-4xl mx-auto w-full p-8 space-y-8 transition-all duration-500">
    <div class="flex justify-between items-center border-b border-slate-800 pb-6">
        <div>
            <h2 class="text-xl font-black text-white tracking-tight flex items-center gap-2">
                <span class="text-indigo-500">📸</span>
                VISUAL ARCHITECT
            </h2>
            <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">Multi-modal Prompt Compiler</p>
        </div>
        <SystemVitals />
    </div>

    <div class="grid md:grid-cols-2 gap-6">
        <div class="space-y-2">
            <label for="engine-select" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Target Engine</label>
            <select id="engine-select" bind:value={selectedModel} class="w-full premium-input bg-[#1c2127] border-slate-800 text-sm">
                {#each Object.keys(targets) as modelId}
                    <option value={modelId}>{targets[modelId].name}</option>
                {/each}
            </select>
        </div>

        <div class="space-y-2">
            <label for="preset-select" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Style Preset</label>
            <select id="preset-select" bind:value={selectedPresetId} on:change={applyPreset} class="w-full premium-input bg-[#1c2127] border-slate-800 text-sm">
                <option value="">-- Manual Build --</option>
                {#each presets as preset}
                    <option value={preset.id}>{preset.name}</option>
                {/each}
            </select>
        </div>
    </div>

    <div class="space-y-6">
        <div class="space-y-2">
            <label for="subject-input" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Primary Subject</label>
            <textarea
                id="subject-input"
                bind:value={formData.subject}
                placeholder="Describe the physical subject and materials..."
                class="w-full premium-input bg-[#1c2127] border-slate-800 text-sm min-h-[100px] font-mono leading-relaxed"
            ></textarea>
        </div>

        <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
                <label for="text-content" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Embedded Text</label>
                <input id="text-content" type="text" bind:value={formData.text_content} placeholder="Any specific words..." class="w-full premium-input bg-[#1c2127] border-slate-800 text-xs" />
            </div>
            <div class="space-y-2">
                <label for="environment" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Environment</label>
                <input id="environment" type="text" bind:value={formData.environment} placeholder="Location, background..." class="w-full premium-input bg-[#1c2127] border-slate-800 text-xs" />
            </div>
            <div class="space-y-2">
                <label for="lighting" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Lighting</label>
                <input id="lighting" type="text" bind:value={formData.lighting} placeholder="Golden hour, cinematic..." class="w-full premium-input bg-[#1c2127] border-slate-800 text-xs" />
            </div>
            <div class="space-y-2">
                <label for="camera" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Camera / Lens</label>
                <input id="camera" type="text" bind:value={formData.camera} placeholder="85mm, wide angle..." class="w-full premium-input bg-[#1c2127] border-slate-800 text-xs" />
            </div>
            <div class="space-y-2">
                <label for="render_style" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Render / Art Style</label>
                <input id="render_style" type="text" bind:value={formData.render_style} placeholder="Unreal Engine 5, oil painting..." class="w-full premium-input bg-[#1c2127] border-slate-800 text-xs" />
            </div>
        </div>
    </div>

    <button
        class="w-full group relative flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-bold py-4 rounded-2xl transition-all shadow-2xl shadow-indigo-600/20 active:scale-95 overflow-hidden"
        on:click={compile}
        disabled={!formData.subject || isLoading}
    >
        {#if isLoading}
            <span class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <span>Compiling Matrix...</span>
        {:else}
            <span class="text-xl group-hover:scale-110 transition-transform">🚀</span>
            <span>Compile Visual Fragment</span>
        {/if}
    </button>

    {#if compiledPrompt}
        <div class="bg-black/40 rounded-2xl border border-slate-800/50 p-6 space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div class="flex justify-between items-center">
                <span class="text-[10px] font-black text-emerald-500 uppercase tracking-[0.2em]">Compilation Success</span>
                <button class="text-[10px] font-black text-slate-500 hover:text-white uppercase tracking-widest transition-colors" on:click={copyToClipboard}>
                    Copy to Clipboard
                </button>
            </div>
            <div class="text-sm font-mono text-emerald-400 leading-relaxed bg-slate-900/50 p-4 rounded-xl border border-emerald-500/10">
                {compiledPrompt}
            </div>
        </div>
    {/if}
</div>
