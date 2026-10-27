import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';
const root = new URL('../public/', import.meta.url).pathname;
const origin = 'https://golfcut.goswie.com';
const urls = [...readFileSync(join(root, 'sitemap.xml'), 'utf8').matchAll(/<loc>(.*?)<\/loc>/g)].map(m => m[1]);
assert.equal(urls.length, new Set(urls).size, 'Duplicate sitemap URLs');
const titles = new Set(), descriptions = new Set();
const sourceFor = path => path === '/' ? join(root, 'index.html') : existsSync(join(root, path, 'index.html')) ? join(root, path, 'index.html') : join(root, `${path}.html`);
const tags = (s, tag) => [...s.matchAll(new RegExp(`<${tag}\\b[^>]*>`, 'g'))].map(m => Object.fromEntries([...m[0].matchAll(/([\w:-]+)="([^"]*)"/g)].map(a => [a[1], a[2]])));
const pages = new Map();
for (const url of urls) {
  assert.ok(url.startsWith(origin + '/'), `Wrong sitemap origin: ${url}`);
  const path = new URL(url).pathname;
  assert.ok(path === '/' || !path.endsWith('/'), `Trailing slash: ${url}`);
  const s = readFileSync(sourceFor(path), 'utf8'); pages.set(path, s);
  assert.match(s, /<html lang="en">/);
  assert.equal([...s.matchAll(/<h1\b/g)].length, 1, `${url}: expected one H1`);
  const title = s.match(/<title>(.*?)<\/title>/)?.[1];
  assert.ok(title && !titles.has(title), `${url}: missing/duplicate title`); titles.add(title);
  const metas = tags(s, 'meta');
  const meta = key => metas.filter(m => m.name === key || m.property === key);
  for (const key of ['description','viewport','robots','og:type','og:site_name','og:locale','og:title','og:description','og:url','og:image','og:image:width','og:image:height','og:image:alt','twitter:card','twitter:title','twitter:description','twitter:image','twitter:image:alt']) {
    assert.equal(meta(key).length, 1, `${url}: missing/duplicate ${key}`);
    assert.ok(meta(key)[0].content, `${url}: empty ${key}`);
  }
  const desc = meta('description')[0].content;
  assert.ok(!descriptions.has(desc), `${url}: duplicate description`); descriptions.add(desc);
  assert.ok(!meta('robots')[0].content.includes('noindex'), `${url}: blocked indexing`);
  const canonical = tags(s,'link').filter(t => t.rel === 'canonical');
  assert.equal(canonical.length, 1); assert.equal(canonical[0].href, url);
  assert.equal(meta('og:url')[0].content, url);
  const graphs = [...s.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/gs)].map(m => JSON.parse(m[1]));
  assert.equal(graphs.length,1);
  const graph = graphs[0]['@graph'];
  for (const type of ['Organization','WebSite','WebPage']) assert.ok(graph.some(g => g['@type'] === type), `${url}: missing ${type}`);
  assert.equal(graph.find(g => g['@type'] === 'WebPage').url,url);
  if(path !== '/') {
    const crumbs = graph.find(g => g['@type'] === 'BreadcrumbList');
    assert.equal(crumbs?.itemListElement.at(-1).item, url);
    assert.match(s,/aria-label="Breadcrumb"/);
  }
  for (const image of tags(s,'img')) {
    assert.ok('alt' in image, `${url}: missing alt`);
    assert.ok(image.width && image.height, `${url}: image dimensions missing`);
  }
}
let checkedLinks = 0;
for (const [path,s] of pages) {
  for (const tag of [...tags(s,'a'),...tags(s,'link'),...tags(s,'img'),...tags(s,'script')]) {
    const value = tag.href || tag.src;
    if (!value || /^(https?:|mailto:|tel:|data:)/.test(value)) continue;
    const target = new URL(value, origin+path); const destination = target.pathname;
    assert.ok(destination === '/' || !destination.endsWith('/'), `${path}: internal redirect ${value}`);
    assert.ok(pages.has(destination) || existsSync(join(root,destination)), `${path}: broken link ${value}`);
    if (target.hash && pages.has(destination)) assert.ok(pages.get(destination).includes(`id="${target.hash.slice(1)}"`), `${path}: missing anchor ${value}`);
    checkedLinks++;
  }
}
const htmlFiles = dir => readdirSync(dir,{withFileTypes:true}).flatMap(d => d.isDirectory() ? htmlFiles(join(dir,d.name)) : d.name.endsWith('.html') ? [join(dir,d.name)] : []);
assert.equal(htmlFiles(root).filter(p => !/\/(404|google[^/]+)\.html$/.test(p)).length, urls.length, 'Sitemap omits public pages');
assert.match(readFileSync(join(root,'404.html'),'utf8'), /content="noindex, follow"/);
assert.equal(readFileSync(join(root,'google828db80516d18f39.html'),'utf8').trim(), 'google-site-verification: google828db80516d18f39.html');
assert.ok(readFileSync(join(root,'robots.txt'),'utf8').includes(`Sitemap: ${origin}/sitemap.xml`));
console.log(`SEO checks passed: ${urls.length} pages, ${checkedLinks} internal links/assets, metadata, JSON-LD, sitemap, 404 and GSC file.`);
