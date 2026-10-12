const assert = require("assert/strict");
const { stripQmlComments } = require("./qml-test-utils");

function maskLiteralTokens(source) {
  const code = stripQmlComments(source);
  const literals =
    /"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|`(?:\\[\s\S]|[^`\\])*`|(^|[=(:,\[!&|?;{}>]|\breturn)(\s*\/(?:\\.|[^/\\\n])+\/[a-z]*)/gm;
  return code.replace(literals, (token, prefix = "") => {
    const retained = prefix || "";
    return retained + token.slice(retained.length).replace(/[^\n]/g, " ");
  });
}

function readOwnDeclarationText(code, open) {
  let depth = 1;
  let own = "";
  for (let index = open + 1; index < code.length; index++) {
    const char = code[index];
    if (char === "{") depth++;
    if (char === "}") depth--;
    if (depth === 0) return { own, end: index + 1 };
    own += depth === 1 && char !== "}" ? char : (char === "\n" ? "\n" : " ");
  }
  throw new Error("Unterminated QML inventory owner");
}

function findOwnerDeclaration(source, componentType, ownerId) {
  const code = maskLiteralTokens(source);
  const objects = /\b([A-Z][\w.]*)\s*\{/g;
  const owners = Array.from(code.matchAll(objects))
    .filter((match) => match[1] === componentType)
    .map((match) => {
      const open = code.indexOf("{", match.index);
      const { own, end } = readOwnDeclarationText(code, open);
      const id = own.match(/\bid\s*:\s*([\w$]+)/)?.[1];
      return { id, own, source: source.slice(match.index, end) };
    })
    .filter((owner) => owner.id === ownerId);
  assert.equal(owners.length, 1, `${componentType} owner ${ownerId} must be unique`);
  return owners[0];
}

// Exact declared fields on this owner, independent of order or nested children.
// This is structural source evidence, not binding or runtime behavior proof.
function assertOwnedProperties(source, componentType, ownerId, expected) {
  const owner = findOwnerDeclaration(source, componentType, ownerId);
  const declarations = Array.from(owner.own.matchAll(/\b(?:(required|readonly)\s+)?property\s+([\w.<>]+)\s+([\w$]+)/g));
  for (const [name, contract] of Object.entries(expected)) {
    const actual = declarations.filter((match) => match[3] === name)
      .map((match) => [match[1], match[2]].filter(Boolean).join(" "));
    assert.deepEqual(actual, [contract], `${componentType} ${ownerId}: ${name}`);
  }
  return owner.source;
}

module.exports = { assertOwnedProperties };
