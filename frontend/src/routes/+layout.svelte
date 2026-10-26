<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { initializeBackend } from '$lib/services/api';
  import BackendStatus from '$lib/components/BackendStatus.svelte';

  onMount(async () => {
    try {
      // Backend is now managed by Rust setup().
      await initializeBackend();
      console.log('Backend connection initialized.');
    } catch (error) {
      console.error('Failed to initialize backend:', error);
    }
  });
</script>

<slot />
<BackendStatus />
