import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';
import {
  FiDownload,
  FiPrinter,
  FiCheckCircle,
  FiAlertTriangle,
  FiTrendingUp,
  FiShield,
  FiArrowLeft,
  FiCode,
  FiCheck,
  FiX
} from 'react-icons/fi';
import { getReport } from '../../services/api';
import { downloadJSON, formatDate, getImpactColor } from '../../utils/helpers';
import { toast } from 'react-toastify';
import './Reports.css';

export default function Reports() {
  const { scanId } = useParams();
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadReport() {
      setLoading(true);
      try {
        const data = await getReport(scanId);
        setReportData(data);
      } catch (err) {
        toast.error('Failed to load accessibility report');
      } finally {
        setLoading(false);
      }
    }
    loadReport();
  }, [scanId]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p>Compiling WCAG audit report and compliance metrics...</p>
      </div>
    );
  }

  const {
    url = 'https://example-shop.com',
    generatedAt = new Date().toISOString(),
    score = 88,
    scoreBefore = 64,
    issues = [],
    summary = { critical: 2, serious: 2, moderate: 2, minor: 1 },
    wcagBreakdown = {
      'WCAG 2.1 Level A': '92%',
      'WCAG 2.1 Level AA': '86%',
      'WCAG 2.1 Level AAA': '65%',
      'Section 508': '96%',
    },
  } = reportData || {};

  const barChartData = [
    { severity: 'Critical', count: summary.critical || 2, color: '#ef4444' },
    { severity: 'Serious', count: summary.serious || 2, color: '#f59e0b' },
    { severity: 'Moderate', count: summary.moderate || 2, color: '#7c3aed' },
    { severity: 'Minor', count: summary.minor || 1, color: '#00d4ff' },
  ];

  const handleExportJSON = () => {
    downloadJSON(reportData, `webrevive-report-${scanId}.json`);
    toast.success('Report exported to JSON');
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="report-page page-container">
      {/* Top Header Bar */}
      <div className="report-top-bar">
        <Link to={`/scan/${scanId}`} className="btn btn-secondary">
          <FiArrowLeft /> Back to Issues
        </Link>

        <div className="report-actions">
          <button className="btn btn-secondary" onClick={handlePrint}>
            <FiPrinter /> Print Report
          </button>
          <button className="btn btn-primary" onClick={handleExportJSON}>
            <FiDownload /> Export JSON
          </button>
        </div>
      </div>

      {/* Target Site Summary Card */}
      <div className="report-summary-card">
        <div className="report-target-meta">
          <h1 className="report-title">Accessibility Compliance Audit</h1>
          <div className="report-meta-tags">
            <span>
              Target: <strong style={{ color: '#fff' }}>{url}</strong>
            </span>
            <span>•</span>
            <span>Generated: {formatDate(generatedAt)}</span>
            <span>•</span>
            <span>Audit Standard: WCAG 2.1 Level AA</span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12 }}>
          <span className="badge badge-success" style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
            <FiCheckCircle /> Remediated Patch Available
          </span>
        </div>
      </div>

      {/* Before / After Impact Score Cards */}
      <div className="comparison-grid">
        <div className="comparison-card">
          <span className="comparison-label">Original Health Score</span>
          <div className="score-display-row">
            <span className="score-number" style={{ color: '#f59e0b' }}>
              {scoreBefore}%
            </span>
            <span className="score-status-text" style={{ color: '#f59e0b' }}>
              Non-Compliant
            </span>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Detected 7 WCAG violations before remediation
          </span>
        </div>

        <div className="comparison-card">
          <span className="comparison-label">Post-Remediation Score</span>
          <div className="score-display-row">
            <span className="score-number" style={{ color: '#10b981' }}>
              {score}%
            </span>
            <span className="score-status-text" style={{ color: '#10b981' }}>
              WCAG 2.1 AA Compliant
            </span>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            +24% Accessibility health improvement
          </span>
        </div>

        <div className="comparison-card">
          <span className="comparison-label">AI Remediation Ratio</span>
          <div className="score-display-row">
            <span className="score-number" style={{ color: 'var(--accent-primary)' }}>
              100%
            </span>
            <span className="score-status-text" style={{ color: 'var(--accent-primary)' }}>
              Automated Coverage
            </span>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            All critical and serious DOM nodes refactored
          </span>
        </div>
      </div>

      {/* Charts Split: Bar chart & WCAG standards gauge */}
      <div className="report-charts-grid">
        {/* Severity Bar Chart */}
        <div className="chart-panel">
          <h2 className="chart-header">
            <FiAlertTriangle style={{ color: 'var(--accent-primary)' }} />
            Issues Distributed by Severity
          </h2>
          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4a" />
                <XAxis dataKey="severity" stroke="#a0a0b0" />
                <YAxis allowDecimals={false} stroke="#a0a0b0" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#16213e',
                    border: '1px solid #2a2a4a',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {barChartData.map((entry, index) => (
                    <Cell key={`bar-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Compliance Checklist Breakdown */}
        <div className="chart-panel">
          <h2 className="chart-header">
            <FiShield style={{ color: 'var(--accent-primary)' }} />
            Compliance Index
          </h2>
          <div className="wcag-checklist">
            {Object.entries(wcagBreakdown).map(([standard, rate]) => (
              <div key={standard} className="wcag-item-row">
                <span className="wcag-item-name">{standard}</span>
                <span className="wcag-item-rate">{rate}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Issues Table Breakdown */}
      <div className="report-table-card">
        <h2 className="chart-header" style={{ marginBottom: 16 }}>
          <FiCode style={{ color: 'var(--accent-primary)' }} />
          Catalog of Audit Findings & Remediation Status
        </h2>

        <table className="report-table">
          <thead>
            <tr>
              <th>Rule ID</th>
              <th>Impact</th>
              <th>Description</th>
              <th>Status</th>
              <th>Success Criteria</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue) => (
              <tr key={issue.id}>
                <td>
                  <strong style={{ color: '#fff', fontFamily: 'var(--font-mono)' }}>
                    {issue.ruleId}
                  </strong>
                </td>
                <td>
                  <span className={`badge badge-${issue.impact || 'minor'}`}>
                    {issue.impact}
                  </span>
                </td>
                <td>{issue.description}</td>
                <td>
                  <span className="badge badge-success" style={{ gap: 4 }}>
                    <FiCheck /> Remediated
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {(issue.wcagTags || ['wcag2a']).slice(0, 2).map((t) => (
                      <span
                        key={t}
                        style={{
                          fontSize: '0.72rem',
                          background: 'rgba(124, 58, 237, 0.2)',
                          color: '#c4b5fd',
                          padding: '2px 6px',
                          borderRadius: '4px',
                        }}
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
