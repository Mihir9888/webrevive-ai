import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from 'recharts';
import {
  FiSearch,
  FiAlertTriangle,
  FiCheckCircle,
  FiActivity,
  FiArrowRight,
  FiShield,
  FiExternalLink,
  FiTrendingUp,
  FiLayers,
} from 'react-icons/fi';
import { scanUrl } from '../../services/api';
import { formatDate } from '../../utils/helpers';
import { toast } from 'react-toastify';
import './Dashboard.css';

export default function Dashboard() {
  const navigate = useNavigate();
  const [quickUrl, setQuickUrl] = useState('');
  const [scanning, setScanning] = useState(false);
  const [recentScans, setRecentScans] = useState([]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('webrevive_mock_scans');
      if (stored) {
        setRecentScans(JSON.parse(stored));
      } else {
        const defaultScans = [
          {
            id: 'scan-demo-101',
            url: 'https://example-shop.com',
            title: 'Example Shop Storefront',
            status: 'completed',
            createdAt: new Date(Date.now() - 3600000 * 3).toISOString(),
            score: 64,
            totalIssues: 12,
            criticalCount: 3,
            seriousCount: 4,
            moderateCount: 3,
            minorCount: 2,
          },
          {
            id: 'scan-demo-102',
            url: 'https://portal.university-demo.edu',
            title: 'University Portal',
            status: 'completed',
            createdAt: new Date(Date.now() - 86400000 * 2).toISOString(),
            score: 82,
            totalIssues: 5,
            criticalCount: 1,
            seriousCount: 2,
            moderateCount: 1,
            minorCount: 1,
          },
          {
            id: 'scan-demo-103',
            url: 'https://fintech-dashboard-app.io',
            title: 'FinTech Banking Gateway',
            status: 'completed',
            createdAt: new Date(Date.now() - 86400000 * 4).toISOString(),
            score: 91,
            totalIssues: 3,
            criticalCount: 0,
            seriousCount: 1,
            moderateCount: 1,
            minorCount: 1,
          },
        ];
        setRecentScans(defaultScans);
        localStorage.setItem('webrevive_mock_scans', JSON.stringify(defaultScans));
      }
    } catch {
      // fallback
    }
  }, []);

  const handleQuickScan = async (e) => {
    e.preventDefault();
    if (!quickUrl.trim()) {
      toast.warning('Please enter a valid website URL');
      return;
    }

    let urlToScan = quickUrl.trim();
    if (!/^https?:\/\//i.test(urlToScan)) {
      urlToScan = 'https://' + urlToScan;
    }

    try {
      setScanning(true);
      toast.info(`Initializing AI scan for ${urlToScan}...`);
      const res = await scanUrl(urlToScan);
      if (res && res.scanId) {
        toast.success('Scan initialized! Inspecting issues...');
        navigate(`/scan/${res.scanId}`);
      }
    } catch (err) {
      toast.error('Unable to initiate scan');
    } finally {
      setScanning(false);
    }
  };

  // Aggregated Statistics
  const totalScans = recentScans.length;
  const totalIssuesFound = recentScans.reduce((acc, s) => acc + (s.totalIssues || 0), 0) || 28;
  const totalIssuesFixed = Math.round(totalIssuesFound * 0.82) || 23;
  const overallSuccessRate = '94.2%';

  // Recharts severity pie data
  const severityData = [
    { name: 'Critical', value: 8, color: '#ef4444' },
    { name: 'Serious', value: 14, color: '#f59e0b' },
    { name: 'Moderate', value: 18, color: '#7c3aed' },
    { name: 'Minor', value: 9, color: '#00d4ff' },
  ];

  return (
    <div className="dashboard-container page-container">
      {/* Welcome Banner & Quick Scan */}
      <motion.div
        className="welcome-card"
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="welcome-title">
          <FiShield style={{ color: 'var(--accent-primary)' }} />
          WebRevive AI - Intelligent Accessibility Engineering
        </div>
        <p className="welcome-desc">
          Automated WCAG 2.1 AA/AAA compliance scanning, AST-based HTML refactoring, and AI-driven
          accessible code remediation. Scan live websites or uploaded UI bundles to eliminate accessibility barriers.
        </p>

        {/* Quick Scan Input */}
        <form className="quick-scan-section" onSubmit={handleQuickScan}>
          <div className="quick-scan-input-wrapper">
            <FiSearch className="quick-scan-icon" />
            <input
              type="text"
              className="quick-scan-input"
              placeholder="Enter target URL (e.g., https://mybrand.com)"
              value={quickUrl}
              onChange={(e) => setQuickUrl(e.target.value)}
              disabled={scanning}
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={scanning}>
            {scanning ? (
              <>
                <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                <span>Scanning...</span>
              </>
            ) : (
              <>
                <FiSearch />
                <span>Scan Now</span>
              </>
            )}
          </button>
        </form>
      </motion.div>

      {/* 4 Stats Cards */}
      <div className="stats-grid">
        <motion.div
          className="stat-card"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <div className="stat-icon-wrapper blue">
            <FiActivity />
          </div>
          <div className="stat-content">
            <span className="stat-value">{totalScans}</span>
            <span className="stat-label">Total Audits Run</span>
          </div>
        </motion.div>

        <motion.div
          className="stat-card"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
        >
          <div className="stat-icon-wrapper orange">
            <FiAlertTriangle />
          </div>
          <div className="stat-content">
            <span className="stat-value">{totalIssuesFound}</span>
            <span className="stat-label">Issues Detected</span>
          </div>
        </motion.div>

        <motion.div
          className="stat-card"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <div className="stat-icon-wrapper green">
            <FiCheckCircle />
          </div>
          <div className="stat-content">
            <span className="stat-value">{totalIssuesFixed}</span>
            <span className="stat-label">Issues Refactored</span>
          </div>
        </motion.div>

        <motion.div
          className="stat-card"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.25 }}
        >
          <div className="stat-icon-wrapper purple">
            <FiTrendingUp />
          </div>
          <div className="stat-content">
            <span className="stat-value">{overallSuccessRate}</span>
            <span className="stat-label">Fix Approval Rate</span>
          </div>
        </motion.div>
      </div>

      {/* Middle Split: Severity Chart & Recent Audits Table */}
      <div className="dashboard-middle-grid">
        {/* Pie Chart */}
        <motion.div
          className="chart-card"
          initial={{ opacity: 0, x: -15 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
        >
          <div className="card-title-row">
            <h2 className="card-title">
              <FiLayers style={{ color: 'var(--accent-primary)' }} />
              Issues Breakdown by Severity
            </h2>
            <span className="badge badge-minor">49 Total</span>
          </div>

          <div className="chart-container-box">
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={severityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} stroke="#16213e" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#16213e',
                    borderColor: '#2a2a4a',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                  itemStyle={{ color: '#fff' }}
                />
                <Legend
                  verticalAlign="bottom"
                  iconType="circle"
                  wrapperStyle={{ paddingTop: '10px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Recent Scans Table */}
        <motion.div
          className="recent-scans-card"
          initial={{ opacity: 0, x: 15 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.35 }}
        >
          <div className="card-title-row">
            <h2 className="card-title">
              <FiActivity style={{ color: 'var(--accent-primary)' }} />
              Recent Accessibility Audits
            </h2>
            <Link to="/scan" className="action-link" style={{ fontSize: '0.85rem' }}>
              New Scan <FiArrowRight />
            </Link>
          </div>

          <div className="recent-scans-table-wrapper">
            <table className="scans-table">
              <thead>
                <tr>
                  <th>Target URL</th>
                  <th>Date</th>
                  <th>Health</th>
                  <th>Issues</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentScans.slice(0, 5).map((scan) => {
                  const score = scan.score || 75;
                  const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';

                  return (
                    <tr key={scan.id}>
                      <td className="url-cell" title={scan.url}>
                        <FiExternalLink style={{ color: 'var(--accent-primary)' }} />
                        <span>{scan.url.replace(/^https?:\/\//i, '')}</span>
                      </td>
                      <td>{formatDate(scan.createdAt)}</td>
                      <td>
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
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, color: '#fff' }}>
                          {scan.totalIssues || 7}
                        </span>
                      </td>
                      <td>
                        <Link to={`/scan/${scan.id}`} className="action-link">
                          Review <FiArrowRight />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
