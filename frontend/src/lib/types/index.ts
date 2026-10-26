export interface HistoryItem {
  id: number;
  timestamp: string;
  original: string;
  refined: string;
  model: string;
  profileKey: string;
  characters: number;
}

export interface ApiStatus {
  operational_tier_name?: string;
}

export interface VisualPromptRequest {
  subject: string;
  text_content: string;
  environment: string;
  lighting: string;
  camera: string;
  render_style: string;
  model_id: string;
}

export interface Preset {
  id: string;
  name: string;
  values: Partial<VisualPromptRequest>;
}

export interface VisualTargets {
  [key: string]: {
    name: string;
    presets: Preset[];
  };
}
