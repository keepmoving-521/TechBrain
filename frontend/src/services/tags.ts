import { request } from "@/utils/request";

import type { Pagination } from "@/services/documents";

export type TagSort = "name" | "-name" | "usage_count" | "-usage_count";

export interface KnowledgeTag {
  id: number;
  name: string;
  normalized_name: string;
  status: string;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

interface TagPage {
  items: KnowledgeTag[];
  pagination: Pagination;
}

export function getTags(params: {
  page: number;
  page_size: number;
  sort: TagSort;
}): Promise<TagPage> {
  return request.get<TagPage>("/tags", { params });
}

export function getTag(tagId: number): Promise<KnowledgeTag> {
  return request.get<KnowledgeTag>(`/tags/${tagId}`);
}
