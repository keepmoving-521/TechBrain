import { request } from "@/utils/request";

export interface KnowledgeSyncFailure {
  id: number | null;
  path: string;
  stage: string;
  code: string;
  message: string;
  field: string | null;
  line: number | null;
  column: number | null;
}

export interface KnowledgeSyncTask {
  id: number;
  status: "success" | "partial_success" | "failed" | string;
  started_at: string;
  finished_at: string;
  scanned_count: number;
  success_count: number;
  failed_count: number;
  created_count: number;
  updated_count: number;
  restored_count: number;
  unchanged_count: number;
  deleted_count: number;
  failures: KnowledgeSyncFailure[];
}

interface KnowledgeSyncTaskListResponse {
  items: KnowledgeSyncTask[];
}

export function triggerKnowledgeSync(): Promise<KnowledgeSyncTask> {
  return request.post<KnowledgeSyncTask>("/knowledge/sync");
}

export async function listKnowledgeSyncTasks(): Promise<KnowledgeSyncTask[]> {
  const response = await request.get<KnowledgeSyncTaskListResponse>("/knowledge/sync/tasks");
  return response.items;
}

export function getKnowledgeSyncTask(taskId: number): Promise<KnowledgeSyncTask> {
  return request.get<KnowledgeSyncTask>(`/knowledge/sync/tasks/${taskId}`);
}
