export type JobKind = "import" | "report" | "run" | "chat";
export type JobStatus = "queued" | "running" | "completed" | "failed";
export type AppMode = "chat" | "cli" | "api" | "reports" | "settings";

export interface ReportPaths {
  html_path: string;
  markdown_path: string;
  html_url?: string | null;
  markdown_url?: string | null;
}

export interface StartupDefaults {
  import_input?: string | null;
  schedule_input?: string | null;
  recreate_index?: boolean;
  start_date?: string | null;
  end_date?: string | null;
  output?: string | null;
  api_url?: string;
  api_port?: number;
  web_url?: string;
  web_port?: number;
}

export interface StartupConfig {
  status: string;
  project_dir: string;
  es_index: string;
  outputs_dir: string;
  uploads_dir: string;
  llm_enabled: boolean;
  llm_report_enabled: boolean;
  defaults: StartupDefaults;
}

export interface HealthResponse {
  status: string;
  es_index: string;
}

export interface UploadResponse {
  count: number;
  input_path: string;
  files: string[];
}

export interface ImportPayload {
  input: string;
  recreate_index: boolean;
}

export interface ReportPayload {
  output?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  schedule_input?: string | null;
}

export interface RunPayload extends ReportPayload {
  input: string;
  recreate_index: boolean;
}

export interface ChatPayload {
  message: string;
  session_id?: string | null;
  schedule_input?: string | null;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  report_paths?: ReportPaths;
}

export interface JobRecord {
  job_id: string;
  kind: JobKind;
  status: JobStatus;
  result?: Record<string, unknown> | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobEvent {
  event: string;
  data: Record<string, unknown>;
  receivedAt: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
  pending?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  sessionId: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface ReportItem extends ReportPaths {
  id: string;
  title: string;
  source: string;
  createdAt: string;
}
