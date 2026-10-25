export interface Source {
  id: string; url: string; sha256: string; role: string;
  observed_contract: Record<string, string | number | number[]>;
}
export interface Workspace {
  read_only?: boolean;
  live_configured: boolean; local_only: boolean; model: string; recorded_run_id: string;
  experiment_worker_ready: boolean;
  maximum_inference_requests: number; default_output_cap: number;
  sources: { sources: Source[]; comparison_limit: string };
}
export interface RunItem {
  adapter?: string;
  provider_mode?: string;
  id: string; kind: 'recorded' | 'live'; created_at: string; state: string; phase: string;
}
export interface Plan {
  case_id: string; hypothesis: string; predict_gate_difference: boolean; predict_miss_difference: boolean;
}
export interface Evidence {
  case_id: string; evidence_id: string; input_sha256: string; source_protocol_sha256: string;
  profiles: { history_refresh: string; misses: number; gate_credits: number }[];
  scope: string;
}
export interface Attempt {
  number: number; state: 'planned' | 'rejected' | 'measured'; plan: Plan; capacity: number; request_count: number;
  preflight: null | { accepted: boolean; reasons: { reason: string; explanation: string; maximum_gate_threshold?: number }[] };
  evidence: Evidence | null; predictions_correct: boolean | null;
  execution: null | { mode: string; image_id: string; policy: Record<string, unknown>; evidence_id: string };
}
export interface EvidenceReport {
  version: string; producer: string; outcome: string; summary: string; measured_tests: number;
  model_inference_used_for_report: boolean; report_sha256: string; rejected_tests: string[];
  measurements: { test_id: string; evidence_id: string; input_sha256: string;
    metrics: Record<string, { left: number; right: number }>; differing_metrics: string[] }[];
  scope: { full_report_disagreement_explained: boolean; asymptotic_claim_adjudicated: boolean };
}
export interface Investigation extends RunItem {
  provider_mode: string;
  error: string | null; model: string; workflow_version: string; status: string; review_reason: string | null;
  attempts: Attempt[]; finding: { next_action: string; scope: string } | null;
  model_finding: unknown | null; evidence_report: EvidenceReport; report_origin: string;
  finding_checks: Record<string, boolean> | null;
  usage: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
  inference_requests: number; elapsed_seconds: number | null; export_available: boolean; limits: string[];
  protocol: { sha256: string; seed: number; tau: number; changed_factor: string; held_fixed: string[];
              cases: { case_id: string; capacity: number; request_count: number; requests: number[]; supplied_predictions: number[] }[];
              maximum_inference_requests: number; max_output_tokens: number };
  provenance: { manifest_verified: boolean; protocol_verified: boolean; numerical_replay_verified: boolean; report_replay_verified: boolean; evidence_ids: string[] };
}
