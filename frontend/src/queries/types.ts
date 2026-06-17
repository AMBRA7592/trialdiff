export type Lens = "post-completion" | "recent" | "critical-density" | "amendment-intensity";

export type SummaryCounts = {
  trialCount: number;
  patchCount: number;
  materialEventCount: number;
  criticalCount: number;
  highCount: number;
};

export type SeverityCount = {
  severity: string;
  count: number;
};

export type EventRow = {
  id: number;
  evidenceEventId?: string | null;
  nctId: string;
  briefTitle: string | null;
  leadSponsor: string | null;
  fromVersion: number;
  toVersion: number;
  submittedDate: string | null;
  severity: string;
  severityPreTiming: string;
  timingContext: string | null;
  category: string;
  categories: string[];
  changedPaths: string[];
  needsHumanReview: boolean;
};

export type EvidenceRecordRow = {
  eventId: string;
  nctId: string;
  briefTitle: string | null;
  leadSponsor: string | null;
  fromVersion: number;
  toVersion: number;
  submittedDate: string | null;
  timingContext: string | null;
  severityPreTiming: string;
  severity: string;
  category: string;
  categories: string[];
  changedPaths: string[];
  deterministicRules: string[];
  claimsSupported: string[];
  claimsNotSupported: string[];
  reviewQuestion: string;
  evidenceVersion: number;
  canonicalHash: string;
};

export type TrialLensRow = {
  nctId: string;
  briefTitle: string | null;
  leadSponsor: string | null;
  patchCount: number;
  eventCount: number;
  criticalCount: number;
  highCount: number;
  criticalDensityPct: number;
  latestEventDate: string | null;
};

export type HomeData = {
  databaseReady: boolean;
  databaseError?: string;
  summary: SummaryCounts;
  severityCounts: SeverityCount[];
  postCompletionEvidenceRecords: EvidenceRecordRow[];
  recentEvents: EventRow[];
  criticalDensityTrials: TrialLensRow[];
  amendmentIntensityTrials: TrialLensRow[];
};

export type TrialDetailData = {
  databaseReady: boolean;
  databaseError?: string;
  trial?: {
    nctId: string;
    briefTitle: string | null;
    officialTitle: string | null;
    leadSponsor: string | null;
    overallStatus: string | null;
    lastUpdatePosted: string | null;
    hasResults: boolean;
  };
  patchCount: number;
  versionCount: number;
  events: EventRow[];
};

export type EvidenceRecordDetail = EvidenceRecordRow & {
  valueSignals: Record<string, unknown>[];
  citationText: string;
  canonicalJson: Record<string, unknown>;
  patchHash: string;
  patchSource: string;
  patchSourceUrl: string | null;
  patchRawHash: string;
  fromSnapshotHash: string | null;
  toSnapshotHash: string | null;
  materialityEventHash: string;
  ruleSetHash: string;
  source: string;
  sourceUrl: string;
  generatedAt: string | null;
  trial?: {
    overallStatus: string | null;
    hasResults: boolean;
  };
};

export type EvidenceRecordData = {
  databaseReady: boolean;
  databaseError?: string;
  record?: EvidenceRecordDetail;
};

export type EvidenceCanonicalData = {
  databaseReady: boolean;
  databaseError?: string;
  canonicalJson?: Record<string, unknown>;
  canonicalHash?: string;
};
