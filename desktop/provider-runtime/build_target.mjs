// Bun release targets use aarch64; npm native addons use arm64.
export function runtimeTarget(platform, arch) {
  const os = platform === "win32" ? "windows" : platform;
  const cpu = arch === "arm64" ? "aarch64" : arch;
  return `bun-${os}-${cpu}${arch === "x64" ? "-baseline" : ""}`;
}
