export function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

export function titleCase(value: string) {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

export function severityLabel(severity: string) {
  return `Triage: ${titleCase(severity)}`;
}

export function severityClass(severity: string) {
  if (severity === "critical") return "badge badge-critical";
  if (severity === "high") return "badge badge-high";
  if (severity === "medium") return "badge badge-medium";
  if (severity === "low") return "badge badge-low";
  if (severity === "uncategorized") return "badge badge-uncategorized";
  return "badge";
}
