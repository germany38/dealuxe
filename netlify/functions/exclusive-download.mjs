import { readFile } from "node:fs/promises";
import { join } from "node:path";
import ITEMS from "../lib/exclusive-items.mjs";

// Download links stay valid this long after checkout.
const MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

// dealuxapp.com is served from a different host, so its success page calls this API cross-origin.
const ALLOWED_ORIGINS = ["https://dealuxapp.com", "https://www.dealuxapp.com"];

const cors = (req) => {
  const origin = req.headers.get("origin");
  return origin && ALLOWED_ORIGINS.includes(origin) ? { "access-control-allow-origin": origin, vary: "origin" } : {};
};

const json = (req, body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store", ...cors(req) },
  });

// Read the product's real PDF from the files bundled with this function.
async function readPdf(file) {
  const dirs = [process.cwd(), new URL("../..", import.meta.url).pathname];
  for (const dir of dirs) {
    try {
      return await readFile(join(dir, "exclusive-files", file));
    } catch {}
  }
  return null;
}

// Look up the Checkout Session with Stripe and confirm it was paid.
async function verify(sessionId) {
  const key = Netlify.env.get("STRIPE_SECRET_KEY");
  if (!key) return { error: "Downloads are temporarily unavailable. Please contact us with your receipt.", status: 503 };
  if (!/^cs_[A-Za-z0-9_]+$/.test(sessionId || "")) return { error: "Invalid checkout reference.", status: 400 };

  const res = await fetch(`https://api.stripe.com/v1/checkout/sessions/${sessionId}`, {
    headers: { authorization: `Bearer ${key}` },
  });
  if (!res.ok) return { error: "We couldn't find that checkout session.", status: 404 };
  const session = await res.json();

  if (session.payment_status !== "paid" && session.payment_status !== "no_payment_required") {
    return { error: "This payment hasn't completed yet. Refresh in a moment.", status: 402 };
  }
  if (Date.now() / 1000 - session.created > MAX_AGE_SECONDS) {
    return { error: "This download link has expired. Contact us with your receipt for a new one.", status: 410 };
  }
  const slug = session.client_reference_id;
  const item = slug && ITEMS[slug];
  if (!item) return { error: "We couldn't match this purchase to a resource. Contact us with your receipt.", status: 404 };
  return { slug, item };
}

export default async (req) => {
  const url = new URL(req.url);
  const result = await verify(url.searchParams.get("session_id"));
  if (result.error) return json(req, { error: result.error }, result.status);
  const { slug, item } = result;

  if (url.pathname.endsWith("/session")) return json(req, { slug, title: item.title, file: item.file });

  const body = await readPdf(item.file);
  if (!body) {
    console.error(`Missing exclusive PDF: ${item.file}`);
    return json(req, { error: "Your payment went through, but this file is temporarily unavailable. Contact us with your receipt." }, 500);
  }

  return new Response(body, {
    headers: {
      "content-type": "application/pdf",
      "content-disposition": `attachment; filename="${item.file}"`,
      "cache-control": "private, no-store",
    },
  });
};

export const config = {
  path: ["/api/exclusive/session", "/api/exclusive/download"],
};
