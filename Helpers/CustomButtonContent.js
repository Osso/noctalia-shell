.pragma library

function toHtml(str) {
  const htmlTagRegex = /<\/?[a-zA-Z][^>]*>/g;
  const placeholders = [];
  let index = 0;
  const protectedStr = String(str || "").replace(htmlTagRegex, tag => {
    placeholders.push(tag);
    return `___HTML_TAG_${index++}___`;
  });

  let escaped = protectedStr
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
    .replace(/\r\n|\r|\n/g, "<br/>");

  return escaped.replace(
    /___HTML_TAG_(\d+)___/g,
    (_, placeholderIndex) => placeholders[Number(placeholderIndex)],
  );
}

function checkCollapse(text, textCollapse) {
  if (!textCollapse || textCollapse.length === 0) {
    return false;
  }

  if (textCollapse.startsWith("/") && textCollapse.endsWith("/") && textCollapse.length > 1) {
    const pattern = textCollapse.substring(1, textCollapse.length - 1);
    try {
      return new RegExp(pattern).test(text);
    } catch (e) {
      return textCollapse === text;
    }
  }

  return textCollapse === text;
}

function chooseJsonLine(content, textStream) {
  if (textStream || !content.includes("\n")) {
    return content;
  }

  const lines = content.split("\n").filter(line => line.trim() !== "");
  return lines.length > 0 ? lines[lines.length - 1] : content;
}

function collapsedResult() {
  return {
    collapsed: true,
    text: "",
    icon: "",
    tooltip: "",
    originalText: "",
    needsScrolling: false,
    visibleText: "",
    parseFailed: false,
  };
}

function visibleTextFor(text, maxTextLength) {
  if (text.length > maxTextLength && maxTextLength > 0) {
    return text.substring(0, maxTextLength);
  }
  return text;
}

function parseDynamicContent(content, options) {
  const config = options || {};
  const contentStr = String(content || "").trim();
  const maxTextLength = Number(config.maxTextLength || 0);
  const textCollapse = String(config.textCollapse || "");
  const parseJson = config.parseJson === true;
  const textStream = config.textStream === true;

  if (parseJson) {
    const lineToParse = chooseJsonLine(contentStr, textStream);
    try {
      const parsed = JSON.parse(lineToParse);
      const text = parsed.text || "";

      if (checkCollapse(text, textCollapse)) {
        return collapsedResult();
      }

      return {
        collapsed: false,
        text,
        icon: parsed.icon || "",
        tooltip: toHtml(parsed.tooltip || ""),
        originalText: text,
        needsScrolling: text.length > maxTextLength && maxTextLength > 0,
        visibleText: visibleTextFor(text, maxTextLength),
        parseFailed: false,
      };
    } catch (e) {
      return parsePlainContent(contentStr, maxTextLength, textCollapse, true);
    }
  }

  return parsePlainContent(contentStr, maxTextLength, textCollapse, false);
}

function parsePlainContent(contentStr, maxTextLength, textCollapse, parseFailed) {
  if (checkCollapse(contentStr, textCollapse)) {
    return collapsedResult();
  }

  return {
    collapsed: false,
    text: contentStr,
    icon: "",
    tooltip: toHtml(contentStr),
    originalText: contentStr,
    needsScrolling: contentStr.length > maxTextLength && maxTextLength > 0,
    visibleText: visibleTextFor(contentStr, maxTextLength),
    parseFailed,
  };
}
