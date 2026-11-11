# Progressive Desktop navigation

## Delivery — 0.3.1

Ship the accepted redesign as a new macOS Apple Silicon 0.3.1 package; do not overwrite the published 0.3.0 bytes. Keep package, npm lock, Cargo manifest/lock and Tauri version aligned. Preserve the existing public downloads for other platforms. Native trust and isolated launch checks apply to the newly built package, independently of the frontend replays below.

## Redesign — 6 November 2026

Use the generated Codex image concept as a composition reference, not as product data. Keep the existing brand asset, engine/IPC, provider setup, consent, autosave and Chat transport unchanged. The generation receipt exposes `image_gen.imagegen`, not an image model version; do not claim a verified GPT Image 2.6 selection.

Adopt warm paper, ink and forest green, with a restrained serif page title, a compact breadcrumb bar and one primary Chat action on État. Replace the oversized overview KPI cards with an inline service summary. Put recent activity and actual configured connections next to each other. Keep client connection details behind an accessible native disclosure; showing a local API key must still require its existing explicit action. The topology must continue distinguishing configured routes from observed requests and blocked profiles; no fictitious active profile, shortcut, provider or usage data from the concept.

Carry the same tokens through Fournisseurs, Chat, advanced screens, dialogs and dark mode. Preserve the 800 × 640 minimum, keyboard focus, contrast and wrapping; use existing system fonts and components, with no new dependencies or external font requests. Verify the frontend with synthetic IPC fixtures separately from native package qualification.

Keep the everyday path visible: État → Fournisseurs → Chat. Réglages stays directly accessible. Group Profils & règles, Stratégies natives, Consommation and Inspecteur under the native **Avancé** disclosure instead of presenting eight equal starting points.

The disclosure starts closed on everyday pages and opens when an advanced page is selected, including native navigation events and existing shortcuts. Keep every destination, its selected state and receipt count; do not clear the chat or alter permissions when navigating. Native disclosure behavior must remain keyboard-accessible. Polling the engine must not close a disclosure the user opened.

The Chat description must name both automatic profiles and direct models. Model ranking remains visible in Fournisseurs; provider onboarding and consent remain unchanged.

Verify initial navigation rendering, keyboard disclosure/navigation, advanced shortcuts and return to Chat on the built frontend. Browser fixtures, native WebView interaction and packaged installation remain separate evidence.
