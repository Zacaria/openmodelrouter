import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

export const R15_SOURCE_DELTA_SHA256 =
  "be5e73c9cfabf50d11ce3a8d2b9fdebf743344b5d4fc6d1a19de8668e3f51c6d";

/** Copy exactly the verified buffer; an absent input never creates a link target. */
export async function stageR15Materials(
  source: string | undefined,
  destination: string,
  expectedSha256 = R15_SOURCE_DELTA_SHA256,
): Promise<boolean> {
  if (!source) return false;
  const bytes = await readFile(source);
  const digest = createHash("sha256").update(bytes).digest("hex");
  if (digest !== expectedSha256) throw new Error("R15 source delta differs");
  const directory = join(destination, "assets/materials/0.3.2");
  await mkdir(directory, { recursive: true });
  await writeFile(join(directory, "rebuild.tar"), bytes, { flag: "wx" });
  return true;
}
