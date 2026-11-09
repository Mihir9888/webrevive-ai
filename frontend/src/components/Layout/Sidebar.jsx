import React, { useState, useEffect } from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  FiGrid,
  FiSearch,
  FiFolder,
  FiShield,
  FiFileText,
  FiCode,
  FiCheckCircle,
  FiLayers,
  FiActivity
} from 'react-icons/fi';
import './Layout.css';

export default function Sidebar({ isOpen, onClose }) {
  const [recentScans, setRecentScans] = useState([]);

  useEffect(() => {
    // Load recent scans from localStorage
    try {
      const raw = localStorage.getItem('webrevive_mock_scans');
      if (raw) {
        setRecentScans(JSON.parse(raw).slice(0, 5));
      } else {
        setRecentScans([
          { id: 'scan-demo-101', url: 'https://example-shop.com', score: 64 },
          { id: 'scan-demo-102', url: 'https://portal.university-demo.edu', score: 82 },
        ]);
      }
    } catch {
      // fallback
    }
  }, []);

  return (
    <aside className={`sidebar ${isOpen ? 'mobile-open' : ''}`}>
      {/* Brand logo & title */}
      <Link to="/" className="sidebar-brand" onClick={onClose}>
        <div className="brand-icon-wrapper">
          <FiShield />
        </div>
        <div className="brand-text">
          <span className="brand-name">WebRevive AI</span>
          <span className="brand-tagline">Accessibility Engine</span>
        </div>
      </Link>

      {/* Main Navigation */}
      <nav className="sidebar-nav">
        <span className="nav-section-title">Navigation</span>
        
        <NavLink
          to="/"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          onClick={onClose}
          end
        >
          <span className="nav-icon"><FiGrid /></span>
          <span>Dashboard</span>
        </NavLink>

        <NavLink
          to="/scan"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          onClick={onClose}
        >
          <span className="nav-icon"><FiSearch /></span>
          <span>Scan URL</span>
        </NavLink>

        <NavLink
          to="/projects"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          onClick={onClose}
        >
          <span className="nav-icon"><FiFolder /></span>
          <span>Projects</span>
        </NavLink>

        <span className="nav-section-title" style={{ marginTop: '12px' }}>
          Recent Audits
        </span>

        <div className="recent-scans-list">
          {recentScans.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', padding: '0 12px' }}>
              No recent scans yet
            </p>
          ) : (
            recentScans.map((scan) => {
              const score = scan.score || 70;
              const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
              const domain = scan.url.replace(/^https?:\/\//i, '').replace(/\/$/, '');

              return (
                <Link
                  key={scan.id}
                  to={`/scan/${scan.id}`}
                  className="recent-scan-item"
                  onClick={onClose}
                  title={scan.url}
                >
                  <span className="recent-scan-url">{domain}</span>
                  <span
                    className="recent-scan-score"
                    style={{
                      backgroundColor: `${color}20`,
                      color: color,
                      border: `1px solid ${color}40`,
                    }}
                  >
                    {score}%
                  </span>
                </Link>
              );
            })
          )}
        </div>
      </nav>

      {/* Sidebar Footer: Engine Status */}
      <div className="sidebar-footer">
        <div className="system-status">
          <span className="status-dot"></span>
          <span>AI Engine Ready</span>
        </div>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          v1.0.0
        </span>
      </div>
    </aside>
  );
}
