export interface Collection {
  id: string;
  owner_id: string | null;
  owner_username: string | null;
  name: string;
  description: string | null;
  snippet_ids: string[];
  is_public: boolean;
  created_at: string;
  updated_at: string;
}
