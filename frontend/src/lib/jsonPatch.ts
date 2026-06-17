export const MISSING = Symbol("missing");

export type MissingValue = typeof MISSING;

export type PatchOperation = {
  op: string;
  path: string;
  value?: unknown;
  from?: string;
};

export type PatchValueContext = {
  index: number;
  op: string;
  path: string;
  oldValue: unknown | MissingValue;
  newValue: unknown | MissingValue;
};

export function isMissing(value: unknown): value is MissingValue {
  return value === MISSING;
}

export function parsePointer(pointer: string): string[] {
  if (pointer === "") return [];
  if (!pointer.startsWith("/")) return [];
  return pointer
    .slice(1)
    .split("/")
    .map((part) => part.replaceAll("~1", "/").replaceAll("~0", "~"));
}

export function resolvePointer(document: unknown, pointer: string, defaultValue: unknown = MISSING): unknown {
  let current = document;
  for (const part of parsePointer(pointer)) {
    if (Array.isArray(current)) {
      if (part === "-") return defaultValue;
      const index = Number(part);
      if (!Number.isInteger(index) || index < 0 || index >= current.length) return defaultValue;
      current = current[index];
    } else if (isRecord(current)) {
      if (!(part in current)) return defaultValue;
      current = current[part];
    } else {
      return defaultValue;
    }
  }
  return current;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function parentAndKey(document: unknown, pointer: string): { parent: unknown; key: string } | null {
  const parts = parsePointer(pointer);
  if (parts.length === 0) return null;
  let parent = document;
  for (const part of parts.slice(0, -1)) {
    if (Array.isArray(parent)) {
      const index = Number(part);
      if (!Number.isInteger(index)) return null;
      parent = parent[index];
    } else if (isRecord(parent)) {
      parent = parent[part];
    } else {
      return null;
    }
  }
  return { parent, key: parts[parts.length - 1] };
}

function applySinglePatch(document: unknown, operation: PatchOperation): void {
  const location = parentAndKey(document, operation.path);
  if (!location) return;

  const { parent, key } = location;
  if (operation.op === "replace") {
    if (Array.isArray(parent)) {
      parent[Number(key)] = operation.value;
    } else if (isRecord(parent)) {
      parent[key] = operation.value;
    }
  } else if (operation.op === "add") {
    if (Array.isArray(parent)) {
      if (key === "-") parent.push(operation.value);
      else parent.splice(Number(key), 0, operation.value);
    } else if (isRecord(parent)) {
      parent[key] = operation.value;
    }
  } else if (operation.op === "remove") {
    if (Array.isArray(parent)) {
      parent.splice(Number(key), 1);
    } else if (isRecord(parent)) {
      delete parent[key];
    }
  }
}

export function buildValueContexts(
  fromDocument: unknown,
  operations: PatchOperation[],
): PatchValueContext[] {
  const working = cloneJson(fromDocument);
  const contexts: PatchValueContext[] = [];

  operations.forEach((operation, index) => {
    const oldValue = resolvePointer(working, operation.path);
    applySinglePatch(working, operation);
    const newValue = operation.op === "remove" ? MISSING : resolvePointer(working, operation.path);
    contexts.push({
      index,
      op: operation.op,
      path: operation.path,
      oldValue: oldValue as unknown | MissingValue,
      newValue: newValue as unknown | MissingValue,
    });
  });

  return contexts;
}
