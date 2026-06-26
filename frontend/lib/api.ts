// PM Insights — Typed API client
// All backend calls go through here. Never use fetch() directly in components.
// TODO Sprint 1: implement all functions below

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// createApp(payload, token)
// listApps(token)
// triggerRun(appId, payload, token)
// listRuns(appId, token)
// getRunStatus(runId, token)
// getRunArtifacts(runId, token)
// generatePrd(clusterId, token)  ← Sprint 2
