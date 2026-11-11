// Build only for this host; native replays remain OS-specific.
import {
  cpSync,
  existsSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { runtimeTarget } from "./build_target.mjs";

const nativeDir = join(
  "node_modules",
  "@oh-my-pi",
  `pi-natives-${process.platform}-${process.arch}`,
);
const nativeFiles = readdirSync(nativeDir).filter(
  (name) => name.endsWith(".node") && !name.includes("modern"),
);
if (nativeFiles.length !== 1)
  throw new Error(
    "Expected one pinned baseline/default native addon for this host",
  );
const native = nativeFiles[0];
cpSync(join(nativeDir, native), native);
const target = runtimeTarget(process.platform, process.arch);
const output = process.platform === "win32" ? "omr-pi.exe" : "omr-pi";
// Explicitly use the supplied executable, including modified library builds.
// --target alone may download an upstream Bun and defeat local relinking.
const executable = resolve(
  process.env.OMR_BUN_EXECUTABLE_PATH || process.execPath,
);
if (!existsSync(executable))
  throw new Error("Missing Bun replacement executable");
const sha256 = (file) =>
  createHash("sha256").update(readFileSync(file)).digest("hex");
const revision = spawnSync(executable, ["--revision"], { encoding: "utf8" });
if (revision.status !== 0)
  throw new Error("Invalid Bun replacement executable");
const build = spawnSync(
  process.execPath,
  [
    "build",
    "bridge.ts",
    "--compile",
    `--target=${target}`,
    `--compile-executable-path=${executable}`,
    "--outfile",
    output,
  ],
  { stdio: "inherit" },
);
if (build.status !== 0) process.exit(build.status ?? 1);
writeFileSync(
  "runtime-build.json",
  JSON.stringify(
    {
      schema: 1,
      target,
      revision: revision.stdout.trim(),
      executable_sha256: sha256(executable),
      compiler_sha256: sha256(process.execPath),
      bridge_sha256: sha256("bridge.ts"),
      lock_sha256: sha256("package-lock.json"),
      native: { file: native, sha256: sha256(native) },
      output: { file: output, sha256: sha256(output) },
    },
    null,
    2,
  ) + "\n",
);
