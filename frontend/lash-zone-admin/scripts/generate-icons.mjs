/**
 * Generate PNG icons from SVG for PWA
 * Uses @resvg/resvg-js (zero native deps, pure WASM)
 * Runs as a prebuild step: node scripts/generate-icons.mjs
 */
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = join(__dirname, '..');
const iconsDir = join(rootDir, 'public', 'icons');

// Try to use @resvg/resvg-js if available, else skip PNG generation
async function generateIcons() {
  let Resvg;
  try {
    const mod = await import('@resvg/resvg-js');
    Resvg = mod.Resvg;
  } catch {
    console.log('[icons] @resvg/resvg-js not available — skipping PNG generation.');
    console.log('[icons] SVG icon will be used for all platforms.');
    return;
  }

  mkdirSync(iconsDir, { recursive: true });

  const svgPath = join(iconsDir, 'icon.svg');
  const svgData = readFileSync(svgPath, 'utf8');

  const sizes = [
    { name: 'icon-192.png', size: 192 },
    { name: 'icon-512.png', size: 512 },
    { name: 'apple-touch-icon.png', size: 180 },
  ];

  for (const { name, size } of sizes) {
    const resvg = new Resvg(svgData, {
      fitTo: { mode: 'width', value: size },
    });
    const png = resvg.render().asPng();
    writeFileSync(join(iconsDir, name), png);
    console.log(`[icons] Generated ${name} (${size}x${size})`);
  }

  console.log('[icons] All PWA icons generated successfully.');
}

generateIcons().catch(console.error);
