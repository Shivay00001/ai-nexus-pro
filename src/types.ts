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
  status: 'pending' | 'running' | 'completed' | 'failed';
  leads_found: number;
  error_message: string;
  created_at: string;
  completed_at: string | null;
};

export type ViewType = 'dashboard' | 'leads' | 'scrape' | 'history' | 'categories';

export type Toast = {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
};

export type ScrapingResult = {
  emails: string[];
  phones: string[];
  companyName: string;
  description: string;
};
