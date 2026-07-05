export interface RadarPoint {
  metric: string;
  value: number;
  reason?: string;
}

export interface SourcePreview {
  id: string;
  company: string;
  source_filename: string;
  stored_path: string;
  parsed_path: string;
  score: number;
  preview: string;
}

export interface AnalysisResult {
  report: string;
  radar: RadarPoint[];
  company_radars?: Record<string, RadarPoint[]>;
  matrix: {
    rows?: Array<Record<string, unknown>>;
  };
  sentiment?: Record<string, unknown>;
  sources: SourcePreview[];
}

export interface ReportResponse {
  session_id: string;
  report: string;
  radar: RadarPoint[];
  company_radars?: Record<string, RadarPoint[]>;
  matrix: {
    rows?: Array<Record<string, unknown>>;
  };
  sentiment?: Record<string, unknown>;
  sources?: SourcePreview[];
}

export interface KnowledgeFile {
  filename: string;
  size: number;
  path: string;
}

export interface RegistryDocument {
  document_id: string;
  company?: string;
  category?: string;
  source_filename?: string;
  stored_path?: string;
  chunk_count?: number;
  classification?: {
    confidence?: number;
    reason?: string;
  };
}

export interface KnowledgeResponse {
  documents: KnowledgeFile[];
  parsed: KnowledgeFile[];
  registry: RegistryDocument[];
  postgres?: {
    documents: number;
    chunks: number;
  };
  chunks: Array<Record<string, unknown>>;
  chunk_count: number;
}
