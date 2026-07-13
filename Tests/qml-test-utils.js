const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function readQml(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function maskedText(text) {
  return text.replace(/[^\n]/g, " ");
}

function consumeSimpleQuote(source, start) {
  const quote = source[start];
  let index = start + 1;
  while (index < source.length) {
    if (source[index] === "\\") index += 2;
    else if (source[index++] === quote) break;
  }
  return index;
}

function interpolationSlashTransition(source, index, depth) {
  if (depth === 0 || source[index] !== "/") return null;
  const next = source[index + 1];
  if (next === "/") return { depth, index: consumeLineComment(source, index) };
  if (next === "*") return { depth, index: consumeBlockComment(source, index) };
  if (startsRegexLiteral(source, index)) return { depth, index: consumeRegexLiteral(source, index) };
  return null;
}

function templateInterpolationTransition(source, index, depth) {
  const slashTransition = interpolationSlashTransition(source, index, depth);
  if (slashTransition) return slashTransition;
  const current = source[index];
  const next = source[index + 1];
  if (current === "$" && next === "{") return { depth: depth + 1, index: index + 2 };
  if (current === "{" && depth > 0) return { depth: depth + 1, index: index + 1 };
  if (current === "}" && depth > 0) return { depth: depth - 1, index: index + 1 };
  if ((current === '"' || current === "'") && depth > 0) return { depth, index: consumeSimpleQuote(source, index) };
  if (current === "`" && depth > 0) return { depth, index: consumeTemplate(source, index) };
  return null;
}

function consumeTemplate(source, start) {
  let interpolationDepth = 0;
  let index = start + 1;
  while (index < source.length) {
    if (source[index] === "\\") {
      index += 2;
      continue;
    }
    const transition = templateInterpolationTransition(source, index, interpolationDepth);
    if (transition) {
      interpolationDepth = transition.depth;
      index = transition.index;
    } else if (source[index] === "`") return index + 1;
    else index++;
  }
  return index;
}

function consumeQuoted(source, start) {
  return source[start] === "`" ? consumeTemplate(source, start) : consumeSimpleQuote(source, start);
}

function consumeLineComment(source, start) {
  const newline = source.indexOf("\n", start);
  return newline === -1 ? source.length : newline;
}

function consumeBlockComment(source, start) {
  const close = source.indexOf("*/", start + 2);
  return close === -1 ? source.length : close + 2;
}

function previousNonSpace(source, index) {
  let cursor = index - 1;
  while (cursor >= 0 && /\s/.test(source[cursor])) cursor--;
  return cursor < 0 ? "" : source[cursor];
}

function startsRegexLiteral(source, index) {
  if (source[index] !== "/") return false;
  const previous = previousNonSpace(source, index);
  if ("=(:,[!&|?;{}>".includes(previous)) return true;
  return source.slice(0, index).trimEnd().endsWith("return");
}

function consumeRegexLiteral(source, start) {
  let inCharacterClass = false;
  let index = start + 1;
  while (index < source.length) {
    const current = source[index];
    if (current === "\\") index += 2;
    else if (current === "[") { inCharacterClass = true; index++; }
    else if (current === "]") { inCharacterClass = false; index++; }
    else if (current === "/" && !inCharacterClass) {
      index++;
      while (/[a-z]/i.test(source[index] || "")) index++;
      return index;
    } else index++;
  }
  return index;
}

function scanQml(source) {
  let withoutComments = "";
  let codeMask = "";
  let index = 0;
  while (index < source.length) {
    const current = source[index];
    const next = source[index + 1];
    if (current === '"' || current === "'" || current === "`") {
      const end = consumeQuoted(source, index);
      const token = source.slice(index, end);
      withoutComments += token;
      codeMask += maskedText(token);
      index = end;
    } else if (current === "/" && next === "/") {
      const end = consumeLineComment(source, index);
      const token = source.slice(index, end);
      withoutComments += maskedText(token);
      codeMask += maskedText(token);
      index = end;
    } else if (current === "/" && next === "*") {
      const end = consumeBlockComment(source, index);
      const token = source.slice(index, end);
      withoutComments += maskedText(token);
      codeMask += maskedText(token);
      index = end;
    } else if (startsRegexLiteral(source, index)) {
      const end = consumeRegexLiteral(source, index);
      const token = source.slice(index, end);
      withoutComments += token;
      codeMask += maskedText(token);
      index = end;
    } else {
      withoutComments += current;
      codeMask += current;
      index++;
    }
  }
  return { codeMask, withoutComments };
}

function stripQmlComments(source) {
  return scanQml(source).withoutComments;
}

function findBalancedBlockEnd(source, open, description) {
  const codeMask = scanQml(source).codeMask;
  let depth = 0;
  for (let index = open; index < codeMask.length; index++) {
    if (codeMask[index] === "{") depth++;
    if (codeMask[index] === "}") depth--;
    if (depth === 0) return index;
  }
  throw new Error(`unterminated ${description}`);
}

function escapedRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractComponentBlocks(source, componentName) {
  const { codeMask, withoutComments } = scanQml(source);
  const blocks = [];
  const declaration = new RegExp(`^[ \\t]*${escapedRegex(componentName)}\\s*\\{`, "gm");
  let match = declaration.exec(codeMask);
  while (match) {
    const start = match.index;
    const open = codeMask.indexOf("{", start);
    const end = findBalancedBlockEnd(codeMask, open, `${componentName} block`);
    blocks.push(withoutComments.slice(start, end + 1));
    declaration.lastIndex = end + 1;
    match = declaration.exec(codeMask);
  }
  return blocks;
}

function findComponentBlock(source, componentName, marker) {
  const matches = extractComponentBlocks(source, componentName).filter(block => block.includes(marker));
  assert.equal(matches.length, 1, `${componentName} block containing ${marker} must be unique`);
  return matches[0];
}

function extractHandlerBlock(source, handlerName) {
  const { codeMask, withoutComments } = scanQml(source);
  const declaration = new RegExp(`^[ \\t]*${escapedRegex(handlerName)}\\s*:`, "m");
  const match = declaration.exec(codeMask);
  assert.notEqual(match, null, `missing ${handlerName} handler`);
  const start = match.index;
  const open = codeMask.indexOf("{", start);
  assert.notEqual(open, -1, `missing ${handlerName} handler block`);
  const end = findBalancedBlockEnd(codeMask, open, `${handlerName} handler`);
  return withoutComments.slice(start, end + 1);
}

function extractFunctionBody(source, functionName) {
  const { codeMask } = scanQml(source);
  const declaration = new RegExp(`^[ \\t]*function\\s+${escapedRegex(functionName)}\\s*\\(`, "m");
  const match = declaration.exec(codeMask);
  assert.notEqual(match, null, `missing function: ${functionName}`);
  const blockStart = codeMask.indexOf("{", match.index);
  const blockEnd = findBalancedBlockEnd(codeMask, blockStart, `function: ${functionName}`);
  return source.slice(blockStart, blockEnd + 1);
}

function extractIpcHandlerBlock(source, targetName) {
  const marker = `target: "${targetName}"`;
  const targetIndex = source.indexOf(marker);
  assert.notEqual(targetIndex, -1, `missing IPC target: ${targetName}`);

  const blockStart = source.lastIndexOf("IpcHandler", targetIndex);
  assert.notEqual(blockStart, -1, `missing IPC handler for target: ${targetName}`);

  const braceStart = source.indexOf("{", blockStart);
  let depth = 0;

  for (let index = braceStart; index < source.length; index++) {
    const char = source[index];

    if (char === "{") {
      depth++;
    } else if (char === "}") {
      depth--;
      if (depth === 0) {
        return source.slice(blockStart, index + 1);
      }
    }
  }

  throw new Error(`unterminated IPC handler: ${targetName}`);
}

module.exports = {
  extractComponentBlocks,
  extractFunctionBody,
  extractHandlerBlock,
  extractIpcHandlerBlock,
  findComponentBlock,
  readQml,
  stripQmlComments,
};
