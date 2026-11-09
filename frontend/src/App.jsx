import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import Dashboard from './components/Dashboard/Dashboard';
import URLScanner from './components/URLScanner/URLScanner';
import IssuesList from './components/IssuesList/IssuesList';
import CodeReview from './components/CodeReview/CodeReview';
import Reports from './components/Reports/Reports';
import ProjectsList from './components/Projects/ProjectsList';
import './App.css';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setSidebarOpen((prev) => !prev);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  return (
    <div className="app-container">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div className="sidebar-backdrop" onClick={closeSidebar} />
      )}

      {/* Main Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />

      {/* App Main Area */}
      <div className="app-wrapper">
        <Header onToggleSidebar={toggleSidebar} />

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/scan" element={<URLScanner />} />
            <Route path="/scan/:scanId" element={<IssuesList />} />
            <Route path="/scan/:scanId/review" element={<CodeReview />} />
            <Route path="/scan/:scanId/report" element={<Reports />} />
            <Route path="/projects" element={<ProjectsList />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
