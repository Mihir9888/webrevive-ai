import React from 'react';
import {
  FiAlertCircle,
  FiAlertTriangle,
  FiInfo,
  FiCheckCircle,
  FiHelpCircle
} from 'react-icons/fi';

/**
 * Format a date timestamp into human-readable string
 * @param {string|number|Date} date
 * @returns {string}
 */
export function formatDate(date) {
  if (!date) return 'N/A';
  try {
    const d = new Date(date);
    if (isNaN(d.getTime())) return String(date);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(d);
  } catch {
    return String(date);
  }
}

/**
 * Return CSS color variable or hex for an impact level
 * @param {string} impact - 'critical' | 'serious' | 'moderate' | 'minor'
 * @returns {string}
 */
export function getImpactColor(impact) {
  switch ((impact || '').toLowerCase()) {
    case 'critical':
      return '#ef4444'; // Red
    case 'serious':
      return '#f59e0b'; // Amber / Orange
    case 'moderate':
      return '#7c3aed'; // Purple
    case 'minor':
      return '#00d4ff'; // Cyan
    case 'success':
    case 'passed':
      return '#10b981'; // Green
    default:
      return '#a0a0b0'; // Gray
  }
}

/**
 * Return a corresponding React Icon component for impact
 * @param {string} impact
 * @returns {JSX.Element}
 */
export function getImpactIcon(impact) {
  const norm = (impact || '').toLowerCase();
  switch (norm) {
    case 'critical':
      return React.createElement(FiAlertCircle, { style: { color: '#ef4444' } });
    case 'serious':
      return React.createElement(FiAlertTriangle, { style: { color: '#f59e0b' } });
    case 'moderate':
      return React.createElement(FiInfo, { style: { color: '#a78bfa' } });
    case 'minor':
      return React.createElement(FiInfo, { style: { color: '#00d4ff' } });
    case 'success':
    case 'passed':
      return React.createElement(FiCheckCircle, { style: { color: '#10b981' } });
    default:
      return React.createElement(FiHelpCircle, { style: { color: '#a0a0b0' } });
  }
}

/**
 * Truncate long strings with ellipsis
 * @param {string} text
 * @param {number} maxLength
 * @returns {string}
 */
export function truncateText(text, maxLength = 60) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Calculate an accessibility / WCAG compliance score from 0 to 100
 * Weighted formula:
 * critical: -15 pts
 * serious: -8 pts
 * moderate: -4 pts
 * minor: -1 pt
 * @param {Array} issues
 * @returns {number} 0-100
 */
export function calculateComplianceScore(issues = []) {
  if (!Array.isArray(issues)) return 100;
  if (issues.length === 0) return 100;

  let deduction = 0;
  for (const issue of issues) {
    const impact = (issue.impact || issue.severity || '').toLowerCase();
    if (impact === 'critical') deduction += 15;
    else if (impact === 'serious') deduction += 8;
    else if (impact === 'moderate') deduction += 4;
    else if (impact === 'minor') deduction += 1.5;
    else deduction += 2;
  }

  const score = Math.max(10, Math.round(100 - deduction));
  return score;
}

/**
 * Group list of issues by impact level
 * @param {Array} issues
 * @returns {{ critical: Array, serious: Array, moderate: Array, minor: Array, other: Array }}
 */
export function groupIssuesByImpact(issues = []) {
  const grouped = {
    critical: [],
    serious: [],
    moderate: [],
    minor: [],
    other: [],
  };

  if (!Array.isArray(issues)) return grouped;

  for (const issue of issues) {
    const impact = (issue.impact || issue.severity || '').toLowerCase();
    if (grouped[impact]) {
      grouped[impact].push(issue);
    } else {
      grouped.other.push(issue);
    }
  }

  return grouped;
}

/**
 * Trigger browser file download of JSON object
 * @param {object} data
 * @param {string} filename
 */
export function downloadJSON(data, filename = 'webrevive-report.json') {
  try {
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('Error downloading JSON:', err);
  }
}
