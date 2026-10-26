<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';

  type Profile = {
    key: string;
    name: string;
    description: string;
  };

  let profiles: Profile[] = [];
  let selectedProfileKey: string = '';
  let error: string | null = null;
  export let id: string = '';

  const dispatch = createEventDispatcher();

  onMount(async () => {
    try {
      const { backendFetch } = await import('$lib/services/backendUrl');
      const res = await backendFetch('/profiles');
      if (!res.ok) {
        throw new Error(`Failed to fetch profiles: ${res.statusText}`);
      }
      const data = await res.json();
      profiles = data.profiles || [];
    } catch (e: any) {
      error = e.message;
      console.error("Error fetching profiles:", e);
    }
  });

  function handleChange(event: Event) {
    const target = event.target as HTMLSelectElement;
    selectedProfileKey = target.value;
    dispatch('profileSelected', { key: selectedProfileKey });
  }
</script>

<div class="profile-selector-container">
  {#if error}
    <div class="error-message">
      <p>Could not load profiles: {error}</p>
      <p>Is the backend running?</p>
    </div>
  {:else if profiles.length > 0}
    <select 
      {id}
      class="profile-select" 
      bind:value={selectedProfileKey} 
      on:change={handleChange}
      aria-label="Select a persona profile"
    >
      <option disabled value="">-- Select a Persona --</option>
      {#each profiles as profile (profile.key)}
        <option value={profile.key}>{profile.name}</option>
      {/each}
    </select>
  {:else}
    <p>Loading profiles...</p>
  {/if}
</div>

<style>
  .profile-selector-container {
    width: 100%;
    margin-bottom: 1rem;
  }

  .profile-select {
    width: 100%;
    padding: 0.75rem;
    border-radius: 0.375rem;
    border: 1px solid #4a5568;
    background-color: #2d3748;
    color: #e2e8f0;
    font-size: 1rem;
    cursor: pointer;
  }

  .profile-select:focus {
    outline: none;
    border-color: #4299e1;
    box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.5);
  }

  .error-message {
    padding: 1rem;
    border-radius: 0.375rem;
    background-color: #4a2222;
    border: 1px solid #c53030;
    color: #fed7d7;
  }
</style>
