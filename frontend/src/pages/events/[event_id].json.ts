import type { APIRoute } from "astro";

import { getEvidenceCanonical } from "@/queries/evidence";

// Evidence records are immutable and hash-addressed: canonical_json is stored
// as text (migration 006) whose exact bytes hash to canonical_hash. Serve
// those bytes verbatim — any re-encode (JSON.stringify round-trip, pretty
// print) would break `sha256(body) == canonical_hash` verification.

function etagMatches(ifNoneMatch: string | null, etag: string): boolean {
  if (!ifNoneMatch) return false;
  if (ifNoneMatch.trim() === "*") return true;
  return ifNoneMatch
    .split(",")
    .map((candidate) => candidate.trim().replace(/^W\//, ""))
    .includes(etag);
}

export const GET: APIRoute = async ({ params, request }) => {
  const eventId = String(params.event_id ?? "");
  const data = await getEvidenceCanonical(eventId);

  if (!data.databaseReady) {
    return new Response(JSON.stringify({ error: "Evidence database unavailable. Try again shortly." }), {
      status: 503,
      headers: { "content-type": "application/json; charset=utf-8" },
    });
  }

  if (data.canonicalText === undefined) {
    return new Response(JSON.stringify({ error: "Evidence Record not found." }), {
      status: 404,
      headers: { "content-type": "application/json; charset=utf-8" },
    });
  }

  const canonicalHash = data.canonicalHash ?? "";

  if (!data.canonicalVerifiable) {
    // Legacy jsonb rows arrive as parsed objects; the original canonical
    // bytes are gone, so serve a compact re-encode and say so. No immutable
    // caching and no hash-derived ETag for a body that is not the hashed bytes.
    return new Response(data.canonicalText, {
      status: 200,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "public, s-maxage=3600",
        "x-trialdiff-canonical-hash": canonicalHash,
        "x-trialdiff-canonical-verified": "false",
      },
    });
  }

  const etag = `"${canonicalHash}"`;
  const headers = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "public, max-age=31536000, immutable",
    etag,
    "x-trialdiff-canonical-hash": canonicalHash,
  };

  if (etagMatches(request.headers.get("if-none-match"), etag)) {
    return new Response(null, { status: 304, headers });
  }

  return new Response(data.canonicalText, { status: 200, headers });
};
