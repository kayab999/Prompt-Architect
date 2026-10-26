/**
 * Enhanced MCP / Gemini CLI unified adapter for Prompt Architect
 * --------------------------------------------------------------
 * • Auto-detection with priority routing
 * • Comprehensive error handling and retries
 * • Health checks and connection monitoring
 * • Type-safe throughout
 */

import { writable } from 'svelte/store';

// ========== STORES & TYPES ==========

export interface GenerationOptions {
  temperature?: number;
  top_p?: number;
  max_output_tokens?: number;
  intent?: 'general' | 'creative' | 'technical' | 'concise' | 'detailed' | 'professional';
  [key: string]: any;
}

export interface MCPClient {
  name: string;
  connect(endpoint?: string): Promise<void>;
  listModels(): Promise<string[]>;
  sendPrompt(model: string, prompt: string, options?: GenerationOptions): Promise<string>;
  fineTune?(datasetPath: string, baseModel: string, config?: object): Promise<string>;
  healthCheck(): Promise<boolean>;
  disconnect(): Promise<void>;
}

export interface AdapterConfig {
  geminiCLIEndpoint?: string;
  mcpEndpoint?: string;
  httpBackendEndpoint?: string;
  mcpToken?: string;
  retryAttempts?: number;
  timeoutMs?: number;
  /** When true, only connect to the local FastAPI sidecar (desktop default). */
  preferHttpOnly?: boolean;
}

export const connectionState = writable<{
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  activeClient?: string;
  lastError?: string;
  detectedBackends: string[];
}>(
  {
    status: 'disconnected',
    detectedBackends: []
  }
);

// ========== ENHANCED UTILITIES ==========

async function robustFetch(url: string, opts: RequestInit & { timeout?: number } = {}) {
  const timeout = opts.timeout || 5000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...opts,
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

function withRetry<T>(
  operation: () => Promise<T>,
  maxRetries: number = 2,
  delay: number = 1000
): Promise<T> {
  return new Promise((resolve, reject) => {
    const attempt = (retryCount: number) => {
      operation()
        .then(resolve)
        .catch((error) => {
          if (retryCount < maxRetries) {
            console.warn(`Retry ${retryCount + 1}/${maxRetries} after error:`, error.message);
            setTimeout(() => attempt(retryCount + 1), delay * (retryCount + 1));
          } else {
            reject(error);
          }
        });
    };
    attempt(0);
  });
}

// ========== ENHANCED GEMINI CLI CLIENT ==========

export class GeminiCLI implements MCPClient {
  public name = 'Gemini CLI';
  private base: string;

  constructor(endpoint: string = 'http://localhost:5000') {
    this.base = endpoint;
  }

  async connect() {
    connectionState.update(state => ({
      ...state,
      status: 'connecting',
      activeClient: this.name
    }));

    try {
      await withRetry(() => robustFetch(`${this.base}/status`, { timeout: 3000 }));
      
      connectionState.update(state => ({
        ...state,
        status: 'connected',
        lastError: undefined
      }));
    } catch (error: any) {
      connectionState.update(state => ({
        ...state,
        status: 'error',
        lastError: `Gemini CLI: ${error.message}`
      }));
      throw error;
    }
  }

  async listModels(): Promise<string[]> {
    const data = await withRetry(() => 
      robustFetch(`${this.base}/models`, { timeout: 4000 })
    );
    return data.models || data.available_models || [];
  }

  async sendPrompt(model: string, prompt: string, options: GenerationOptions = {}): Promise<string> {
    const body = JSON.stringify({ 
      model, 
      prompt, 
      options: {
        temperature: options.temperature || 0.7,
        max_output_tokens: options.max_output_tokens || 1000,
        ...options
      }
    });

    const data = await withRetry(() =>
      robustFetch(`${this.base}/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        timeout: 30000 
      })
    );

    return data.refined || data.output || data.result || '';
  }

  async healthCheck(): Promise<boolean> {
    try {
      await robustFetch(`${this.base}/health`, { timeout: 2000 });
      return true;
    } catch {
      return false;
    }
  }

  async disconnect() {
    connectionState.update(state => ({
      ...state,
      status: 'disconnected',
      activeClient: undefined
    }));
  }
}

// ========== ENHANCED MCP CONNECTOR ==========

export class MCPConnector implements MCPClient {
  public name = 'MCP Server';
  private endpoint: string = '';
  private token?: string;

  constructor(endpoint: string = 'http://localhost:8080/mcp', token?: string) {
    this.endpoint = endpoint;
    this.token = token;
  }

  async connect() {
    connectionState.update(state => ({
      ...state,
      status: 'connecting',
      activeClient: this.name
    }));

    try {
      await withRetry(() => 
        robustFetch(`${this.endpoint}/health`, {
          headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
          timeout: 3000
        })
      );

      connectionState.update(state => ({
        ...state,
        status: 'connected',
        lastError: undefined
      }));
    } catch (error: any) {
      connectionState.update(state => ({
        ...state,
        status: 'error',
        lastError: `MCP Server: ${error.message}`
      }));
      throw error;
    }
  }

  async listModels(): Promise<string[]> {
    const data = await withRetry(() =>
      robustFetch(`${this.endpoint}/models`, {
        headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
        timeout: 4000
      })
    );
    return data.models || data.available_models || [];
  }

  async sendPrompt(model: string, prompt: string, options: GenerationOptions = {}): Promise<string> {
    const body = JSON.stringify({ 
      model, 
      prompt, 
      ...options 
    });

    const data = await withRetry(() =>
      robustFetch(`${this.endpoint}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.token ? { Authorization: `Bearer ${this.token}` } : {})
        },
        body,
        timeout: 30000
      })
    );

    return data.output || data.result || data.content || '';
  }

  async healthCheck(): Promise<boolean> {
    try {
      await robustFetch(`${this.endpoint}/health`, {
        headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
        timeout: 2000
      });
      return true;
    } catch {
      return false;
    }
  }

  async disconnect() {
    connectionState.update(state => ({
      ...state,
      status: 'disconnected',
      activeClient: undefined
    }));
  }
}

// ========== ENHANCED HTTP BACKEND ==========

export class HttpBackend implements MCPClient {
  public name = 'HTTP Backend';
  private base: string;

  constructor(endpoint?: string) {
    this.base = endpoint || 'http://127.0.0.1:8000';
  }

  async connect() {
    connectionState.update(state => ({
      ...state,
      status: 'connecting',
      activeClient: this.name
    }));

    try {
      await withRetry(() => robustFetch(`${this.base}/status`, { timeout: 3000 }));

      connectionState.update(state => ({
        ...state,
        status: 'connected',
        lastError: undefined
      }));
    } catch (error: any) {
      connectionState.update(state => ({
        ...state,
        status: 'error',
        lastError: `HTTP Backend: ${error.message}`
      }));
      throw error;
    }
  }

  async listModels(): Promise<string[]> {
    const data = await withRetry(() => robustFetch(`${this.base}/models`, { timeout: 4000 }));
    return data.models || data.available_models || [];
  }

  async sendPrompt(model: string, prompt: string, options: GenerationOptions = {}): Promise<string> {
    // Prefer the primary generate endpoint used by the Architect UI
    const generateBody = JSON.stringify({
      user_input: prompt,
      profile_key: options.intent || options.profile_key || 'technical',
      model,
    });

    try {
      const data = await withRetry(() =>
        robustFetch(`${this.base}/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: generateBody,
          timeout: 60000
        })
      );
      if (data.response) return data.response;
    } catch {
      // fall through to /optimize
    }

    const body = JSON.stringify({
      prompt,
      intent: options.intent || 'general',
      target_model: options.target_model || model,
      refiner_model: model,
    });

    const data = await withRetry(() =>
      robustFetch(`${this.base}/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        timeout: 60000
      })
    );

    return data.optimized_prompt || data.refined_prompt || data.output || data.response || '';
  }

  async healthCheck(): Promise<boolean> {
    try {
      await robustFetch(`${this.base}/health`, { timeout: 2000 });
      return true;
    } catch {
      return false;
    }
  }

  async disconnect() {
    connectionState.update(state => ({
      ...state,
      status: 'disconnected',
      activeClient: undefined
    }));
  }
}

// ========== FACTORY WITH HEALTH MONITORING ==========

export async function createMCPClient(config: AdapterConfig = {}): Promise<MCPClient> {
  const {
    geminiCLIEndpoint = 'http://localhost:5000',
    mcpEndpoint = 'http://localhost:8080/mcp',
    httpBackendEndpoint = 'http://127.0.0.1:8000',
    mcpToken,
    preferHttpOnly = true,
  } = config;

  console.log(`[MCPAdapter] Configuring with HTTP Backend: ${httpBackendEndpoint}`);

  const clients = preferHttpOnly
    ? [
        {
          name: 'HTTP Backend',
          factory: () => new HttpBackend(httpBackendEndpoint),
          priority: 0,
        },
      ]
    : [
        {
          name: 'HTTP Backend',
          factory: () => new HttpBackend(httpBackendEndpoint),
          priority: 0,
        },
        {
          name: 'Gemini CLI',
          factory: () => new GeminiCLI(geminiCLIEndpoint),
          priority: 1,
        },
        {
          name: 'MCP Server',
          factory: () => new MCPConnector(mcpEndpoint, mcpToken),
          priority: 2,
        },
      ];

  const detectedBackends: string[] = [];
  let lastError: Error | null = null;

  for (const clientInfo of clients) {
    try {
      console.log(`[MCPAdapter] Attempting connection to ${clientInfo.name}...`);

      const client = clientInfo.factory();
      await client.connect();

      detectedBackends.push(client.name);

      connectionState.update((state) => ({
        ...state,
        detectedBackends,
        lastError: undefined,
      }));

      console.log(`[MCPAdapter] Connected to ${clientInfo.name}`);
      return client;
    } catch (error: any) {
      console.warn(`[MCPAdapter] ${clientInfo.name} failed:`, error.message);
      lastError = error as Error;
      detectedBackends.push(`${clientInfo.name} (failed)`);
    }
  }

  connectionState.update((state) => ({
    ...state,
    status: 'error',
    lastError: lastError?.message || 'All backend connections failed',
    detectedBackends,
  }));

  throw new Error(
    `No available backends. Tried: ${clients.map((c) => c.name).join(', ')}`
  );
}

// ========== CONNECTION MANAGER ==========

class ConnectionManager {
  private client: MCPClient | null = null;
  private healthCheckInterval: number | null = null;

  async initialize(config?: AdapterConfig): Promise<MCPClient> {
    this.client = await createMCPClient(config);
    this.startHealthChecks();
    return this.client;
  }

  private startHealthChecks() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }

    this.healthCheckInterval = window.setInterval(async () => {
      if (this.client) {
        const isHealthy = await this.client.healthCheck().catch(() => false);
        
        if (!isHealthy) {
          console.warn('[MCPAdapter] Health check failed, reconnecting...');
          connectionState.update(state => ({ ...state, status: 'error' }));
          
          try {
            await this.client.connect();
            connectionState.update(state => ({ ...state, status: 'connected' }));
          } catch {
            // Reconnection will be handled by the next operation
          }
        }
      }
    }, 30000); 
  }

  getClient(): MCPClient {
    if (!this.client) {
      throw new Error('MCP client not initialized. Call initialize() first.');
    }
    return this.client;
  }

  async reconnect(config?: AdapterConfig): Promise<MCPClient> {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }
    
    if (this.client) {
      await this.client.disconnect().catch(() => {});
    }
    
    return this.initialize(config);
  }

  disconnect() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
    
    if (this.client) {
      this.client.disconnect().catch(() => {});
      this.client = null;
    }
  }
}

export const connectionManager = new ConnectionManager();

export async function getMCPClient(config?: AdapterConfig): Promise<MCPClient> {
  return connectionManager.initialize(config);
}
