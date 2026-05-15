import type { JobEvent } from "./types";

function parseEventData(raw: string): Record<string, unknown> {
  if (!raw) {
    return {};
  }
  try {
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null ? parsed : { message: raw };
  } catch {
    return { message: raw };
  }
}

export function subscribeJobEvents(
  jobId: string,
  onEvent: (event: JobEvent) => void,
  onDone: () => void,
  onError: (message: string) => void
) {
  const source = new EventSource(`/api/jobs/${jobId}/events`);
  const eventNames = ["started", "stage", "completed", "failed", "running"];

  eventNames.forEach((eventName) => {
    source.addEventListener(eventName, (event) => {
      onEvent({
        event: eventName,
        data: parseEventData((event as MessageEvent).data),
        receivedAt: new Date().toLocaleTimeString()
      });
      if (eventName === "completed" || eventName === "failed") {
        source.close();
        onDone();
      }
    });
  });

  source.onerror = () => {
    source.close();
    onError("任务事件流已断开");
  };

  return () => source.close();
}
