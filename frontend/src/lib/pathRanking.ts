// Ranks changed paths so short previews (slice(0, 2)) surface signal paths
// before administrative registry-maintenance noise.
//
// The suppression set mirrors the Python classifier's review-metadata
// suppression (trialdiff/classifier/materiality.py: suppress_review_metadata_rules
// drops any path containing "/reviewUnit"), plus registry bookkeeping sections
// and statusModule submit/post/verify date fields that never carry review
// signal on their own.

const ADMINISTRATIVE_SECTION_PREFIXES = [
  "/annotationSection",
  "/documentSection",
  "/derivedSection",
];

const ADMINISTRATIVE_STATUS_MODULE_FIELDS = [
  "/protocolSection/statusModule/statusVerifiedDate",
  "/protocolSection/statusModule/lastUpdateSubmitDate",
  "/protocolSection/statusModule/lastUpdatePostDateStruct",
  "/protocolSection/statusModule/studyFirstSubmitDate",
  "/protocolSection/statusModule/studyFirstSubmitQcDate",
  "/protocolSection/statusModule/studyFirstPostDateStruct",
  "/protocolSection/statusModule/resultsFirstSubmitDate",
  "/protocolSection/statusModule/resultsFirstSubmitQcDate",
  "/protocolSection/statusModule/resultsFirstPostDateStruct",
  "/protocolSection/statusModule/dispFirstSubmitDate",
  "/protocolSection/statusModule/dispFirstSubmitQcDate",
  "/protocolSection/statusModule/dispFirstPostDateStruct",
];

function matchesPrefix(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`);
}

export function isAdministrativePath(path: string): boolean {
  // Mirror of trialdiff/classifier/materiality.py is_review_metadata_path().
  if (path.includes("/reviewUnit")) return true;
  if (ADMINISTRATIVE_SECTION_PREFIXES.some((prefix) => matchesPrefix(path, prefix))) return true;
  return ADMINISTRATIVE_STATUS_MODULE_FIELDS.some((prefix) => matchesPrefix(path, prefix));
}

// Stable partition: signal paths first, administrative paths last, preserving
// the original relative order inside each group.
export function rankChangedPaths(paths: string[]): string[] {
  const signal: string[] = [];
  const administrative: string[] = [];
  for (const path of paths) {
    (isAdministrativePath(path) ? administrative : signal).push(path);
  }
  return [...signal, ...administrative];
}
