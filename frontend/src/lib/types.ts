export interface VisualPromptRequest {
  subject: string;
  text_content?: string;
  environment?: string;
  lighting?: string;
  camera?: string;
  render_style?: string;
  model_id: string;
}

export interface Preset {
  id: string;
  name: string;
  values: Partial<VisualPromptRequest>;
}

export interface ModelConfig {
  name: string;
  version: string;
  presets: Preset[];
}

export interface VisualTargets {
  [key: string]: ModelConfig;
}

/** Host metrics from GET /vital-signs */
export interface SystemVitals {
  cpu_percent: number;
  ram_percent: number;
  temperature: number | null;
  gpu_load: number | null;
  tier_id: number;
  tier_name: string;
  ollama_online?: boolean;
  groq_configured?: boolean;
}

export interface GenerateResponse {
  response: string;
  success: boolean;
  reason?: string | null;
  iterations?: number;
  integrity_signature?: Record<string, unknown> | null;
}
