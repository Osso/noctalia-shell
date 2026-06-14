#!/usr/bin/env node

const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const colorSchemeRoot = path.join(repoRoot, "Assets/ColorScheme");

const requiredPaletteKeys = [
  "mPrimary",
  "mOnPrimary",
  "mSecondary",
  "mOnSecondary",
  "mTertiary",
  "mOnTertiary",
  "mError",
  "mOnError",
  "mSurface",
  "mOnSurface",
  "mSurfaceVariant",
  "mOnSurfaceVariant",
  "mOutline",
  "mShadow",
  "mHover",
  "mOnHover",
];

const requiredTerminalVariants = [
  mode => `terminal/alacritty/%s-${mode}`,
  mode => `terminal/foot/%s-${mode}`,
  mode => `terminal/ghostty/%s-${mode}`,
  mode => `terminal/kitty/%s-${mode}.conf`,
  mode => `terminal/wezterm/%s-${mode}.toml`,
];

function schemeDirectories() {
  return fs.readdirSync(colorSchemeRoot)
    .filter(entry => fs.statSync(path.join(colorSchemeRoot, entry)).isDirectory())
    .sort();
}

function readScheme(schemeName) {
  const schemePath = path.join(colorSchemeRoot, schemeName, `${schemeName}.json`);
  assert.ok(fs.existsSync(schemePath), `missing color scheme JSON: ${schemePath}`);
  return JSON.parse(fs.readFileSync(schemePath, "utf8"));
}

function assertPalette(modeName, palette) {
  assert.equal(typeof palette, "object", `${modeName} palette must be an object`);
  assert.deepEqual(Object.keys(palette).sort(), [...requiredPaletteKeys].sort(), `${modeName} palette keys changed`);

  for (const key of requiredPaletteKeys) {
    assert.match(palette[key], /^#[0-9a-fA-F]{6}$/, `${modeName}.${key} must be a hex color`);
  }
}

function assertTerminalVariantsExist(schemeName) {
  for (const mode of ["dark", "light"]) {
    for (const variantPath of requiredTerminalVariants.map(makePath => makePath(mode))) {
      const relativePath = variantPath.replace("%s", schemeName);
      const absolutePath = path.join(colorSchemeRoot, schemeName, relativePath);
      assert.ok(fs.existsSync(absolutePath), `missing terminal variant: ${relativePath}`);
      assert.ok(fs.statSync(absolutePath).size > 0, `empty terminal variant: ${relativePath}`);
    }
  }
}

function testColorSchemeAssets() {
  const schemes = schemeDirectories();
  assert.equal(schemes.length, 10);

  for (const schemeName of schemes) {
    const scheme = readScheme(schemeName);
    assert.deepEqual(Object.keys(scheme).sort(), ["dark", "light"], `${schemeName} must define dark and light modes`);
    assertPalette(`${schemeName}.dark`, scheme.dark);
    assertPalette(`${schemeName}.light`, scheme.light);
    assertTerminalVariantsExist(schemeName);
  }
}

testColorSchemeAssets();
console.log("ok testColorSchemeAssets");
