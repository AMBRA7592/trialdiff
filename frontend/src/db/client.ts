import postgres from "postgres";

let cachedClient: postgres.Sql | null = null;

export function hasDatabaseUrl() {
  return Boolean(process.env.DATABASE_URL);
}

export function getSql() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is not configured");
  }

  if (!cachedClient) {
    cachedClient = postgres(process.env.DATABASE_URL, {
      connect_timeout: 10,
      idle_timeout: 20,
      max: 1,
      prepare: false,
      ssl: "require",
    });
  }

  return cachedClient;
}
