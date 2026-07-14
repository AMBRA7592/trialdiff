import postgres from "postgres";

let cachedClient: postgres.Sql | null = null;
let cachedClientUrl: string | null = null;

// Astro (Vite) exposes .env-file variables to server code on import.meta.env,
// while hosted runtimes (Vercel) inject them via process.env. Check both so
// `frontend/.env` works under `astro dev` without exporting the variable.
// process.env is consulted first: import.meta.env values are inlined into the
// bundle at build time (verified against the built Vercel function), so a
// runtime environment variable must win over a potentially stale baked value.
function readEnv(name: string): string | undefined {
  const fromProcess = process.env[name];
  if (typeof fromProcess === "string" && fromProcess.length > 0) {
    return fromProcess;
  }
  const fromImportMeta = (import.meta.env as Record<string, unknown>)[name];
  return typeof fromImportMeta === "string" && fromImportMeta.length > 0 ? fromImportMeta : undefined;
}

function databaseUrl(): string | undefined {
  return readEnv("DATABASE_URL");
}

function poolMax(): number {
  const raw = readEnv("DATABASE_POOL_MAX");
  const parsed = raw === undefined ? Number.NaN : Number.parseInt(raw, 10);
  if (Number.isFinite(parsed) && parsed >= 1) return parsed;
  return 5;
}

export function hasDatabaseUrl() {
  return Boolean(databaseUrl());
}

export function getSql() {
  const url = databaseUrl();
  if (!url) {
    throw new Error("DATABASE_URL is not configured");
  }

  if (!cachedClient || cachedClientUrl !== url) {
    const options: postgres.Options<{}> = {
      connect_timeout: 10,
      idle_timeout: 20,
      max: poolMax(),
      prepare: false,
    };
    // If the connection string carries an explicit sslmode (Neon URLs do,
    // local URLs use sslmode=disable), let postgres.js honor it. Only default
    // to TLS when the URL says nothing about ssl.
    if (!/[?&]sslmode=/.test(url)) {
      options.ssl = "require";
    }
    cachedClient = postgres(url, options);
    cachedClientUrl = url;
  }

  return cachedClient;
}
