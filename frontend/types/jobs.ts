/**
 * Types for the Job Discovery feature
 * Matches backend response models from GET /jobs endpoint
 */

export type JobBoardProvider = "ashby" | "lever" | "greenhouse";

export interface DiscoveredJob {
  id: string;
  board_id: string;
  provider: JobBoardProvider;
  company_name: string | null;
  external_id: string;
  title: string;
  location: string | null;
  is_remote: boolean;
  department: string | null;
  team: string | null;
  apply_url: string;
  description: string | null;
  posted_at: string | null;
}

export interface JobsListResponse {
  jobs: DiscoveredJob[];
  total_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface JobFilters {
  keyword: string;
  provider: JobBoardProvider | "all";
  remote: "any" | "remote" | "onsite";
  location: string;
}
