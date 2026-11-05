import type { Config, Context } from "@netlify/edge-functions";
import { injectClickio, MARKER } from "../../scripts/clickio-tags.mjs";

// Injects the Clickio consent/site tags and publisher sidebar (see scripts/clickio-tags.mjs) into every HTML page.
export default async (_req: Request, context: Context) => {
  const res = await context.next();
  const type = res.headers.get("content-type") || "";
  if (!type.includes("text/html")) return res;

  const html = await res.text();
  if (html.includes(MARKER)) return new Response(html, res);

  const headers = new Headers(res.headers);
  headers.delete("content-length");
  return new Response(injectClickio(html), { status: res.status, statusText: res.statusText, headers });
};

export const config: Config = {
  path: "/*",
  excludedPath: [
    "/assets/*",
    "/.netlify/*",
    "/*.css",
    "/*.js",
    "/*.json",
    "/*.xml",
    "/*.txt",
    "/*.png",
    "/*.jpg",
    "/*.jpeg",
    "/*.webp",
    "/*.svg",
    "/*.ico",
    "/*.pdf",
    "/*.csv",
  ],
};
