import { readFileSync, writeFileSync } from "node:fs";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";

const [baselinePath, actualPath, diffPath] = process.argv.slice(2);
if (!baselinePath || !actualPath) {
  console.error("Usage: node compare_screenshots.mjs <baseline.png> <actual.png> [diff.png]");
  process.exit(2);
}

const baseline = PNG.sync.read(readFileSync(baselinePath));
const actual = PNG.sync.read(readFileSync(actualPath));
if (baseline.width !== actual.width || baseline.height !== actual.height) {
  console.log(JSON.stringify({
    status: "DIMENSION_MISMATCH",
    baseline: { width: baseline.width, height: baseline.height },
    actual: { width: actual.width, height: actual.height },
    changedPixels: null,
    changedRatio: 1,
  }));
  process.exit(1);
}

const diff = new PNG({ width: baseline.width, height: baseline.height });
const changedPixels = pixelmatch(
  baseline.data,
  actual.data,
  diff.data,
  baseline.width,
  baseline.height,
  { threshold: 0.1, includeAA: false },
);
const totalPixels = baseline.width * baseline.height;
const changedRatio = changedPixels / totalPixels;
if (diffPath && changedPixels > 0) writeFileSync(diffPath, PNG.sync.write(diff));

const tolerance = 0.005;
const status = changedRatio <= tolerance ? "MATCH" : "REGRESSION";
console.log(JSON.stringify({
  status,
  width: baseline.width,
  height: baseline.height,
  changedPixels,
  changedRatio,
  tolerance,
}));
if (status !== "MATCH") process.exit(1);
