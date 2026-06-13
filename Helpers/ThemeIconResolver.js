.pragma library

function themeHasIcon(iconApi, iconName) {
  if (!iconApi || !iconName)
    return false;

  try {
    if (iconApi.hasThemeIcon)
      return iconApi.hasThemeIcon(iconName);
  } catch (e) {
    // Fall through to checked iconPath for older runtimes.
  }

  try {
    if (iconApi.iconPath) {
      const checkedPath = iconApi.iconPath(iconName, true);
      return checkedPath !== undefined && checkedPath !== null && checkedPath !== "";
    }
  } catch (e2) {
    return false;
  }

  return false;
}

function resolveIconPath(iconApi, iconName, fallbackName) {
  const fallback = fallbackName || "application-x-executable";
  const primary = iconName || "";

  if (!iconApi || !iconApi.iconPath)
    return "";

  if (themeHasIcon(iconApi, primary))
    return iconApi.iconPath(primary, true) || "";

  if (themeHasIcon(iconApi, fallback))
    return iconApi.iconPath(fallback, true) || "";

  return "";
}
