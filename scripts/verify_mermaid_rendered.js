#!/usr/bin/env node
/**
 * Validate Mermaid diagrams by checking the BUILT HTML output.
 *
 * The mkdocs-mermaid2 plugin wraps diagrams in `<pre><code>...</code></pre>`,
 * which causes the browser's HTML parser to strip `<br/>`, `<i>`, `<b>` etc.
 * before mermaid sees the source. This script extracts the textContent from
 * each rendered <pre class="mermaid"> block — exactly what mermaid will see —
 * and runs it through mermaid's own parser.
 *
 * Pre-condition: the site has been built (run `mkdocs build` first).
 *
 * Usage:
 *   node scripts/verify_mermaid_rendered.js site/
 *
 * Exits 0 if all rendered diagrams parse; non-zero on any failure.
 */

const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

async function main() {
  // Set up a minimal DOM via jsdom — Mermaid's parser uses DOMPurify.
  const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
  global.window = dom.window;
  global.document = dom.window.document;
  global.Element = dom.window.Element;
  global.HTMLElement = dom.window.HTMLElement;
  global.Node = dom.window.Node;
  global.DocumentFragment = dom.window.DocumentFragment;

  const mermaid = (await import("mermaid")).default;
  mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });

  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error("usage: verify_mermaid_rendered.js <site_root>");
    process.exit(2);
  }

  const siteRoot = args[0];
  const htmlFiles = [];
  walkDir(siteRoot, htmlFiles);

  let totalDiagrams = 0;
  const failures = [];

  for (const file of htmlFiles) {
    const html = fs.readFileSync(file, "utf-8");
    const blocks = extractMermaidBlocks(html);
    for (const { source, sourceFile } of blocks) {
      totalDiagrams++;
      try {
        await mermaid.parse(source);
      } catch (e) {
        failures.push({
          file,
          source,
          error: e.message || String(e),
        });
      }
    }
  }

  console.log(`\n# verify_mermaid_rendered.js summary`);
  console.log(`- HTML files scanned: ${htmlFiles.length}`);
  console.log(`- Diagrams in built HTML: ${totalDiagrams}`);
  console.log(`- Syntax failures (post-render): ${failures.length}`);

  if (failures.length > 0) {
    console.log(`\n## Failures (rendered textContent)\n`);
    for (const f of failures) {
      console.log(`### \`${f.file}\``);
      console.log("```mermaid");
      console.log(f.source);
      console.log("```");
      console.log(`**Error:** ${f.error}\n`);
    }
    process.exit(1);
  }
  process.exit(0);
}

function walkDir(dir, files) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith(".")) continue;
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) walkDir(p, files);
    else if (entry.isFile() && p.endsWith(".html")) files.push(p);
  }
}

function extractMermaidBlocks(html) {
  // Use jsdom to parse HTML, find every <pre class="mermaid">, and
  // extract textContent — exactly what mermaid sees at runtime.
  const dom = new JSDOM(html);
  const blocks = [];
  for (const pre of dom.window.document.querySelectorAll("pre.mermaid")) {
    blocks.push({ source: pre.textContent.trim() });
  }
  return blocks;
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
