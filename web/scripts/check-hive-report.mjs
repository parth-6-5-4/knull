// Generated-report fixture boundary: actual project parser, isolated Chromium.
import assert from 'node:assert/strict';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { marked } from 'marked';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../../', import.meta.url));
const evidenceDir = path.join(root, 'docs/reports/hive-003');
const normalize = (value) => value.replace(/\r\n?/g, '\n');
let input = '';
for await (const chunk of process.stdin) input += chunk;
const fixtures = JSON.parse(input);
assert.ok(Array.isArray(fixtures) && fixtures.length > 0, 'fixtures required');

// Reuse current report prose rules/tokens. This is a report-only fixture, not
// the full console: no React shell, Tailwind build, provider or remote fonts.
const css = await readFile(path.join(root, 'web/src/styles.css'), 'utf8');
const tokens = [...css.matchAll(/^\s*(--[\w-]+:\s*[^;]+;)/gm)].map((match) => match[1]).join('\n');
const prose = css.split('/* report prose */')[1].split('/* dot-grid canvas')[0];
const body = css.match(/body \{([\s\S]*?)\n\}/)[1];
const harnessCss = `:root{${tokens}}body{${body};margin:0;padding:24px} ${prose}`;
const results = { fixtures: fixtures.length, viewport_checks: 0, network_requests: [], page_errors: [],
  screenshots: [], viewports: [] };
await mkdir(evidenceDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
results.chromium_version = browser.version();
try {
  const context = await browser.newContext({ serviceWorkers: 'block' });
  await context.route('**/*', async (route) => {
    results.network_requests.push(route.request().url());
    await route.abort();
  });
  const page = await context.newPage();
  page.on('pageerror', (error) => results.page_errors.push(error.message));
  page.on('dialog', async (dialog) => {
    results.page_errors.push(`unexpected ${dialog.type()} dialog: ${dialog.message()}`);
    await dialog.dismiss();
  });
  for (const [index, fixture] of fixtures.entries()) {
    const parsed = marked.parse(fixture.markdown, { async: false });
    for (const viewport of [{ width: 390, height: 844 }, { width: 1440, height: 900 }]) {
      await page.setViewportSize(viewport);
      await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${harnessCss}</style></head><body><article class="report">${parsed}</article></body></html>`);
      const actual = await page.evaluate(() => {
        const report = document.querySelector('.report');
        return {
          headings: [...report.querySelectorAll('h1,h2,h3,h4,h5,h6')].map((node) => [node.tagName, node.textContent]),
          claims: [...report.querySelectorAll('.hive-claim')].map((node) => node.textContent),
          objective: report.querySelector('.hive-objective')?.textContent,
          titles: [...report.querySelectorAll('.hive-source-title')].map((node) => node.textContent),
          urls: [...report.querySelectorAll('.hive-source-url')].map((node) => node.textContent),
          citations: [...report.querySelectorAll('a:not(.hive-source-url)')].map((node) => [node.getAttribute('href'), node.textContent]),
          sourceCitations: [...report.querySelectorAll('.hive-citation')].map((node) => node.textContent),
          activeUrls: [...report.querySelectorAll('a.hive-source-url')].map((node) => node.getAttribute('href')),
          ids: [...report.querySelectorAll('[id]')].map((node) => node.id),
          listCounts: [...report.querySelectorAll('ul')].map((node) => node.children.length),
          elements: [...report.querySelectorAll('*')].map((node) => ({ tag: node.tagName,
            attrs: [...node.attributes].map((attr) => [attr.name, attr.value]) })),
          literalStyles: [...report.querySelectorAll('span,.hive-source-url')].map((node) => ({
            whiteSpace: getComputedStyle(node).whiteSpace, overflowWrap: getComputedStyle(node).overflowWrap })),
          documentWidth: document.documentElement.scrollWidth,
          viewportWidth: window.innerWidth,
          reportWidth: report.getBoundingClientRect().width,
        };
      });
      const label = `fixture ${index}, ${viewport.width}x${viewport.height}`;
      assert.deepEqual(actual.headings, [['H1', 'Research report'], ['H2', 'Findings'], ['H2', 'Sources']], label);
      assert.deepEqual(actual.claims, fixture.claims.map(normalize), label);
      assert.equal(actual.objective, normalize(fixture.objective), label);
      assert.deepEqual(actual.titles, fixture.titles.map(normalize), label);
      assert.deepEqual(actual.urls, fixture.urls.map(normalize), label);
      assert.deepEqual(actual.activeUrls, fixture.active_urls, label);
      const anchors = fixture.claims.map((_, i) => `hive-source-${i + 1}`);
      assert.deepEqual(actual.ids, anchors, label);
      const citationLabels = fixture.fact_ids.map((id) => normalize(`[${id}]`));
      assert.deepEqual(actual.citations, anchors.map((id, i) => [`#${id}`, citationLabels[i]]), label);
      assert.deepEqual(actual.sourceCitations, citationLabels, label);
      assert.deepEqual(actual.listCounts, [fixture.claims.length, fixture.claims.length], label);
      for (const element of actual.elements) {
        assert.ok(['H1', 'H2', 'P', 'UL', 'LI', 'SPAN', 'A'].includes(element.tag), `${label}: unexpected ${element.tag}`);
        for (const [name, value] of element.attrs) {
          assert.ok(['id', 'class', 'style', 'href'].includes(name), `${label}: unexpected ${name}`);
          if (name === 'style') assert.equal(value, 'white-space: pre-wrap; overflow-wrap: anywhere', label);
          if (name === 'class') assert.ok(['hive-claim', 'hive-objective', 'hive-source-title', 'hive-source-url', 'hive-citation'].includes(value), label);
          if (name === 'id') assert.ok(anchors.includes(value), label);
        }
      }
      for (const style of actual.literalStyles) {
        assert.deepEqual(style, { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }, label);
      }
      assert.ok(actual.documentWidth <= actual.viewportWidth, `${label}: document overflow`);
      assert.ok(actual.reportWidth <= actual.viewportWidth, `${label}: report overflow`);
      assert.deepEqual(results.network_requests, [], `${label}: network request`);
      assert.deepEqual(results.page_errors, [], `${label}: page error`);
      results.viewport_checks += 1;
      results.viewports.push({ fixture: index, ...viewport, document_width: actual.documentWidth,
        report_width: actual.reportWidth });
      if ([0, 4, 5].includes(index)) {
        const relative = `docs/reports/hive-003/report-fixture-${index}-${viewport.width}x${viewport.height}.png`;
        await page.screenshot({ path: path.join(root, relative), fullPage: true });
        results.screenshots.push(relative);
      }
    }
  }
  await context.close();
} finally {
  await browser.close();
}
assert.deepEqual(results.network_requests, []);
assert.deepEqual(results.page_errors, []);
await writeFile(path.join(evidenceDir, 'report-browser-evidence.json'), JSON.stringify(results, null, 2) + '\n');
process.stdout.write(JSON.stringify(results) + '\n');
