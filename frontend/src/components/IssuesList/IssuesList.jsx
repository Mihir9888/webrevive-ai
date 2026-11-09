import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiExternalLink,
  FiChevronDown,
  FiSearch,
  FiZap,
  FiCode,
  FiFileText,
  FiCheck,
  FiHelpCircle,
  FiTarget,
  FiArrowRight,
  FiArrowLeft,
  FiClock,
  FiShield
} from 'react-icons/fi';
import { useScan, useIssues } from '../../hooks/useAccessibility';
import { analyzeIssues } from '../../services/api';
import { formatDate, getImpactIcon, calculateComplianceScore } from '../../utils/helpers';
import { toast } from 'react-toastify';
import './IssuesList.css';

export default function IssuesList() {
  const { scanId } = useParams();
  const navigate = useNavigate();

  const { scan, loading: scanLoading } = useScan(scanId);
  const {
    issues,
    allFilteredCount,
    totalRawCount,
    loading: issuesLoading,
    impactFilter,
    setImpactFilter,
    searchQuery,
    setSearchQuery,
    currentPage,
    setCurrentPage,
    totalPages,
  } = useIssues(scanId);

  const [expandedIssueId, setExpandedIssueId] = useState(null);
  const [analyzingAll, setAnalyzingAll] = useState(false);
  const [analyzingMap, setAnalyzingMap] = useState({});

  const toggleExpand = (id) => {
    setExpandedIssueId((prev) => (prev === id ? null : id));
  };

  const handleAnalyzeAll = async () => {
    setAnalyzingAll(true);
    try {
      toast.info('Dispatching AI engine to generate semantic fixes...');
      await analyzeIssues(scanId);
      toast.success('AI remediation ready for code review!');
      navigate(`/scan/${scanId}/review`);
    } catch (err) {
      toast.error('AI analysis request encountered an issue');
    } finally {
      setAnalyzingAll(false);
    }
  };

  const handleAnalyzeSingle = async (issueId, e) => {
    e.stopPropagation();
    setAnalyzingMap((prev) => ({ ...prev, [issueId]: true }));
    try {
      await new Promise((res) => setTimeout(res, 800));
      toast.success('Fix generated for this issue! Opening Code Review...');
      navigate(`/scan/${scanId}/review`);
    } catch {
      toast.error('Could not analyze issue');
    } finally {
      setAnalyzingMap((prev) => ({ ...prev, [issueId]: false }));
    }
  };

  if (scanLoading || issuesLoading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p>Inspecting accessibility rules and building issue catalog...</p>
      </div>
    );
  }

  const score = scan?.score !== undefined 
    ? scan.score 
    : calculateComplianceScore(issues);
  const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div className="issues-page page-container">
      {/* Scan Summary Top Bar */}
      <div className="scan-summary-header">
        <div className="summary-info">
          <div className="summary-url">
            <FiShield style={{ color: 'var(--accent-primary)' }} />
            <span>{scan?.url || 'https://target-audit.com'}</span>
          </div>
          <div className="summary-meta">
            <span>
              <FiClock style={{ verticalAlign: 'middle', marginRight: 4 }} />
              Audited: {formatDate(scan?.createdAt || new Date())}
            </span>
            <span>•</span>
            <span>
              Total Issues: <strong style={{ color: '#fff' }}>{totalRawCount}</strong>
            </span>
            <span>•</span>
            <span>
              Health Index:{' '}
              <strong style={{ color: scoreColor }}>{score}%</strong>
            </span>
          </div>
        </div>

        <div className="summary-actions">
          <button
            className="btn btn-accent"
            onClick={handleAnalyzeAll}
            disabled={analyzingAll}
          >
            {analyzingAll ? (
              <>
                <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                <span>Synthesizing Fixes...</span>
              </>
            ) : (
              <>
                <FiZap />
                <span>Analyze All Issues with AI</span>
              </>
            )}
          </button>

          <Link to={`/scan/${scanId}/review`} className="btn btn-primary">
            <FiCode />
            <span>Review Suggested Fixes</span>
          </Link>

          <Link to={`/scan/${scanId}/report`} className="btn btn-secondary">
            <FiFileText />
            <span>Audit Report</span>
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="filter-pills">
          <button
            className={`filter-pill ${impactFilter === 'all' ? 'active' : ''}`}
            onClick={() => setImpactFilter('all')}
          >
            All Issues ({totalRawCount})
          </button>
          <button
            className={`filter-pill ${impactFilter === 'critical' ? 'active' : ''}`}
            onClick={() => setImpactFilter('critical')}
          >
            <span style={{ color: '#ef4444' }}>●</span> Critical
          </button>
          <button
            className={`filter-pill ${impactFilter === 'serious' ? 'active' : ''}`}
            onClick={() => setImpactFilter('serious')}
          >
            <span style={{ color: '#f59e0b' }}>●</span> Serious
          </button>
          <button
            className={`filter-pill ${impactFilter === 'moderate' ? 'active' : ''}`}
            onClick={() => setImpactFilter('moderate')}
          >
            <span style={{ color: '#7c3aed' }}>●</span> Moderate
          </button>
          <button
            className={`filter-pill ${impactFilter === 'minor' ? 'active' : ''}`}
            onClick={() => setImpactFilter('minor')}
          >
            <span style={{ color: '#00d4ff' }}>●</span> Minor
          </button>
        </div>

        <div className="search-wrapper">
          <FiSearch className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Filter by rule, description, selector..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Issues List Cards */}
      {issues.length === 0 ? (
        <div className="empty-state">
          <FiCheck className="empty-state-icon" style={{ color: '#10b981' }} />
          <h3>No Accessibility Violations Found</h3>
          <p>
            No issues match the selected impact filter or search keyword.
          </p>
          <button
            className="btn btn-secondary"
            onClick={() => {
              setImpactFilter('all');
              setSearchQuery('');
            }}
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="issues-cards-list">
          {issues.map((issue) => {
            const isExpanded = expandedIssueId === issue.id;
            const isAnalyzing = analyzingMap[issue.id];

            return (
              <div key={issue.id} className="issue-card">
                {/* Header row clickable */}
                <div
                  className="issue-card-header"
                  onClick={() => toggleExpand(issue.id)}
                >
                  <div className="issue-header-left">
                    <span className={`badge badge-${issue.impact || 'minor'}`}>
                      {issue.impact || 'minor'}
                    </span>
                    <span className="issue-rule-id">{issue.ruleId}</span>
                    <span className="issue-rule-title">{issue.description}</span>
                  </div>

                  <div className="issue-header-right">
                    <button
                      className="btn btn-accent"
                      style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                      onClick={(e) => handleAnalyzeSingle(issue.id, e)}
                      disabled={isAnalyzing}
                    >
                      {isAnalyzing ? (
                        <>
                          <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                          <span>Remediating...</span>
                        </>
                      ) : (
                        <>
                          <FiZap />
                          <span>Analyze with AI</span>
                        </>
                      )}
                    </button>
                    <FiChevronDown
                      className={`chevron-icon ${isExpanded ? 'expanded' : ''}`}
                    />
                  </div>
                </div>

                {/* Expanded Details */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      className="issue-card-body"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      {/* Guidance / Help */}
                      <div className="issue-detail-row">
                        <span className="detail-label">Remediation Guidance</span>
                        <p className="detail-value">{issue.help}</p>
                      </div>

                      {/* HTML Source Snippet */}
                      {issue.html && (
                        <div className="issue-detail-row">
                          <span className="detail-label">Offending DOM Element</span>
                          <div className="code-snippet-box">
                            <code>{issue.html}</code>
                          </div>
                        </div>
                      )}

                      {/* CSS Target Selector */}
                      {issue.selector && (
                        <div className="issue-detail-row">
                          <span className="detail-label">DOM Selector Path</span>
                          <div className="selector-box">
                            <FiTarget style={{ verticalAlign: 'middle', marginRight: 6 }} />
                            <span>{issue.selector}</span>
                          </div>
                        </div>
                      )}

                      {/* WCAG Criteria Tags */}
                      {issue.wcagTags && issue.wcagTags.length > 0 && (
                        <div className="issue-detail-row">
                          <span className="detail-label">WCAG Success Criteria</span>
                          <div className="wcag-tags-row">
                            {issue.wcagTags.map((tag) => (
                              <span key={tag} className="wcag-tag">
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Action footer */}
                      <div className="issue-actions-row">
                        {issue.helpUrl ? (
                          <a
                            href={issue.helpUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="action-link"
                            style={{ fontSize: '0.85rem' }}
                          >
                            <FiHelpCircle />
                            <span>Rule Documentation & Guidelines</span>
                            <FiExternalLink />
                          </a>
                        ) : <div />}

                        <button
                          className="btn btn-primary"
                          style={{ padding: '6px 14px', fontSize: '0.82rem' }}
                          onClick={() => navigate(`/scan/${scanId}/review`)}
                        >
                          <FiCode />
                          <span>Open in Refactoring Studio</span>
                          <FiArrowRight />
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination-bar">
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Showing {issues.length} of {allFilteredCount} issues
          </span>

          <div className="pagination-controls">
            <button
              className="page-btn"
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
              disabled={currentPage === 1}
            >
              <FiArrowLeft /> Prev
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((pg) => (
              <button
                key={pg}
                className={`page-btn ${currentPage === pg ? 'active' : ''}`}
                onClick={() => setCurrentPage(pg)}
              >
                {pg}
              </button>
            ))}

            <button
              className="page-btn"
              onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
              disabled={currentPage === totalPages}
            >
              Next <FiArrowRight />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
