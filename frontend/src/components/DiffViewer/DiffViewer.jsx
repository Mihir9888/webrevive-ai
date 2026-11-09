import React, { useState } from 'react';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';
import { FiColumns, FiMaximize2, FiMinimize2, FiCode } from 'react-icons/fi';
import './DiffViewer.css';

const darkStyles = {
  variables: {
    dark: {
      diffViewerBackground: '#0d1117',
      diffViewerColor: '#c9d1d9',
      addedBackground: 'rgba(16, 185, 129, 0.15)',
      addedColor: '#7ee787',
      removedBackground: 'rgba(239, 68, 68, 0.15)',
      removedColor: '#ffa198',
      wordAddedBackground: 'rgba(16, 185, 129, 0.35)',
      wordRemovedBackground: 'rgba(239, 68, 68, 0.35)',
      addedGutterBackground: 'rgba(16, 185, 129, 0.2)',
      removedGutterBackground: 'rgba(239, 68, 68, 0.2)',
      gutterBackground: '#161b22',
      gutterBackgroundDark: '#161b22',
      highlightBackground: '#2a2a4a',
      highlightGutterBackground: '#2a2a4a',
      codeFoldGutterBackground: '#1f242c',
      codeFoldBackground: '#161b22',
      emptyLineBackground: '#0d1117',
      gutterColor: '#6e7681',
      addedGutterColor: '#7ee787',
      removedGutterColor: '#ffa198',
    },
  },
  line: {
    padding: '3px 8px',
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: '13px',
  },
  gutter: {
    padding: '0 10px',
  },
};

export default function DiffViewer({
  originalCode = '',
  modifiedCode = '',
  language = 'html',
  title = 'Code Remediation Diff',
}) {
  const [splitView, setSplitView] = useState(true);

  return (
    <div className="diff-viewer-container">
      <div className="diff-header-bar">
        <div className="diff-title">
          <FiCode style={{ color: 'var(--accent-primary)' }} />
          <span>{title}</span>
        </div>

        <div className="diff-controls">
          <div className="diff-legend">
            <span className="legend-item">
              <span className="legend-dot removed" />
              <span>Original Violations</span>
            </span>
            <span className="legend-item">
              <span className="legend-dot added" />
              <span>AI Remediation</span>
            </span>
          </div>

          <div className="diff-view-toggle">
            <button
              className={`diff-toggle-btn ${splitView ? 'active' : ''}`}
              onClick={() => setSplitView(true)}
            >
              Split View
            </button>
            <button
              className={`diff-toggle-btn ${!splitView ? 'active' : ''}`}
              onClick={() => setSplitView(false)}
            >
              Unified
            </button>
          </div>
        </div>
      </div>

      <div className="diff-content-wrapper">
        <ReactDiffViewer
          oldValue={originalCode}
          newValue={modifiedCode}
          splitView={splitView}
          useDarkTheme={true}
          styles={darkStyles}
          compareMethod={DiffMethod.WORDS}
          leftTitle="Original (Inaccessible Source)"
          rightTitle="Refactored (Accessible DOM / ARIA)"
          showDiffOnly={false}
        />
      </div>
    </div>
  );
}
