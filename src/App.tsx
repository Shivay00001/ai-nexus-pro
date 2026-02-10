import { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { LeadsView } from './components/LeadsView';
import { ScrapingView } from './components/ScrapingView';
import { HistoryView } from './components/HistoryView';
import { CategoriesView } from './components/CategoriesView';
import { ToastContainer } from './components/Toast';

function AppContent() {
  const { currentView } = useApp();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />;
      case 'leads':
        return <LeadsView />;
      case 'scrape':
        return <ScrapingView />;
      case 'history':
        return <HistoryView />;
      case 'categories':
        return <CategoriesView />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-[#030712] bg-grid-pattern">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <main
        className={`transition-all duration-300 min-h-screen ${sidebarCollapsed ? 'ml-[72px]' : 'ml-64'
          }`}
      >
        <div className="max-w-7xl mx-auto px-6 py-8">
          {renderView()}
        </div>
      </main>
      <ToastContainer />
    </div>
  );
}

function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}

export default App;
