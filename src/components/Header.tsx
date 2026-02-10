import { Database, Search } from 'lucide-react';

type HeaderProps = {
  onScrapeSubmit: (url: string) => void;
  isLoading: boolean;
};

export function Header({ onScrapeSubmit, isLoading }: HeaderProps) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const url = formData.get('url') as string;
    if (url) {
      onScrapeSubmit(url);
      e.currentTarget.reset();
    }
  };

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <Database className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Lead Scraper Pro</h1>
              <p className="text-sm text-gray-600">Extract and organize leads from any website</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="url"
              name="url"
              placeholder="Enter website URL to scrape (e.g., https://example.com)"
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
              disabled={isLoading}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {isLoading ? 'Scraping...' : 'Scrape Leads'}
          </button>
        </form>
      </div>
    </header>
  );
}
