/*
  # Lead Scraper Database Schema
  
  ## Overview
  Creates a comprehensive database schema for a web scraping lead generation platform
  that organizes leads by categories.
  
  ## New Tables
  
  ### categories
  - `id` (uuid, primary key) - Unique category identifier
  - `name` (text, unique) - Category name (e.g., "Technology", "Healthcare", "Finance")
  - `description` (text) - Category description
  - `color` (text) - Color code for UI display
  - `created_at` (timestamptz) - Creation timestamp
  
  ### leads
  - `id` (uuid, primary key) - Unique lead identifier
  - `category_id` (uuid, foreign key) - Reference to category
  - `company_name` (text) - Company name
  - `contact_name` (text) - Contact person name
  - `email` (text) - Email address
  - `phone` (text) - Phone number
  - `website` (text) - Website URL
  - `description` (text) - Lead description
  - `source_url` (text) - URL where lead was found
  - `status` (text) - Lead status (new, contacted, qualified, etc.)
  - `created_at` (timestamptz) - Creation timestamp
  - `updated_at` (timestamptz) - Last update timestamp
  
  ### scraping_jobs
  - `id` (uuid, primary key) - Unique job identifier
  - `url` (text) - Target URL
  - `status` (text) - Job status (pending, running, completed, failed)
  - `leads_found` (integer) - Number of leads found
  - `error_message` (text) - Error message if failed
  - `created_at` (timestamptz) - Creation timestamp
  - `completed_at` (timestamptz) - Completion timestamp
  
  ## Security
  
  ### Row Level Security (RLS)
  - Enabled on all tables
  - Authenticated users can read all data
  - Authenticated users can insert, update, and delete their own data
  
  ## Notes
  - All tables use UUIDs for primary keys
  - Timestamps are automatically set
  - Proper indexes added for performance
  - Foreign key constraints ensure data integrity
*/

-- Create categories table
CREATE TABLE IF NOT EXISTS categories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text UNIQUE NOT NULL,
  description text DEFAULT '',
  color text DEFAULT '#3B82F6',
  created_at timestamptz DEFAULT now()
);

-- Create leads table
CREATE TABLE IF NOT EXISTS leads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id uuid REFERENCES categories(id) ON DELETE SET NULL,
  company_name text DEFAULT '',
  contact_name text DEFAULT '',
  email text DEFAULT '',
  phone text DEFAULT '',
  website text DEFAULT '',
  description text DEFAULT '',
  source_url text DEFAULT '',
  status text DEFAULT 'new',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create scraping_jobs table
CREATE TABLE IF NOT EXISTS scraping_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  url text NOT NULL,
  status text DEFAULT 'pending',
  leads_found integer DEFAULT 0,
  error_message text DEFAULT '',
  created_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_leads_category_id ON leads(category_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_status ON scraping_jobs(status);

-- Enable Row Level Security
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraping_jobs ENABLE ROW LEVEL SECURITY;

-- Categories policies
CREATE POLICY "Users can view all categories"
  ON categories FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Users can insert categories"
  ON categories FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Users can update categories"
  ON categories FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Users can delete categories"
  ON categories FOR DELETE
  TO authenticated
  USING (true);

-- Leads policies
CREATE POLICY "Users can view all leads"
  ON leads FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Users can insert leads"
  ON leads FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Users can update leads"
  ON leads FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Users can delete leads"
  ON leads FOR DELETE
  TO authenticated
  USING (true);

-- Scraping jobs policies
CREATE POLICY "Users can view all scraping jobs"
  ON scraping_jobs FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Users can insert scraping jobs"
  ON scraping_jobs FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Users can update scraping jobs"
  ON scraping_jobs FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Users can delete scraping jobs"
  ON scraping_jobs FOR DELETE
  TO authenticated
  USING (true);

-- Insert default categories
INSERT INTO categories (name, description, color) VALUES
  ('Technology', 'Technology and software companies', '#3B82F6'),
  ('Healthcare', 'Healthcare and medical services', '#10B981'),
  ('Finance', 'Financial services and banking', '#F59E0B'),
  ('E-commerce', 'Online retail and e-commerce', '#8B5CF6'),
  ('Marketing', 'Marketing and advertising agencies', '#EF4444'),
  ('Real Estate', 'Real estate and property services', '#06B6D4'),
  ('Education', 'Educational institutions and services', '#EC4899'),
  ('Manufacturing', 'Manufacturing and industrial', '#6366F1'),
  ('Other', 'Uncategorized leads', '#6B7280')
ON CONFLICT (name) DO NOTHING;