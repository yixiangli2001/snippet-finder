export interface Snippet {
  id: string;
  owner_id: string | null;
  owner_username: string | null;
  title: string;
  language: string;
  code: string;
  description: string;
  tags: string[];
  is_public: boolean;
  times_copied: number;
  created_at: string;
  updated_at: string;
}
