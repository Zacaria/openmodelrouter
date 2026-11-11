import fs from "node:fs";
import path from "node:path";
const root = path.resolve(import.meta.dirname, "..");
const entries = [];
for (const project of [root, path.join(root, "provider-runtime")]) {
  const lock = JSON.parse(
    fs.readFileSync(path.join(project, "package-lock.json"), "utf8"),
  );
  for (const [location, item] of Object.entries(lock.packages)) {
    if (!location || item.dev || item.devOptional) continue;
    const directory = path.join(project, location);
    if (!fs.existsSync(directory)) continue;
    const files = fs
      .readdirSync(directory)
      .filter(
        (name) =>
          /^licen[sc]e(?:[._-].*)?$/i.test(name) &&
          fs.statSync(path.join(directory, name)).isFile(),
      );
    const manifest = JSON.parse(
      fs.readFileSync(path.join(directory, "package.json"), "utf8"),
    );
    const declaration = `Package metadata: ${JSON.stringify({ license: manifest.license, author: manifest.author, repository: manifest.repository })}`;
    entries.push(
      `${location} @ ${item.version}\n${files.length ? files.map((file) => fs.readFileSync(path.join(directory, file), "utf8")).join("\n") : declaration + "\nNo license text was included in this npm package; see the declared upstream license."}`,
    );
  }
}
entries.push(
  fs.readFileSync(
    path.join(
      root,
      "provider-runtime/node_modules/@oh-my-pi/pi-natives/THIRD-PARTY-NOTICES.txt",
    ),
    "utf8",
  ),
);
entries.push(
  fs.readFileSync(path.join(root, "licenses/Bun-LICENSE.md"), "utf8"),
);
entries.push(
  fs.readFileSync(path.join(root, "licenses/React-remove-scroll-bar-2.3.8-LICENSE.txt"), "utf8"),
);
const target = path.join(root, ".sidecar-build", "licenses");
// The AI SDK packages ship an Apache header, not the complete license terms.
entries.push(fs.readFileSync(path.join(root, "licenses/Apache-2.0.txt"), "utf8"));
fs.mkdirSync(target, { recursive: true });
fs.writeFileSync(
  path.join(target, "NPM-LICENSES.txt"),
  entries.join("\n\n----------------\n\n"),
);
console.log(`Collected ${entries.length} dependency notices`);
