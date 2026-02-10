import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export type Category = {
  id: string;
  name: string;
  description: string;
  color: string;
  created_at: string;
};

export type Lead = {
  id: string;
  category_id: string | null;
  company_name: string;
  contact_name: string;
  email: string;
  phone: string;
  website: string;
  description: string;
  source_url: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ScrapingJob = {
  id: string;
  url: string;
  status: string;
  leads_found: number;
  error_message: string;
  created_at: string;
  completed_at: string | null;
};
