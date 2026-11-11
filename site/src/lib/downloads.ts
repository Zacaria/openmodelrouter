export type Download = {
  version: string;
  os: "macos" | "windows" | "linux";
  arch: "arm64" | "x64";
  file: string;
  bytes: number;
  sha256: string;
  sourceCommit: string;
  prerelease: boolean | null;
  releaseApproved: boolean;
  native: "verified" | "unverified";
  generation: "verified" | "synthetic-only";
  trust:
    | "macos-notarized"
    | "macos-adhoc-blocked"
    | "windows-signed"
    | "windows-unsigned"
    | "linux-unsigned"
    | "unverified";
  href: string;
};

export const platforms = [
  {
    os: "macos",
    arch: "arm64",
    label: "macOS · Apple Silicon (arm64)",
  },
  {
    os: "macos",
    arch: "x64",
    label: "macOS · Intel (x64)",
  },
  {
    os: "windows",
    arch: "x64",
    label: "Windows · x64",
  },
  { os: "linux", arch: "x64", label: "Linux · x64" },
] as const;
