"use strict";
(() => {
  const release = JSON.parse(
    document.querySelector("#release-data").textContent,
  );
  const copy = JSON.parse(document.querySelector("#ui-copy").textContent);
  const scenarios = JSON.parse(
    document.querySelector("#scenario-data").textContent,
  );

  const allowedOS = ["macos", "windows", "linux"];
  const escapeHTML = (value) =>
    String(value).replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const svg = (name) => {
    const paths = {
      check: '<path d="m5 12 4 4L19 6"/>',
      chevron: '<path d="m6 9 6 6 6-6"/>',
      up: '<path d="M7 17 17 7M7 7h10v10"/>',
    };
    return `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || ""}</svg>`;
  };

  /** OS detection is advisory. An Intel macOS user-agent does NOT identify a Mac chip.
      High-entropy architecture hints are progressive enhancement, never a requirement. */
  function detectPlatform({
    userAgent = "",
    platform = "",
    hintsPlatform = "",
    maxTouchPoints = 0,
    architecture = "",
    bitness = "",
  } = {}) {
    const all = `${hintsPlatform} ${platform} ${userAgent}`.toLowerCase();
    if (
      /android|iphone|ipad|ipod/.test(all) ||
      (/mac/.test(all) && maxTouchPoints > 1)
    ) {
      return { os: null, arch: null, mobile: true };
    }
    const os = /mac/.test(all)
      ? "macos"
      : /win/.test(all)
        ? "windows"
        : /linux/.test(all) && !/cros/.test(all)
          ? "linux"
          : null;
    if (!os) return { os: null, arch: null, mobile: false };
    let arch = null;
    const hint = architecture.toLowerCase();
    if (hint === "arm")
      arch = bitness === "64" ? "arm64" : bitness === "32" ? "arm32" : "arm";
    else if (hint === "x86")
      arch = bitness === "64" ? "x64" : bitness === "32" ? "x86" : null;
    else if (os !== "macos") {
      if (/aarch64|arm64/.test(all)) arch = "arm64";
      else if (/x86_64|amd64|win64|wow64|\bx64\b/.test(all)) arch = "x64";
      else if (/i[3-6]86|windows (?:nt [\d.]+; )?x86/.test(all)) arch = "x86";
    }
    return { os, arch, mobile: false };
  }

  const state = {
    os: null,
    arch: null,
    file: null,
    archByOS: {},
    manual: false,
    scenario: "chat",
    revision: 0,
  };
  let detected = detectPlatform({
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    hintsPlatform: navigator.userAgentData?.platform || "",
    maxTouchPoints: navigator.maxTouchPoints || 0,
  });
  const findPackage = (os, arch) =>
    release.packages.find((p) => p.os === os && p.arch === arch) || null;
  const packageForState = () =>
    release.packages.find(
      (p) =>
        p.os === state.os && p.arch === state.arch && p.file === state.file,
    ) || findPackage(state.os, state.arch);
  const supportsDetectedArchitecture = (os) =>
    !(detected.os === os && detected.arch && !findPackage(os, detected.arch));

  function initialArch(os) {
    if (!os) return null;
    if (findPackage(os, state.archByOS[os])) return state.archByOS[os];
    if (detected.os === os && findPackage(os, detected.arch))
      return detected.arch;
    if (os === "macos" || !supportsDetectedArchitecture(os)) return null;
    return "x64"; // The sole published package, explicitly labelled in the UI.
  }
  function setOS(os) {
    if (!allowedOS.includes(os)) return;
    state.os = os;
    state.manual = true;
    state.revision++;
    state.arch = initialArch(os);
    renderDownloads();
  }
  function setArchitecture(arch) {
    if (!findPackage(state.os, arch)) return;
    state.arch = arch;
    state.archByOS[state.os] = arch;
    state.manual = true;
    state.revision++;
    renderDownloads();
  }
  const formatBytes = (bytes) =>
    `${(bytes / 1e6).toLocaleString(document.documentElement.lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} MB`;
  function renderDownloads() {
    const pkg = packageForState();
    const available = release.packages.filter((p) => p.os === state.os);
    const fallback = pkg || findPackage(state.os, "x64");
    const unavailable =
      document.documentElement.lang === "fr"
        ? "Aucun paquet disponible pour cette plateforme."
        : "No package available for this platform.";
    const osLabel = state.os ? copy.osLabels[state.os] : "";
    const heading = state.os
      ? (state.manual ? copy.manual : copy.detect).replace("{os}", osLabel)
      : detected.mobile
        ? copy.mobile
        : copy.chooseOS;
    let opts =
      state.os && !available.length
        ? `<span class="neutral-hint">${unavailable}</span>`
        : state.os === "macos"
          ? ["arm64", "x64"]
              .map(
                (arch) =>
                  `<button type="button" class="package-option" data-arch="${arch}" ${findPackage(state.os, arch) ? "" : 'disabled aria-disabled="true"'} aria-pressed="${state.arch === arch}">${copy.macos[arch]} <span>(${arch})</span></button>`,
              )
              .join("")
          : state.os && !supportsDetectedArchitecture(state.os)
            ? `<span class="arch-warning">${copy.unsupportedArch}</span><button type="button" class="package-option" data-arch="x64" aria-pressed="${state.arch === "x64"}">x64 · .${escapeHTML(fallback.format)}</button>`
            : state.os
              ? `<div class="package-fixed">${svg("check")}<span>${copy[state.os]}</span>${pkg ? `<span>· .${escapeHTML(pkg.format)}</span>` : ""}</div>`
              : `<span class="neutral-hint">${copy.chooseOS}</span>`;
    const formats = release.packages.filter(
      (p) => p.os === state.os && p.arch === state.arch,
    );
    const mixedVersions = new Set(formats.map((p) => p.version)).size > 1;
    if (formats.length > 1)
      opts += formats
        .map(
          (p) =>
            `<button type="button" class="package-option" data-package-format="${p.file}" aria-pressed="${p.file === pkg?.file}">.${escapeHTML(p.format)}${mixedVersions ? ` · v${escapeHTML(p.version)}` : ""}</button>`,
        )
        .join("");
    document.querySelectorAll("[data-download]").forEach((panel) => {
      panel.querySelector(".detected-label").textContent = heading;
      panel
        .querySelectorAll("[data-os]")
        .forEach((button) =>
          button.setAttribute(
            "aria-pressed",
            String(button.dataset.os === state.os),
          ),
        );
      panel.querySelector(".package-options").innerHTML = opts;
      panel.querySelector(".chip-help").hidden = state.os !== "macos";
      const link = panel.querySelector(".download-cta");
      if (pkg) {
        link.setAttribute("href", pkg.url);
        link.setAttribute("download", pkg.file);
        link.removeAttribute("aria-disabled");
        link.querySelector("span").textContent = copy.download.replace(
          "{os}",
          osLabel,
        );
        link.setAttribute(
          "aria-label",
          `${copy.download.replace("{os}", osLabel)} · ${pkg.arch} · ${pkg.format}`,
        );
      } else {
        link.removeAttribute("href");
        link.removeAttribute("download");
        link.removeAttribute("aria-label");
        link.setAttribute("aria-disabled", "true");
        link.querySelector("span").textContent = !state.os
          ? copy.noOS
          : !available.length
            ? unavailable
            : state.os === "macos"
              ? copy.chooseChip
              : copy.choosePackage;
      }
      panel.querySelector(".package-meta").textContent = pkg
        ? `v${pkg.version} · ${pkg.arch} · .${pkg.format} · ${formatBytes(pkg.bytes)}`
        : copy.releaseMeta;
    });
    renderDetails(pkg);
  }
  function renderDetails(pkg) {
    const host = document.querySelector(".package-details-content");
    const wasOpen = host.querySelector("details")?.open || false;
    if (!pkg) {
      host.innerHTML = `<p>${copy.unselectedDetail}</p>`;
      return;
    }
    const architecture =
      pkg.os === "macos" ? `${copy.macos[pkg.arch]} (${pkg.arch})` : pkg.arch;
    host.innerHTML = `<h3>${copy.osLabels[pkg.os]} · ${architecture}</h3>
      <p class="package-facts">v${escapeHTML(pkg.version)} · .${pkg.format} · ${formatBytes(pkg.bytes)}<br>${escapeHTML(pkg.file)}</p>
      ${pkg.notes ? `<p class="package-notes">${escapeHTML(pkg.notes)}</p>` : ""}
      <details id="checksum-details" ${wasOpen ? "open" : ""}><summary>${copy.checksums}${svg("chevron")}</summary>
      <code class="checksum" tabindex="0">${pkg.sha256}</code>
      <div class="checksum-actions"><button type="button" data-copy-checksum>${copy.copy}</button><a href="${pkg.checksumUrl}" target="_blank" rel="noopener noreferrer">${copy.sha}${svg("up")}</a></div>
      <p class="source-commit">${copy.sourceCommit}<code>${escapeHTML(pkg.sourceCommit)}</code></p></details>`;
  }
  function setScenario(key) {
    const s = scenarios.find((item) => item.key === key);
    if (!s) return;
    state.scenario = key;
    document.querySelectorAll("[data-scenario]").forEach((button) => {
      button.classList.toggle("selected", button.dataset.scenario === key);
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.scenario === key),
      );
    });
    document
      .querySelectorAll("[data-route]")
      .forEach((path) =>
        path.classList.toggle("active", path.dataset.route === key),
      );
    document.querySelector("[data-request]").textContent = `“${s.request}”`;
    document.querySelector("[data-family]").textContent = s.family;
    document.querySelector("[data-intent]").textContent = s.intent;
    document.querySelector("[data-fit]").textContent = s.fit;
    document.querySelector("[data-takeaway]").textContent = s.takeaway;
    document.querySelector("[data-short-family]").textContent = s.short;
    document.querySelector("#scenario-announcement").textContent = s.family;
  }
  let toastTimer;
  function toast(text) {
    const el = document.querySelector(".toast");
    el.textContent = text;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.hidden = true;
    }, 4000);
  }
  const menuButton = document.querySelector(".menu-toggle");
  const mobileNav = document.querySelector("#mobile-nav");
  function closeMenu() {
    mobileNav.hidden = true;
    menuButton.setAttribute("aria-expanded", "false");
  }

  document.addEventListener("click", async (event) => {
    const osButton = event.target.closest("[data-os]");
    if (osButton) {
      setOS(osButton.dataset.os);
      return;
    }
    const archButton = event.target.closest("[data-arch]");
    if (archButton) {
      const panel = archButton.closest("[data-download]");
      const arch = archButton.dataset.arch;
      setArchitecture(arch);
      panel
        .querySelector(`[data-arch="${arch}"]`)
        ?.focus({ preventScroll: true });
      return;
    }
    const formatButton = event.target.closest("[data-package-format]");
    if (formatButton) {
      const panel = formatButton.closest("[data-download]");
      state.file = formatButton.dataset.packageFormat;
      renderDownloads();
      [...panel.querySelectorAll("[data-package-format]")]
        .find((b) => b.dataset.packageFormat === state.file)
        ?.focus({ preventScroll: true });
      return;
    }
    const scenarioButton = event.target.closest("[data-scenario]");
    if (scenarioButton) {
      setScenario(scenarioButton.dataset.scenario);
      return;
    }
    const disabledLink = event.target.closest(
      '.download-cta[aria-disabled="true"]',
    );
    if (disabledLink) {
      event.preventDefault();
      const panel = disabledLink.closest("[data-download]");
      panel
        .querySelector(state.os ? "[data-arch]:not(:disabled)" : "[data-os]")
        ?.focus({ preventScroll: true });
      return;
    }
    const help = event.target.closest(".chip-help button");
    if (help) {
      const isOpen = help.getAttribute("aria-expanded") === "true";
      help.setAttribute("aria-expanded", String(!isOpen));
      help.nextElementSibling.hidden = isOpen;
      return;
    }
    if (event.target.closest("[data-copy-checksum]")) {
      const pkg = packageForState();
      if (!pkg) return;
      try {
        await navigator.clipboard.writeText(pkg.sha256);
        toast(copy.copied);
      } catch (_) {
        const node = document.querySelector(".checksum");
        const range = document.createRange();
        range.selectNodeContents(node);
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
        toast(copy.copyFailed);
      }
      return;
    }
    if (event.target.closest(".menu-toggle")) {
      const open = menuButton.getAttribute("aria-expanded") === "true";
      menuButton.setAttribute("aria-expanded", String(!open));
      mobileNav.hidden = open;
      return;
    }
    if (event.target.closest("#mobile-nav a")) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !mobileNav.hidden) {
      closeMenu();
      menuButton.focus();
      return;
    }
    if (
      ![
        "ArrowLeft",
        "ArrowRight",
        "ArrowUp",
        "ArrowDown",
        "Home",
        "End",
      ].includes(event.key)
    )
      return;
    const target = event.target;
    if (!target.matches("[data-os],[data-scenario],[data-arch]")) return;
    const attr = target.hasAttribute("data-os")
      ? "data-os"
      : target.hasAttribute("data-arch")
        ? "data-arch"
        : "data-scenario";
    const group = target.closest(
      ".os-tabs,.package-options,.scenario-options,.graph-models",
    );
    if (!group) return;
    const buttons = [...group.querySelectorAll(`[${attr}]:not(:disabled)`)];
    const i = buttons.indexOf(target);
    const index =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? buttons.length - 1
          : (i +
              (["ArrowRight", "ArrowDown"].includes(event.key) ? 1 : -1) +
              buttons.length) %
            buttons.length;
    event.preventDefault();
    buttons[index].focus();
    buttons[index].click();
  });
  state.os = detected.os;
  state.arch = initialArch(state.os);
  renderDownloads();
  document.documentElement.classList.add("enhanced");
  if (
    navigator.userAgentData?.getHighEntropyValues &&
    !state.manual &&
    !detected.mobile
  ) {
    const revision = state.revision;
    navigator.userAgentData
      .getHighEntropyValues(["architecture", "bitness"])
      .then((hints) => {
        if (state.manual || state.revision !== revision) return; // Never override a manual choice.
        detected = detectPlatform({
          userAgent: navigator.userAgent,
          platform: navigator.platform,
          hintsPlatform: navigator.userAgentData.platform,
          maxTouchPoints: navigator.maxTouchPoints || 0,
          architecture: hints.architecture,
          bitness: hints.bitness,
        });
        state.os = detected.os;
        state.arch = initialArch(state.os);
        renderDownloads();
      })
      .catch(() => {
        /* The initial detector and manual selector remain usable. */
      });
  }
  window.OMR = Object.freeze({
    detectPlatform,
    getState: () => structuredClone(state),
    getRelease: () => structuredClone(release),
  });
})();
