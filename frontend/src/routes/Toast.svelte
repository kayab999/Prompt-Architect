<script>
  import { createEventDispatcher } from 'svelte';

  export let message = '';
  const dispatch = createEventDispatcher();

  function close() {
    dispatch('close');
  }
</script>

<div class="toast" role="alert" aria-live="assertive">
  <p>{message}</p>
  <button on:click={close} aria-label="Close">&times;</button>
</div>

<style>
  .toast {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background-color: #ff4d4d;
    color: white;
    padding: 1rem;
    border-radius: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 101;
  }
  .toast p {
    margin: 0;
    margin-right: 1rem;
  }
  .toast button {
    background: none;
    border: none;
    color: white;
    font-size: 1.5rem;
    cursor: pointer;
  }
</style>
