import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FiFolder,
  FiPlus,
  FiExternalLink,
  FiActivity,
  FiShield,
  FiClock,
  FiSearch,
  FiX,
  FiCheck
} from 'react-icons/fi';
import { useProjects } from '../../hooks/useAccessibility';
import { formatDate } from '../../utils/helpers';
import { toast } from 'react-toastify';
import './ProjectsList.css';

export default function ProjectsList() {
  const navigate = useNavigate();
  const { projects, loading, addProject } = useProjects();

  const [showModal, setShowModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectUrl, setNewProjectUrl] = useState('');

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newProjectName.trim() || !newProjectUrl.trim()) {
      toast.warning('Please provide both a project name and URL');
      return;
    }

    let urlToUse = newProjectUrl.trim();
    if (!/^https?:\/\//i.test(urlToUse)) {
      urlToUse = 'https://' + urlToUse;
    }

    try {
      await addProject({
        name: newProjectName.trim(),
        url: urlToUse,
        scansCount: 0,
        score: 100,
        status: 'new',
      });
      setShowModal(false);
      setNewProjectName('');
      setNewProjectUrl('');
    } catch {
      // toast is already handled in hook
    }
  };

  const handleRunScan = (projectUrl) => {
    navigate('/scan');
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p>Loading managed accessibility projects...</p>
      </div>
    );
  }

  return (
    <div className="projects-page page-container">
      {/* Header bar */}
      <div className="projects-top-bar">
        <div>
          <h1 className="page-title">
            <FiFolder style={{ color: 'var(--accent-primary)' }} />
            Managed Accessibility Projects
          </h1>
          <p className="page-subtitle">
            Continuous accessibility monitoring and refactoring repositories
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <FiPlus /> New Project Target
        </button>
      </div>

      {/* Projects Grid */}
      <div className="projects-grid">
        {projects.map((proj) => {
          const score = proj.score || 85;
          const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';

          return (
            <div key={proj.id} className="project-card">
              <div>
                <div className="project-card-header">
                  <div>
                    <h3 className="project-name">{proj.name}</h3>
                    <a
                      href={proj.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="project-url"
                    >
                      <FiExternalLink />
                      <span>{proj.url.replace(/^https?:\/\//i, '')}</span>
                    </a>
                  </div>
                  <span
                    className="badge"
                    style={{
                      backgroundColor: `${scoreColor}20`,
                      color: scoreColor,
                      border: `1px solid ${scoreColor}40`,
                    }}
                  >
                    {score}%
                  </span>
                </div>

                <div className="project-stats-row">
                  <div className="pstat-item">
                    <span className="pstat-val">{proj.scansCount || 1}</span>
                    <span className="pstat-lbl">Audits</span>
                  </div>
                  <div className="pstat-item">
                    <span className="pstat-val" style={{ color: '#10b981' }}>
                      WCAG AA
                    </span>
                    <span className="pstat-lbl">Standard</span>
                  </div>
                  <div className="pstat-item">
                    <span className="pstat-val" style={{ fontSize: '0.88rem' }}>
                      {formatDate(proj.lastScanDate)}
                    </span>
                    <span className="pstat-lbl">Last Audited</span>
                  </div>
                </div>
              </div>

              <div className="project-card-actions">
                <button
                  className="btn btn-primary"
                  style={{ flex: 1, padding: '8px 14px', fontSize: '0.85rem' }}
                  onClick={() => handleRunScan(proj.url)}
                >
                  <FiSearch /> Scan Now
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '8px 14px', fontSize: '0.85rem' }}
                  onClick={() => navigate('/scan/scan-demo-101')}
                >
                  History
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* New Project Modal */}
      {showModal && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h3 style={{ color: '#fff', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                <FiFolder style={{ color: 'var(--accent-primary)' }} /> Add Target Website
              </h3>
              <button
                style={{ background: 'transparent', color: 'var(--text-secondary)', fontSize: '1.2rem' }}
                onClick={() => setShowModal(false)}
              >
                <FiX />
              </button>
            </div>

            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label className="form-label">Project Name</label>
                <input
                  type="text"
                  placeholder="e.g. Marketing Storefront"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label className="form-label">Target Website URL</label>
                <input
                  type="text"
                  placeholder="https://example.com"
                  value={newProjectUrl}
                  onChange={(e) => setNewProjectUrl(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 24 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  <FiCheck /> Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
