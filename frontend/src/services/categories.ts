import { request } from "@/utils/request";

export interface CategoryTreeNode {
  id: number;
  parent_id: number | null;
  name: string;
  slug: string;
  path: string;
  sort_order: number;
  status: string;
  direct_document_count: number;
  document_count: number;
  children: CategoryTreeNode[];
}

interface CategoryTreeResponse {
  items: CategoryTreeNode[];
}

export async function getCategoryTree(): Promise<CategoryTreeNode[]> {
  const response = await request.get<CategoryTreeResponse>("/categories/tree");
  return response.items;
}
