import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import {
  FiCheck,
  FiX,
  FiEdit2,
  FiCode,
  FiLayers,
  FiCheckCircle,
  FiFileText,
  FiZap,
  FiShield,
  FiArrowRight,
  FiColumns,
  FiPercent,
  FiSave
} from 'react-icons/fi';
import DiffViewer from '../DiffViewer/DiffViewer';
import { useSuggestions } from '../../hooks/useAccessibility';
import { applyRefactoring, getDiff } from '../../services/api';
import { toast } from 'react-toastify';
import './CodeReview.css';

const DEFAULT_SOURCE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Online Shop</title>
</head>
<body>
  <!-- Header with inaccessible button -->
  <header class="navbar">
    <div class="logo">ShopBrand</div>
    <button class="cart-icon-btn" onclick="openCart()">
      <i class="fa fa-shopping-cart"></i>
    </button>
  </header>

  <!-- Hero Banner with missing image alt -->
  <div class="hero-banner">
    <img src="/assets/hero-banner-spring.jpg" class="promo-img">
    <h4 class="section-title">Trending Products</h4>
  </div>

  <!-- Form lacking label and poor contrast -->
  <section class="newsletter-section">
    <form class="newsletter">
      <input type="email" placeholder="Enter your email" name="subscriber">
      <button type="submit">Subscribe</button>
    </form>
    <p class="subtext-muted" style="color: #999999; background-color: #ffffff;">
      Terms and conditions apply to all promotions.
    </p>
    <a href="/articles/24" class="read-more-link">Click here</a>
  </section>

  <!-- Missing main landmark -->
  <div id="app-content">
    <p>Product catalog content goes here...</p>
  </div>
</body>
</html>`;

export default function CodeReview() {
  const { scanId } = useParams();
  const navigate = useNavigate();

  const {
    suggestions,
    loading,
    changeSuggestionStatus,
    runAnalysis,
    analyzing,
  } = useSuggestions(scanId);

  const [activeSuggestionId, setActiveSuggestionId] = useState(null);
  const [sourceCode, setSourceCode] = useState(DEFAULT_SOURCE_HTML);
  const [isDiffMode, setIsDiffMode] = useState(false);
  const [diffData, setDiffData] = useState(null);
  const [applying, setApplying] = useState(false);

  // Edit suggestion modal/state
  const [editingCode, setEditingCode] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (suggestions.length > 0 && !activeSuggestionId) {
      setActiveSuggestionId(suggestions[0].id);
    }
  }, [suggestions, activeSuggestionId]);

  // Load diff when switching to Diff view
  useEffect(() => {
    if (isDiffMode && !diffData) {
      getDiff(scanId).then((res) => {
        setDiffData(res);
      });
    }
  }, [isDiffMode, diffData, scanId]);

  const activeSuggestion = suggestions.find((s) => s.id === activeSuggestionId) || suggestions[0];

  // Count metrics
  const approvedCount = suggestions.filter((s) => s.status === 'approved').length;
  const rejectedCount = suggestions.filter((s) => s.status === 'rejected').length;
  const pendingCount = suggestions.filter((s) => !s.status || s.status === 'pending').length;

  const handleApplyAllApproved = async () => {
    const approvedIds = suggestions
      .filter((s) => s.status === 'approved')
      .map((s) => s.id);

    if (approvedIds.length === 0) {
      toast.warning('No approved fixes to apply yet. Please approve at least one suggestion.');
      return;
    }

    setApplying(true);
    try {
      await applyRefactoring(scanId, approvedIds);
      toast.success(`Successfully refactored ${approvedIds.length} accessibility violations!`);
      // Update local editor preview to refactored content
      if (diffData?.modifiedCode) {
        setSourceCode(diffData.modifiedCode);
      }
    } catch (err) {
      toast.error('Failed to apply refactored fixes');
    } finally {
      setApplying(false);
    }
  };

  const handleStartEdit = () => {
    if (activeSuggestion) {
      setEditingCode(activeSuggestion.suggestedCode || '');
      setIsEditing(true);
    }
  };

  const handleSaveEdit = () => {
    if (activeSuggestion) {
      activeSuggestion.suggestedCode = editingCode;
      setIsEditing(false);
      toast.success('Custom remediation code saved');
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p>Loading code review workspace and suggestions...</p>
      </div>
    );
  }

  return (
    <div className="review-page page-container">
      {/* Top Status & Controls Header */}
      <div className="review-header-bar">
        <div className="review-stats-summary">
          <span className="summary-pill pill-approved">
            <FiCheck /> {approvedCount} Approved
          </span>
          <span className="summary-pill pill-rejected">
            <FiX /> {rejectedCount} Rejected
          </span>
          <span className="summary-pill pill-pending">
            ● {pendingCount} Pending Review
          </span>
        </div>

        <div className="review-actions-group">
          <button
            className={`btn ${isDiffMode ? 'btn-accent' : 'btn-secondary'}`}
            onClick={() => setIsDiffMode(!isDiffMode)}
          >
            <FiColumns />
            <span>{isDiffMode ? 'Show Code Editor' : 'Side-by-Side Diff'}</span>
          </button>

          <button
            className="btn btn-primary"
            onClick={handleApplyAllApproved}
            disabled={applying || approvedCount === 0}
          >
            {applying ? (
              <>
                <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                <span>Applying Fixes...</span>
              </>
            ) : (
              <>
                <FiCheckCircle />
                <span>Apply All Approved ({approvedCount})</span>
              </>
            )}
          </button>

          <Link to={`/scan/${scanId}/report`} className="btn btn-secondary">
            <FiFileText />
            <span>View Final Report</span>
          </Link>
        </div>
      </div>

      {/* Main Workspace */}
      {isDiffMode ? (
        /* Diff Mode Active */
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
          <DiffViewer
            originalCode={diffData?.originalCode || DEFAULT_SOURCE_HTML}
            modifiedCode={diffData?.modifiedCode || DEFAULT_SOURCE_HTML}
            language="html"
            title="Refactoring Diff: WCAG 2.1 AA Remediations"
          />
        </div>
      ) : (
        /* Standard Split Mode: Suggestions List on Left, Editor & Suggestion on Right */
        <div className="review-split-workspace">
          {/* Left Panel: Suggestions List */}
          <div className="review-left-panel">
            <div className="panel-header">
              <span>Remediation Queue ({suggestions.length})</span>
              <button
                className="btn btn-accent"
                style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                onClick={runAnalysis}
                disabled={analyzing}
              >
                <FiZap /> {analyzing ? 'Synthesizing...' : 'Re-Analyze'}
              </button>
            </div>

            <div className="suggestions-scroll-list">
              {suggestions.map((sug) => {
                const isSelected = sug.id === activeSuggestion?.id;
                let statusBadge = (
                  <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fcd34d' }}>
                    Pending
                  </span>
                );
                if (sug.status === 'approved') {
                  statusBadge = <span className="badge badge-success">Approved</span>;
                } else if (sug.status === 'rejected') {
                  statusBadge = <span className="badge badge-critical">Rejected</span>;
                }

                return (
                  <div
                    key={sug.id}
                    className={`suggestion-nav-card ${isSelected ? 'active' : ''}`}
                    onClick={() => setActiveSuggestionId(sug.id)}
                  >
                    <div className="suggestion-card-top">
                      <span className={`badge badge-${sug.impact || 'minor'}`}>
                        {sug.impact}
                      </span>
                      {statusBadge}
                    </div>
                    <div className="suggestion-card-title">{sug.ruleId}</div>
                    <div className="suggestion-card-desc">
                      {sug.selector || sug.explanation}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Panel: Editor & Active Suggestion Details */}
          <div className="review-right-panel">
            {/* Monaco Editor Container */}
            <div className="monaco-editor-card">
              <div className="editor-card-header">
                <span className="editor-title">
                  <FiCode style={{ color: 'var(--accent-primary)' }} />
                  Source Code Preview (index.html)
                </span>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Highlighting: {activeSuggestion?.selector || 'DOM Target'}
                </span>
              </div>

              <div className="editor-canvas-wrapper">
                <Editor
                  height="100%"
                  defaultLanguage="html"
                  theme="vs-dark"
                  value={sourceCode}
                  onChange={(val) => setSourceCode(val || '')}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    wordWrap: 'on',
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                  }}
                />
              </div>
            </div>

            {/* AI Suggestion Box */}
            {activeSuggestion && (
              <div className="ai-suggestion-box">
                <div className="suggestion-box-header">
                  <div className="ai-engine-tag">
                    <FiShield style={{ color: 'var(--accent-primary)' }} />
                    <span>AI Remediation Fix: {activeSuggestion.ruleId}</span>
                  </div>

                  <div className="confidence-score-badge">
                    <FiPercent />
                    <span>{activeSuggestion.confidence || 95}% Confidence Score</span>
                  </div>
                </div>

                <p className="explanation-text">
                  {activeSuggestion.explanation}
                </p>

                {/* Fix preview or edit mode */}
                <div className="fix-preview-box">
                  <div className="fix-preview-title">Suggested Accessible Code Replacement</div>
                  {isEditing ? (
                    <div>
                      <textarea
                        value={editingCode}
                        onChange={(e) => setEditingCode(e.target.value)}
                        style={{
                          width: '100%',
                          minHeight: 90,
                          background: '#090914',
                          border: '1px solid var(--accent-primary)',
                          color: '#38e1ff',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.85rem',
                          padding: 10,
                          borderRadius: 4,
                        }}
                      />
                      <div style={{ marginTop: 8, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                        <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '0.8rem' }} onClick={() => setIsEditing(false)}>
                          Cancel
                        </button>
                        <button className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '0.8rem' }} onClick={handleSaveEdit}>
                          <FiSave /> Save Fix
                        </button>
                      </div>
                    </div>
                  ) : (
                    <pre className="code-pre-tag">
                      <code>{activeSuggestion.suggestedCode}</code>
                    </pre>
                  )}
                </div>

                {/* Approve, Reject, Edit Decision Bar */}
                <div className="suggestion-decision-bar">
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    Current Status:{' '}
                    <strong style={{ color: '#fff', textTransform: 'capitalize' }}>
                      {activeSuggestion.status || 'pending'}
                    </strong>
                  </span>

                  <div className="decision-btn-group">
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '8px 14px' }}
                      onClick={handleStartEdit}
                      disabled={isEditing}
                    >
                      <FiEdit2 />
                      <span>Edit Fix</span>
                    </button>

                    <button
                      className="btn btn-reject"
                      style={{ padding: '8px 16px' }}
                      onClick={() => changeSuggestionStatus(activeSuggestion.id, 'rejected')}
                    >
                      <FiX />
                      <span>Reject</span>
                    </button>

                    <button
                      className="btn btn-approve"
                      style={{ padding: '8px 18px' }}
                      onClick={() => changeSuggestionStatus(activeSuggestion.id, 'approved')}
                    >
                      <FiCheck />
                      <span>Approve Fix</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
