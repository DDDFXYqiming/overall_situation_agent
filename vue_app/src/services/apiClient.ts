import type {
  ChatPayload,
  ChatResponse,
  HealthResponse,
  ImportPayload,
  JobKind,
  JobRecord,
  ReportPayload,
  ReportPaths,
  RunPayload,
  StartupConfig,
  UploadResponse
} from "./types";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers
    }
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = payload?.detail || response.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload as T;
}

export const apiClient = {
  startup: () => requestJson<StartupConfig>("/api/web/startup"),
  health: () => requestJson<HealthResponse>("/health"),

  upload(files: File[]) {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return requestJson<UploadResponse>("/api/uploads", { method: "POST", body: form });
  },

  importData(payload: ImportPayload) {
    return requestJson<{ count: number; imported: boolean; message: string }>("/api/import", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  report(payload: ReportPayload) {
    return requestJson<ReportPaths>("/api/report", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  run(payload: RunPayload) {
    return requestJson<ReportPaths>("/api/run", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  chat(payload: ChatPayload) {
    return requestJson<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  createJob(kind: JobKind, payload: ImportPayload | ReportPayload | RunPayload | ChatPayload) {
    return requestJson<JobRecord>(`/api/jobs/${kind}`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  getJob(jobId: string) {
    return requestJson<JobRecord>(`/api/jobs/${jobId}`);
  }
};
