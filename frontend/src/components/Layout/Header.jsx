import React, { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  FiMenu,
  FiSettings,
  FiGithub,
  FiCpu,
  FiX,
  FiCheck,
  FiExternalLink
} from 'react-icons/fi';
import './Layout.css';

export default function Header({ onToggleSidebar }) {
  const location = useLocation();
  const [showSettings, setShowSettings] = useState(false);
  const [wcagLevel, setWcagLevel] = useState('AA');
  const [autoRefactor, setAutoRefactor] = useState(true);

  // Derive dynamic breadcrumbs and title
  const pathParts = location.pathname.split('/').filter(Boolean);

  let title = 'Accessibility Dashboard';
  const breadcrumbs = [{ label: 'WebRevive', path: '/' }];

  if (pathParts.length === 0) {
    title = 'Overview & Health Dashboard';
  } else if (pathParts[0] === 'scan' && pathParts.length === 1) {
    title = 'Automated Website Scanner';
    breadcrumbs.push({ label: 'Scanner', path: '/scan' });
  } else if (pathParts[0] === 'scan' && pathParts.length >= 2) {
    const scanId = pathParts[1];
    breadcrumbs.push({ label: 'Scanner', path: '/scan' });
    breadcrumbs.push({ label: `Audit: ${scanId}`, path: `/scan/${scanId}` });

    if (pathParts[2] === 'review') {
      title = 'AI Code Refactoring & Review';
      breadcrumbs.push({ label: 'Code Review', path: `/scan/${scanId}/review` });
    } else if (pathParts[2] === 'report') {
      title = 'WCAG Compliance Audit Report';
      breadcrumbs.push({ label: 'Report', path: `/scan/${scanId}/report` });
    } else {
      title = 'Scan Results & Detected Issues';
    }
  } else if (pathParts[0] === 'projects') {
    title = 'Managed Projects & Targets';
    breadcrumbs.push({ label: 'Projects', path: '/projects' });
  }

  return (
    <>
      <header className="header">
        <div className="header-left">
          <button
            className="mobile-toggle"
            onClick={onToggleSidebar}
            aria-label="Toggle navigation menu"
          >
            <FiMenu />
          </button>

          <div className="header-breadcrumb-wrapper">
            <div className="breadcrumb-trail">
              {breadcrumbs.map((crumb, idx) => (
                <React.Fragment key={crumb.path}>
                  {idx > 0 && <span className="breadcrumb-separator">/</span>}
                  {idx === breadcrumbs.length - 1 ? (
                    <span style={{ color: 'var(--text-secondary)' }}>{crumb.label}</span>
                  ) : (
                    <Link to={crumb.path}>{crumb.label}</Link>
                  )}
                </React.Fragment>
              ))}
            </div>
            <h1 className="header-title">{title}</h1>
          </div>
        </div>

        <div className="header-actions">
          <div className="badge-engine">
            <FiCpu />
            <span>Claude & axe-core 4.4</span>
          </div>

          <button
            className="header-icon-btn"
            onClick={() => setShowSettings(true)}
            title="Engine Settings"
            aria-label="Settings"
          >
            <FiSettings />
          </button>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="header-icon-btn"
            title="GitHub Repository"
            aria-label="GitHub Repository"
          >
            <FiGithub />
          </a>
        </div>
      </header>

      {/* Settings Modal */}
      {showSettings && (
        <div className="settings-modal-backdrop" onClick={() => setShowSettings(false)}>
          <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
            <div className="settings-header">
              <h3 style={{ color: '#fff', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                <FiSettings /> AI Engine Settings
              </h3>
              <button
                className="header-icon-btn"
                style={{ width: 32, height: 32 }}
                onClick={() => setShowSettings(false)}
              >
                <FiX />
              </button>
            </div>

            <div className="settings-content">
              <div className="settings-option">
                <div>
                  <div style={{ fontWeight: 600, color: '#fff' }}>Target WCAG Standard</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Compliance guidelines evaluated during inspection
                  </div>
                </div>
                <select
                  value={wcagLevel}
                  onChange={(e) => setWcagLevel(e.target.value)}
                  style={{ width: 140 }}
                >
                  <option value="A">WCAG 2.1 Level A</option>
                  <option value="AA">WCAG 2.1 Level AA</option>
                  <option value="AAA">WCAG 2.1 Level AAA</option>
                </select>
              </div>

              <div className="settings-option">
                <div>
                  <div style={{ fontWeight: 600, color: '#fff' }}>AI Context Synthesis</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Automatically suggest semantic markup and ARIA fixes
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={autoRefactor}
                  onChange={(e) => setAutoRefactor(e.target.checked)}
                  style={{ width: 18, height: 18, cursor: 'pointer' }}
                />
              </div>

              <div className="settings-option">
                <div>
                  <div style={{ fontWeight: 600, color: '#fff' }}>Backend Endpoint</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    http://localhost:8000 (Proxy configured)
                  </div>
                </div>
                <span className="badge badge-success">Connected</span>
              </div>
            </div>

            <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button className="btn btn-primary" onClick={() => setShowSettings(false)}>
                <FiCheck /> Save Preferences
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
