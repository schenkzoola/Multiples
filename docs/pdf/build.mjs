// Builds the user manual and assembly guide as PDFs from the Markdown docs.
// Usage (from docs/pdf): npm install, then npm run build
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Marked } from "marked";
import { gfmHeadingId } from "marked-gfm-heading-id";
import puppeteer from "puppeteer";

const HERE = dirname(fileURLToPath(import.meta.url));
const DOCS = resolve(HERE, "..");
const ROOT = resolve(DOCS, "..");
const REPO_URL = "https://github.com/schenkzoola/Multiples/blob/master";
const PCB_VERSION = "v1.0";

const DOCUMENTS = [
  { src: "manual.md", out: "passive-multiple-manual.pdf", title: "User Manual" },
  { src: "assembly-guide.md", out: "passive-multiple-assembly-guide.pdf", title: "Assembly Guide" },
];

// The date the source file last changed, so rebuilding unchanged docs gives the same date.
function lastChanged(file) {
  try {
    const date = execFileSync("git", ["log", "-1", "--format=%cs", "--", file], { cwd: ROOT }).toString().trim();
    if (date) return date;
  } catch {}
  return new Date().toISOString().slice(0, 10);
}

// Links to other files in the repo point at GitHub, since the PDF travels on its own.
function rewriteLinks(html) {
  return html.replace(/href="([^"#:][^":]*)"/g, (_, target) => {
    const repoPath = relative(ROOT, resolve(DOCS, target)).split("\\").join("/");
    return `href="${REPO_URL}/${repoPath}"`;
  });
}

// Chrome stamps each PDF with the build time, so unchanged docs would still
// produce a new file on every build. Pin the stamps to the doc's "Updated"
// date instead. The replacement is the same length, so the PDF stays valid.
function pinTimestamps(pdf, date) {
  const stamp = `D:${date.replaceAll("-", "")}000000`;
  const text = Buffer.from(pdf).toString("latin1")
    .replace(/\/(CreationDate|ModDate) \(D:\d{14}/g, (_, key) => `/${key} (${stamp}`);
  return Buffer.from(text, "latin1");
}

function page(doc, body) {
  const fonts = pathToFileURL(join(HERE, "node_modules/@fontsource/inter/files")).href;
  const css = readFileSync(join(HERE, "style.css"), "utf8").replaceAll("FONT_DIR", fonts);
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<base href="${pathToFileURL(DOCS).href}/">
<title>Passive Multiple ${doc.title}</title>
<style>${css}</style>
</head>
<body>
<header class="cover">
  <div class="brand">Schenktronics</div>
  <h1>Passive Multiple</h1>
  <div class="doc-title">${doc.title}</div>
  <div class="meta">For PCB ${PCB_VERSION} · Updated ${doc.date}</div>
</header>
${body}
</body>
</html>`;
}

const marked = new Marked({ gfm: true }).use(gfmHeadingId());
const tmp = mkdtempSync(join(tmpdir(), "pm-pdf-"));
// GitHub's Ubuntu runners block Chrome's sandbox, so it's turned off there.
const args = ["--allow-file-access-from-files", ...(process.env.CI ? ["--no-sandbox"] : [])];
const browser = await puppeteer.launch({ args });
try {
  for (const doc of DOCUMENTS) {
    const source = join(DOCS, doc.src);
    // The cover replaces the document's own H1.
    const markdown = readFileSync(source, "utf8").replace(/^# .*\n/, "");
    doc.date = lastChanged(source);
    const htmlPath = join(tmp, doc.out.replace(/\.pdf$/, ".html"));
    writeFileSync(htmlPath, page(doc, rewriteLinks(marked.parse(markdown))));

    const tab = await browser.newPage();
    await tab.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle0" });
    await tab.evaluate(() => document.fonts.ready);
    const pdf = await tab.pdf({
      format: "Letter",
      printBackground: true,
      displayHeaderFooter: true,
      headerTemplate: "<span></span>",
      footerTemplate: `
        <div style="font-family: Helvetica, Arial, sans-serif; font-size: 7.5pt; color: #777;
                    width: 100%; margin: 0 16mm; display: flex; justify-content: space-between;">
          <span>Passive Multiple · ${doc.title} · PCB ${PCB_VERSION}</span>
          <span>schenktronics.com · CC BY-NC-SA 4.0</span>
          <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
        </div>`,
      margin: { top: "16mm", bottom: "18mm", left: "16mm", right: "16mm" },
    });
    await tab.close();
    writeFileSync(join(HERE, doc.out), pinTimestamps(pdf, doc.date));
    console.log("wrote", relative(ROOT, join(HERE, doc.out)));
  }
} finally {
  await browser.close();
  rmSync(tmp, { recursive: true, force: true });
}
