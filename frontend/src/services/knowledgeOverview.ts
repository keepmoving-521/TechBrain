import { request } from "@/utils/request";

export interface OverviewStatistics {
  document_count: number;
  published_document_count: number;
  draft_document_count: number;
  category_count: number;
  tag_count: number;
}

export interface RecentDocument {
  id: number;
  document_id: string;
  title: string;
  summary: string | null;
  category_id: number;
  category: string;
  tags: string[];
  status: string;
  updated_at: string;
}

export interface PopularCategory {
  id: number;
  name: string;
  path: string;
  document_count: number;
}

export interface PopularTag {
  id: number;
  name: string;
  usage_count: number;
}

export interface KnowledgeOverview {
  is_empty: boolean;
  statistics: OverviewStatistics;
  recent_documents: RecentDocument[];
  popular_categories: PopularCategory[];
  popular_tags: PopularTag[];
}

export function getKnowledgeOverview(): Promise<KnowledgeOverview> {
  return request.get<KnowledgeOverview>("/knowledge/overview");
}
