export interface LocalizedText {
  en: string;
  es: string;
  [key: string]: string;
}

export interface FieldOption {
  value: string;
  label: LocalizedText;
}

export interface FunnelField {
  key: string;
  type: 'text' | 'select' | 'tel' | 'email' | 'textarea';
  required: boolean;
  label: LocalizedText;
  options?: FieldOption[];
}

export interface FunnelStep {
  id: string;
  title: LocalizedText;
  fields: FunnelField[];
}

export interface FunnelSchema {
  slug: string;
  languages: string[];
  steps: FunnelStep[];
}

export interface FunnelResponse {
  slug: string;
  name: string;
  schema_json: FunnelSchema;
  branding: Record<string, unknown>;
  languages: string[];
}

export type Language = 'en' | 'es';
