(() => {
  const key = "omr-language";
  const supported = (value) => value === "en" || value === "fr";

  document.querySelectorAll("a[data-language]").forEach((link) => {
    const lang = link.dataset.language;
    if (!supported(lang)) return;
    link.href = `/${lang}/${location.hash}`;
    link.addEventListener("click", () => {
      link.href = `/${lang}/${location.hash}`;
      try {
        localStorage.setItem(key, lang);
      } catch {
        // The link works even when storage is unavailable.
      }
    });
  });

  if (location.pathname !== "/") return;
  let preferred;
  try {
    preferred = localStorage.getItem(key);
  } catch {
    // Browser language detection works without storage.
  }
  if (!supported(preferred)) {
    const languages = navigator.languages?.length
      ? navigator.languages
      : [navigator.language];
    preferred = languages
      .filter((value) => typeof value === "string")
      .map((value) => value.toLowerCase().split("-")[0])
      .find(supported);
  }
  location.replace(`/${preferred || "en"}/${location.hash}`);
})();
