import { useState, useEffect, useCallback } from 'react';
import {
  getScan,
  getScanIssues,
  getSuggestions,
  updateSuggestion,
  analyzeIssues,
  getProjects,
  createProject,
} from '../services/api';
import { toast } from 'react-toastify';

/**
 * Hook to manage scan details
 */
export function useScan(scanId) {
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchScan = useCallback(async () => {
    if (!scanId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getScan(scanId);
      setScan(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch scan details');
      toast.error('Failed to load scan details');
    } finally {
      setLoading(false);
    }
  }, [scanId]);

  useEffect(() => {
    fetchScan();
  }, [fetchScan]);

  return { scan, loading, error, refetch: fetchScan };
}

/**
 * Hook to manage scan issues with filtering and pagination
 */
export function useIssues(scanId) {
  const [rawIssues, setRawIssues] = useState([]);
  const [filteredIssues, setFilteredIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [impactFilter, setImpactFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 5;

  const fetchIssues = useCallback(async () => {
    if (!scanId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await getScanIssues(scanId);
      const list = response.issues || (Array.isArray(response) ? response : []);
      setRawIssues(list);
    } catch (err) {
      setError(err.message || 'Failed to fetch scan issues');
      toast.error('Could not load accessibility issues');
    } finally {
      setLoading(false);
    }
  }, [scanId]);

  useEffect(() => {
    fetchIssues();
  }, [fetchIssues]);

  // Apply filters whenever issues, impactFilter, or searchQuery change
  useEffect(() => {
    let result = [...rawIssues];

    if (impactFilter !== 'all') {
      result = result.filter(
        (issue) => (issue.impact || '').toLowerCase() === impactFilter.toLowerCase()
      );
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (issue) =>
          (issue.ruleId && issue.ruleId.toLowerCase().includes(query)) ||
          (issue.description && issue.description.toLowerCase().includes(query)) ||
          (issue.selector && issue.selector.toLowerCase().includes(query)) ||
          (issue.wcagTags && issue.wcagTags.some((tag) => tag.toLowerCase().includes(query)))
      );
    }

    setFilteredIssues(result);
    setCurrentPage(1); // Reset to page 1 on filter change
  }, [rawIssues, impactFilter, searchQuery]);

  // Paginated slice
  const paginatedIssues = filteredIssues.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const totalPages = Math.max(1, Math.ceil(filteredIssues.length / pageSize));

  return {
    issues: paginatedIssues,
    allFilteredCount: filteredIssues.length,
    totalRawCount: rawIssues.length,
    loading,
    error,
    impactFilter,
    setImpactFilter,
    searchQuery,
    setSearchQuery,
    currentPage,
    setCurrentPage,
    totalPages,
    refetch: fetchIssues,
  };
}

/**
 * Hook to manage AI Suggestions and review workflow
 */
export function useSuggestions(scanId) {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  const fetchSuggestions = useCallback(async () => {
    if (!scanId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getSuggestions(scanId);
      const list = data.suggestions || (Array.isArray(data) ? data : []);
      setSuggestions(list);
    } catch (err) {
      setError(err.message || 'Failed to load suggestions');
    } finally {
      setLoading(false);
    }
  }, [scanId]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  const changeSuggestionStatus = async (suggestionId, newStatus) => {
    try {
      await updateSuggestion(suggestionId, { status: newStatus });
      setSuggestions((prev) =>
        prev.map((item) =>
          item.id === suggestionId ? { ...item, status: newStatus } : item
        )
      );
      toast.success(`Fix marked as ${newStatus}`);
    } catch (err) {
      toast.error('Failed to update suggestion status');
    }
  };

  const runAnalysis = async () => {
    setAnalyzing(true);
    try {
      const result = await analyzeIssues(scanId);
      if (result.suggestions) {
        setSuggestions(result.suggestions);
      } else {
        await fetchSuggestions();
      }
      toast.success('AI Analysis finished: Generated fixes ready for review');
    } catch (err) {
      toast.error('Failed to run AI analysis');
    } finally {
      setAnalyzing(false);
    }
  };

  return {
    suggestions,
    loading,
    error,
    analyzing,
    changeSuggestionStatus,
    runAnalysis,
    refetch: fetchSuggestions,
  };
}

/**
 * Hook to manage projects
 */
export function useProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getProjects();
      setProjects(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const addProject = async (projectData) => {
    try {
      const created = await createProject(projectData);
      setProjects((prev) => [created, ...prev]);
      toast.success('Project created successfully');
      return created;
    } catch (err) {
      toast.error('Failed to create project');
      throw err;
    }
  };

  return { projects, loading, error, addProject, refetch: fetchProjects };
}
