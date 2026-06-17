import type { APIRoute } from "astro";

import { getEvidenceCanonical } from "@/queries/evidence";

export const GET: APIRoute = async ({ params }) => {
  const eventId = String(params.event_id ?? "");
  const data = await getEvidenceCanonical(eventId);

  if (!data.databaseReady) {
    return new Response(
      JSON.stringify({ error: data.databaseError ?? "Database connection pending." }),
      {
        status: 503,
        headers: { "content-type": "application/json; charset=utf-8" },
      },
    );
  }

  if (!data.canonicalJson) {
    return new Response(JSON.stringify({ error: "Evidence Record not found." }), {
      status: 404,
      headers: { "content-type": "application/json; charset=utf-8" },
    });
  }

  return new Response(JSON.stringify(data.canonicalJson, null, 2), {
    status: 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "x-trialdiff-canonical-hash": data.canonicalHash ?? "",
    },
  });
};
