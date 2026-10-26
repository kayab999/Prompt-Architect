import { writable } from 'svelte/store';

function createAppStore() {
  const { subscribe, update } = writable({
    loading: false,
    errorMessage: '',
    successMessage: '',
    isErrorPersistent: false,
  });

  function setError(message: string, persistent = true) {
    update(store => ({ ...store, errorMessage: message, isErrorPersistent: persistent, successMessage: '' }));
  }

  function setSuccess(message: string, duration = 3000) {
    update(store => ({ ...store, successMessage: message, errorMessage: '', isErrorPersistent: false }));
    setTimeout(() => {
      update(store => {
        if (store.successMessage === message) {
          return { ...store, successMessage: '' };
        }
        return store;
      });
    }, duration);
  }

  function clearMessages() {
    update(store => ({ ...store, errorMessage: '', successMessage: '', isErrorPersistent: false }));
  }
  
  function setLoading(isLoading: boolean) {
    update(store => ({ ...store, loading: isLoading }));
  }

  return {
    subscribe,
    setError,
    setSuccess,
    clearMessages,
    setLoading,
  };
}

export const app = createAppStore();