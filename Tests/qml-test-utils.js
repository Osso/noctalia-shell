const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");

function readQml(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function extractFunctionBody(source, functionName) {
  const marker = `function ${functionName}(`;
  const markerIndex = source.indexOf(marker);
  assert.notEqual(markerIndex, -1, `missing function: ${functionName}`);

  const blockStart = source.indexOf("{", markerIndex);
  let depth = 0;

  for (let index = blockStart; index < source.length; index++) {
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

  throw new Error(`unterminated function: ${functionName}`);
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
  extractFunctionBody,
  extractIpcHandlerBlock,
  readQml,
};
