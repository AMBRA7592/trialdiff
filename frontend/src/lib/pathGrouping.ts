import type { Severity } from "./pathMatching";
import { maxSeverity, pointerHasPrefix } from "./pathMatching";
import type { EnrichedPatchOperation } from "./patchEnrichment";

export type OperationGroup = {
  key: string;
  label: string;
  description: string;
  defaultOpen: boolean;
  severity: Severity;
  operations: EnrichedPatchOperation[];
};

type GroupDefinition = {
  key: string;
  label: string;
  description: string;
  defaultOpen: boolean;
  prefixes: string[];
};

const GROUPS: GroupDefinition[] = [
  {
    key: "primary-outcomes",
    label: "Primary outcomes",
    description: "Outcome measures that define the trial's primary evidence target.",
    defaultOpen: true,
    prefixes: ["/protocolSection/outcomesModule/primaryOutcomes"],
  },
  {
    key: "secondary-outcomes",
    label: "Secondary outcomes",
    description: "Additional endpoints and outcome descriptions.",
    defaultOpen: true,
    prefixes: ["/protocolSection/outcomesModule/secondaryOutcomes"],
  },
  {
    key: "results-outcomes",
    label: "Results outcome measures",
    description: "Posted result outcome measures and result-level endpoint data.",
    defaultOpen: true,
    prefixes: ["/resultsSection/outcomeMeasuresModule"],
  },
  {
    key: "design",
    label: "Design",
    description: "Trial model, phase, allocation, masking, arms, or interventions.",
    defaultOpen: true,
    prefixes: ["/protocolSection/designModule", "/protocolSection/armsInterventionsModule"],
  },
  {
    key: "eligibility",
    label: "Eligibility",
    description: "Criteria and population definition changes.",
    defaultOpen: true,
    prefixes: ["/protocolSection/eligibilityModule"],
  },
  {
    key: "status",
    label: "Status and stopping reason",
    description: "Recruitment status, termination, suspension, withdrawal, or why-stopped text.",
    defaultOpen: true,
    prefixes: ["/protocolSection/statusModule/overallStatus", "/protocolSection/statusModule/whyStopped"],
  },
  {
    key: "timeline",
    label: "Timeline",
    description: "Start, primary completion, and completion date movement.",
    defaultOpen: true,
    prefixes: [
      "/protocolSection/statusModule/startDateStruct",
      "/protocolSection/statusModule/primaryCompletionDateStruct",
      "/protocolSection/statusModule/completionDateStruct",
    ],
  },
  {
    key: "safety",
    label: "Adverse events and safety",
    description: "Posted serious or other adverse event data.",
    defaultOpen: true,
    prefixes: ["/resultsSection/adverseEventsModule"],
  },
  {
    key: "contacts-locations",
    label: "Contacts and locations",
    description: "Site, contact, and location updates that are usually operational.",
    defaultOpen: false,
    prefixes: ["/protocolSection/contactsLocationsModule"],
  },
  {
    key: "sponsor-admin",
    label: "Sponsor and administrative fields",
    description: "Sponsor, collaborator, oversight, or registry maintenance changes.",
    defaultOpen: false,
    prefixes: [
      "/protocolSection/sponsorCollaboratorsModule",
      "/protocolSection/oversightModule",
      "/protocolSection/referencesModule",
      "/protocolSection/identificationModule",
    ],
  },
];

export function groupOperations(operations: EnrichedPatchOperation[]): OperationGroup[] {
  const groups = new Map<string, OperationGroup>();

  for (const operation of operations) {
    const definition = groupDefinitionForPath(operation.path);
    const group = groups.get(definition.key) ?? {
      key: definition.key,
      label: definition.label,
      description: definition.description,
      defaultOpen: definition.defaultOpen,
      severity: "uncategorized",
      operations: [],
    };

    group.operations.push(operation);
    group.severity = maxSeverity(group.operations.map((item) => item.severity));
    groups.set(definition.key, group);
  }

  return Array.from(groups.values()).sort((left, right) => {
    const severityDelta = severitySortValue(right.severity) - severitySortValue(left.severity);
    if (severityDelta !== 0) return severityDelta;
    return left.label.localeCompare(right.label);
  });
}

function groupDefinitionForPath(path: string): GroupDefinition {
  return (
    GROUPS.find((group) => group.prefixes.some((prefix) => pointerHasPrefix(path, prefix))) ?? {
      key: "other",
      label: "Other registry fields",
      description: "Changes outside the current high-signal rule families.",
      defaultOpen: false,
      prefixes: [],
    }
  );
}

function severitySortValue(severity: Severity) {
  if (severity === "critical") return 5;
  if (severity === "high") return 4;
  if (severity === "medium") return 3;
  if (severity === "low") return 2;
  if (severity === "uncategorized") return 1;
  return 0;
}
