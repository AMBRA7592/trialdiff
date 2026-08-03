import type { APIRoute } from "astro";

import { getEvidenceSupersessionIndex } from "@/queries/evidence";

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };

export const GET: APIRoute = async () => {
  const data = await getEvidenceSupersessionIndex();
  if (!data.databaseReady) {
    return new Response(JSON.stringify({ error: "Evidence database unavailable. Try again shortly." }), {
      status: 503,
      headers: { ...JSON_HEADERS, "cache-control": "no-store" },
    });
  }

  const activeGeneration = data.entries.find((entry) => entry.isActiveGeneration)?.packageGeneration ?? null;
  const body = JSON.stringify({
    schema: "trialdiff.evidence_supersession_index",
    active_package_generation: activeGeneration,
    records: data.entries.map((entry) => ({
      event_id: entry.eventId,
      package_generation: entry.packageGeneration,
      status: entry.successorEventId ? "superseded" : entry.isActiveGeneration ? "current" : "inactive",
      successor_event_id: entry.successorEventId,
      predecessor_event_id: entry.predecessorEventId,
    })),
  });

  return new Response(body, {
    status: 200,
    headers: {
      ...JSON_HEADERS,
      "cache-control": "public, max-age=0, must-revalidate",
    },
  });
};
