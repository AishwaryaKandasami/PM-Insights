// PM Insights — Domain types
// These mirror .cursorrules Section 5 exactly.
// Do not rename or abbreviate field names.

// TODO Sprint 1: implement full type definitions

export type RunStatus = 'pending' | 'processing' | 'complete' | 'failed';

export type AtomType = 'bug' | 'feature_request' | 'sentiment' | 'ux_issue';

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export type ArtifactType =
  | 'bug_triage_matrix'
  | 'feature_backlog'
  | 'rice_table'
  | 'executive_summary'
  | 'prd_draft';

export interface ApiResponse<T> {
  data: T | null;
  error: { code: string; message: string } | null;
  meta: { request_id: string; timestamp: string };
}

// App, Run, Atom, Cluster, Artifact — implement in Sprint 1
