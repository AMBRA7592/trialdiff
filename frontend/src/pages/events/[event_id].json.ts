import { createHash } from "node:crypto";

import type { APIRoute } from "astro";

import { getEvidenceCanonical, getEvidenceCanonicalHash } from "@/queries/evidence";

// Evidence records are immutable and hash-addressed: canonical_json stores
// the exact bytes that hash to canonical_hash (migration 006 + re-import).
// This endpoint serves those bytes verbatim and REFUSES to serve a body it
// cannot verify: sha256(body) is recomputed on every miss and compared to
// the stored hash, so a half-done migration (006 applied without the
// re-import, leaving jsonb re-serializations behind) fails loudly instead
// of poisoning immutable caches with unverifiable bytes.

function etagMatches(ifNoneMatch: string | null, etag: string): boolean {
  if (!ifNoneMatch) return false;
  return ifNoneMatch
    .split(",")
    .map((candidate) => candidate.trim().replace(/^W\//, ""))
    .includes(etag);
}

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };

export const GET: APIRoute = async ({ params, request }) => {
  const eventId = String(params.event_id ?? "");

  // Conditional requests are answered from the hash column alone — no need
  // to transfer a potentially multi-megabyte body to return a 304.
  const ifNoneMatch = request.headers.get("if-none-match");
  if (ifNoneMatch) {
    const head = await getEvidenceCanonicalHash(eventId);
    if (head.databaseReady && head.canonicalHash) {
      const etag = `"${head.canonicalHash}"`;
      if (etagMatches(ifNoneMatch, etag)) {
        return new Response(null, {
          status: 304,
          headers: {
            ...JSON_HEADERS,
            "cache-control": "public, max-age=31536000, immutable",
            etag,
            "x-trialdiff-canonical-hash": head.canonicalHash,
          },
        });
      }
    }
  }

  const data = await getEvidenceCanonical(eventId);

  if (!data.databaseReady) {
    return new Response(JSON.stringify({ error: "Evidence database unavailable. Try again shortly." }), {
      status: 503,
      headers: JSON_HEADERS,
    });
  }

  if (data.canonicalText === undefined) {
    return new Response(JSON.stringify({ error: "Evidence Record not found." }), {
      status: 404,
      headers: JSON_HEADERS,
    });
  }

  const canonicalHash = data.canonicalHash ?? "";
  const bodyHash = createHash("sha256").update(data.canonicalText, "utf8").digest("hex");

  if (bodyHash !== canonicalHash) {
    // Serving these bytes 200 would assert verifiability the data cannot
    // support — an integrity failure, not a degraded success.
    console.error(
      `canonical bytes for ${eventId} hash to ${bodyHash}, expected ${canonicalHash}; ` +
        "the database predates the migration-006 re-import (see RELEASING.md section B)",
    );
    return new Response(
      JSON.stringify({
        error:
          "Stored canonical bytes do not verify against canonical_hash. " +
          "The database needs the post-migration-006 re-import; see RELEASING.md section B.",
        canonical_hash: canonicalHash,
      }),
      {
        status: 500,
        headers: {
          ...JSON_HEADERS,
          "cache-control": "no-store",
          "x-trialdiff-canonical-verified": "false",
        },
      },
    );
  }

  const etag = `"${canonicalHash}"`;
  return new Response(data.canonicalText, {
    status: 200,
    headers: {
      ...JSON_HEADERS,
      "cache-control": "public, max-age=31536000, immutable",
      etag,
      "x-trialdiff-canonical-hash": canonicalHash,
    },
  });
};
