import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { getStore } from "@netlify/blobs";
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import ITEMS from "../lib/exclusive-items.mjs";

// Download links stay valid this long after checkout.
const MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });

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

// Wrap text to a given width.
function wrap(text, font, size, width) {
  const lines = [];
  let line = "";
  for (const word of text.split(/\s+/)) {
    const next = line ? `${line} ${word}` : word;
    if (font.widthOfTextAtSize(next, size) > width && line) {
      lines.push(line);
      line = word;
    } else line = next;
  }
  if (line) lines.push(line);
  return lines;
}

// pdf-lib's standard fonts only cover WinAnsi; swap out anything else.
const clean = (s) =>
  s.replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/[–—]/g, "-").replace(/[^\x20-\x7E\xA0-\xFF]/g, "");

// Build a printable worksheet PDF from the item's details.
async function buildPdf(item) {
  const doc = await PDFDocument.create();
  doc.setTitle(clean(item.title));
  doc.setAuthor("Dealux");
  const regular = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const gold = rgb(0.72, 0.56, 0.16);
  const ink = rgb(0.1, 0.1, 0.1);
  const grey = rgb(0.45, 0.45, 0.45);
  const W = 612, H = 792, M = 56;
  const title = clean(item.title);

  const footer = (page, n) => {
    page.drawLine({ start: { x: M, y: 40 }, end: { x: W - M, y: 40 }, thickness: 0.5, color: grey });
    page.drawText(`Dealux Exclusive  |  ${item.id}  |  Page ${n} of ${item.pages}`, { x: M, y: 26, size: 8, font: regular, color: grey });
    page.drawText("dealuxapp.com", { x: W - M - regular.widthOfTextAtSize("dealuxapp.com", 8), y: 26, size: 8, font: regular, color: grey });
  };

  // Cover / overview
  let page = doc.addPage([W, H]);
  page.drawRectangle({ x: 0, y: H - 170, width: W, height: 170, color: rgb(0.07, 0.07, 0.07) });
  page.drawText(`DEALUX EXCLUSIVE  -  ${clean(item.type).toUpperCase()}`, { x: M, y: H - 60, size: 10, font: bold, color: gold });
  let y = H - 95;
  for (const l of wrap(title, bold, 24, W - 2 * M)) {
    page.drawText(l, { x: M, y, size: 24, font: bold, color: rgb(1, 1, 1) });
    y -= 28;
  }
  y = H - 210;
  page.drawText(clean(item.category), { x: M, y, size: 11, font: bold, color: gold });
  y -= 24;
  for (const l of wrap(clean(item.description), regular, 12, W - 2 * M)) {
    page.drawText(l, { x: M, y, size: 12, font: regular, color: ink });
    y -= 17;
  }
  y -= 18;
  page.drawText("How to use this resource", { x: M, y, size: 14, font: bold, color: ink });
  y -= 22;
  const steps = [
    "Print this PDF or fill it in on screen with any PDF reader.",
    "Work through each section before you commit to a decision or purchase.",
    "Write down real numbers - prices, dates, totals - so you can compare later.",
    "Keep completed sheets together and revisit them to spot what worked.",
  ];
  steps.forEach((s, i) => {
    page.drawText(`${i + 1}.`, { x: M, y, size: 11, font: bold, color: gold });
    page.drawText(s, { x: M + 18, y, size: 11, font: regular, color: ink });
    y -= 20;
  });
  y -= 16;
  page.drawText("Notes", { x: M, y, size: 14, font: bold, color: ink });
  y -= 10;
  while (y > 70) {
    y -= 24;
    page.drawLine({ start: { x: M, y }, end: { x: W - M, y }, thickness: 0.5, color: grey });
  }
  footer(page, 1);

  // Worksheet pages
  for (let n = 2; n <= item.pages; n++) {
    page = doc.addPage([W, H]);
    y = H - 60;
    page.drawText(title.length > 70 ? title.slice(0, 67) + "..." : title, { x: M, y, size: 14, font: bold, color: ink });
    y -= 18;
    const heading = item.type === "Checklist" ? "Checklist" : item.type === "Infographic" ? "Key points" : "Worksheet";
    page.drawText(`${heading} - part ${n - 1}`, { x: M, y, size: 10, font: bold, color: gold });
    y -= 30;
    page.drawText("Date: ____________________", { x: M, y, size: 10, font: regular, color: ink });
    page.drawText("Goal / budget: ____________________", { x: W / 2, y, size: 10, font: regular, color: ink });
    y -= 30;
    while (y > 80) {
      if (item.type === "Infographic") {
        page.drawRectangle({ x: M, y: y - 70, width: W - 2 * M, height: 70, borderColor: gold, borderWidth: 1 });
        y -= 86;
      } else {
        if (item.type === "Checklist") page.drawRectangle({ x: M, y: y - 2, width: 11, height: 11, borderColor: ink, borderWidth: 0.8 });
        const x0 = item.type === "Checklist" ? M + 20 : M;
        page.drawLine({ start: { x: x0, y: y - 2 }, end: { x: W - M, y: y - 2 }, thickness: 0.5, color: grey });
        y -= 28;
      }
    }
    footer(page, n);
  }
  return doc.save();
}

export default async (req, context) => {
  const url = new URL(req.url);
  const result = await verify(url.searchParams.get("session_id"));
  if (result.error) return json({ error: result.error }, result.status);
  const { slug, item } = result;

  if (url.pathname.endsWith("/session")) return json({ slug, title: item.title });

  // Prefer the bundled PDF, then an uploaded blob (key = file name); otherwise generate one.
  let body = null;
  try {
    body = await readFile(join(process.cwd(), "exclusive-files", item.file));
  } catch {}
  if (!body) try {
    body = await getStore("exclusive-pdfs").get(item.file, { type: "arrayBuffer" });
  } catch {}
  if (!body) body = await buildPdf(item);

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
