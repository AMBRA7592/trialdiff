export type Severity = "ignore" | "low" | "medium" | "high" | "critical" | "uncategorized";

export type ClassifierRule = {
  ruleKey: string;
  pathPattern: string;
  opFilter: string[];
  valueFilter: Record<string, unknown>;
  severity: Exclude<Severity, "uncategorized">;
  category: string;
  timingSensitive: boolean;
  description: string;
};

export type PatchOperationContext = {
  op: string;
  path: string;
  oldValue: unknown;
  newValue: unknown;
};

export const severityRank: Record<Severity, number> = {
  ignore: 0,
  uncategorized: 0,
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

export function parsePointer(pointer: string): string[] {
  if (pointer === "") return [];
  if (!pointer.startsWith("/")) return [];
  return pointer
    .slice(1)
    .split("/")
    .map((part) => part.replaceAll("~1", "/").replaceAll("~0", "~"));
}

export function matchPath(pattern: string, path: string): boolean {
  return matchParts(parsePointer(pattern), parsePointer(path));
}

function matchParts(patternParts: string[], pathParts: string[]): boolean {
  if (patternParts.length === 0) return pathParts.length === 0;

  const [head, ...tail] = patternParts;
  if (head === "**") {
    if (tail.length === 0) return true;
    for (let index = 0; index <= pathParts.length; index += 1) {
      if (matchParts(tail, pathParts.slice(index))) return true;
    }
    return false;
  }

  if (pathParts.length === 0) return false;
  if (head === "*" || head === pathParts[0]) {
    return matchParts(tail, pathParts.slice(1));
  }
  return false;
}

export function ruleMatchesOperation(rule: ClassifierRule, operation: PatchOperationContext): boolean {
  if (rule.opFilter.length > 0 && !rule.opFilter.includes(operation.op)) return false;
  if (!matchPath(rule.pathPattern, operation.path)) return false;

  const inValues = rule.valueFilter.in;
  if (Array.isArray(inValues)) {
    return inValues.includes(operation.newValue);
  }

  return true;
}

export function matchingRulesForOperation(
  operation: PatchOperationContext,
  rules: ClassifierRule[],
): ClassifierRule[] {
  return rules.filter((rule) => ruleMatchesOperation(rule, operation));
}

export function maxSeverity(severities: Severity[]): Severity {
  let best: Severity = "uncategorized";
  for (const severity of severities) {
    if (severityRank[severity] > severityRank[best]) {
      best = severity;
    }
  }
  return best;
}

// Shared JSON-pointer prefix predicate: true when `path` IS `prefix` or is
// nested under it. Segment-aware (avoids matching lookalike segments that
// merely start with the prefix text).
export function pointerHasPrefix(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`);
}
