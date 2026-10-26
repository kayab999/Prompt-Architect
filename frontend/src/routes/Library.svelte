<script lang="ts">
  import { onMount } from "svelte";
  import { writable } from "svelte/store";
  import { activeTemplate, templateVariables } from "$lib/stores/prompt";
  import type { PromptTemplate } from "$lib/stores/prompt";

  const library = writable<PromptTemplate[]>([]);

  async function loadLibrary() {
    try {
      const { backendFetch } = await import('$lib/services/backendUrl');
      const res = await backendFetch('/library');
      const data = await res.json();
      library.set(data.library || []);
    } catch (err) {
      console.error("Error loading library:", err);
    }
  }

  function loadPrompt(item: PromptTemplate) {
    // Resetear variables antes de cargar el nuevo template
    templateVariables.set({});
    activeTemplate.set(item);
  }

  onMount(loadLibrary);
</script>

<div class="library-container">
  <h2 class="section-title">Prompt Library</h2>
  <div class="library-grid">
    {#each $library as item}
      <button class="library-item" on:click={() => loadPrompt(item)}>
        <div class="item-header">
          <span class="category-badge">{item.category || 'General'}</span>
          <span class="version-tag">v{item.version ?? 1}</span>
        </div>
        <p class="template-preview">{item.template?.substring(0, 100) ?? 'Untitled'}...</p>
        <div class="item-footer">
          <span class="variables-count">{item.variables?.length ?? 0} variables</span>
          <span class="date"
            >{item.timestamp
              ? new Date(item.timestamp).toLocaleDateString()
              : "N/A"}</span
          >
        </div>
      </button>
    {/each}
  </div>
</div>

<style lang="postcss">
  .library-container {
    padding: 20px;
  }
  .section-title {
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 1.5rem;
    color: #fff;
  }
  .library-grid {
    display: grid;
    gap: 16px;
  }
  .library-item {
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 16px;
    text-align: left;
    transition: all 0.2s;
    cursor: pointer;
    width: 100%;
  }
  .library-item:hover {
    border-color: #6366f1;
    background: #252525;
    transform: translateY(-2px);
  }
  .item-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  .category-badge {
    font-size: 0.7rem;
    background: #312e81;
    color: #c7d2fe;
    padding: 2px 8px;
    border-radius: 99px;
    text-transform: uppercase;
    font-weight: 600;
  }
  .version-tag {
    font-size: 0.7rem;
    color: #666;
  }
  .template-preview {
    font-size: 0.85rem;
    color: #aaa;
    line-height: 1.4;
    margin: 0 0 12px 0;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .item-footer {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #555;
  }
  .variables-count {
    color: #818cf8;
  }
</style>
