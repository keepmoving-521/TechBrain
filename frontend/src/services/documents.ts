import { request } from "@/utils/request";

export type DocumentSort = "updated_at" | "-updated_at";

export interface DocumentListItem {
  id: number;
  document_id: string;
  title: string;
  summary: string | null;
  category_id: number;
  category: string;
  tags: string[];
  status: string;
  visibility: string;
  language: string;
  created_at: string;
  updated_at: string;
  relative_path: string;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_previous: boolean;
  has_next: boolean;
}

export interface DocumentPage {
  items: DocumentListItem[];
  pagination: Pagination;
}

export interface DocumentListParams {
  page: number;
  page_size: number;
  category_id?: number;
  tag_id?: number;
  status?: string;
  sort: DocumentSort;
}

export function getDocuments(params: DocumentListParams): Promise<DocumentPage> {
  return request.get<DocumentPage>("/documents", { params });
}
