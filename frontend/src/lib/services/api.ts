import { connectionManager, connectionState } from "./mcpAdapter";
import {
  resolveBackendBaseUrl,
  setBackendBaseUrl,
} from "./backendUrl";

let clientInitialized = false;

export { connectionState };

export async function initializeBackend() {
  if (clientInitialized) return;

  try {
    const httpBackendEndpoint = await resolveBackendBaseUrl(true);
    setBackendBaseUrl(httpBackendEndpoint);
    console.log(`[API] Backend base URL: ${httpBackendEndpoint}`);

    const config = {
      geminiCLIEndpoint: import.meta.env.VITE_GEMINI_CLI_ENDPOINT as
        | string
        | undefined,
      mcpEndpoint: import.meta.env.VITE_MCP_ENDPOINT as string | undefined,
      httpBackendEndpoint,
      mcpToken: import.meta.env.VITE_MCP_TOKEN as string | undefined,
      // In Tauri / local desktop, only the HTTP sidecar matters
      preferHttpOnly:
        Boolean((window as any).__TAURI__) ||
        import.meta.env.VITE_PREFER_HTTP === "1",
    };

    await connectionManager.initialize(config);
    clientInitialized = true;
  } catch (error) {
    console.error("Failed to initialize backend:", error);
    throw error;
  }
}

export async function reconnectBackend() {
  clientInitialized = false;
  connectionManager.disconnect();
  await initializeBackend();
}
