import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = new URL('../out/', import.meta.url).pathname;
const htmlFiles: string[] = [];

function walk(directory: string) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) walk(path);
    else if (entry.name.endsWith('.html')) htmlFiles.push(path);
  }
}

function routeExists(route: string) {
  const clean = route.replace(/^\/PocketTally\//, '').replace(/\/$/, '');
  if (!clean || clean === '404.html') return true;
  return existsSync(join(root, clean, 'index.html')) || existsSync(join(root, clean));
}

walk(root);
const failures: string[] = [];
for (const file of htmlFiles) {
  const html = readFileSync(file, 'utf8');
  for (const match of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
    const value = match[1];
    if (!value.startsWith('/PocketTally/') || value.startsWith('/PocketTally/_next/')) continue;
    const route = value.split('#', 1)[0].split('?', 1)[0];
    if (!routeExists(route)) failures.push(`${relative(root, file)} -> ${route}`);
  }
}

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log(`文档内部链接有效：检查 ${htmlFiles.length} 个 HTML 文件`);
