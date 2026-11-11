import { describe, expect, it, vi } from "vitest";
import { ConfigAutosave } from "./config-autosave";
import type { Config, Snapshot } from "./types";

const config = {
  connections: [],
  decider: null,
  expected_output: 1,
} as unknown as Config;
const snapshot = (value: Config, revision: number) =>
  ({ config: value, revision }) as Snapshot;
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

describe("automatic config persistence", () => {
  it("coalesces edits, serializes writes with CAS and does not replace a newer draft", async () => {
    vi.useFakeTimers();
    const first = deferred<Snapshot>();
    const write = vi
      .fn()
      .mockReturnValueOnce(first.promise)
      .mockImplementation(async (c: Config, r: number) => snapshot(c, r + 1));
    const accepted = vi.fn();
    const queue = new ConfigAutosave(write, accepted, () => {});
    queue.reset(snapshot(config, 4));
    queue.edit({ ...config, expected_output: 2 }, null);
    queue.edit({ ...config, expected_output: 3 }, null);
    await vi.advanceTimersByTimeAsync(350);
    expect(write).toHaveBeenCalledTimes(1);
    expect(write.mock.calls[0][0].expected_output).toBe(3);
    queue.edit({ ...config, expected_output: 4 }, null);
    queue.edit({ ...config, expected_output: 5 }, null);
    const flushed = queue.flush();
    first.resolve(snapshot({ ...config, expected_output: 3 }, 5));
    await flushed;
    expect(write).toHaveBeenCalledTimes(2);
    expect(write.mock.calls[1][0].expected_output).toBe(5);
    expect(write.mock.calls[1][1]).toBe(5);
    expect(accepted.mock.calls.map((call) => call[1])).toEqual([false, true]);
    queue.dispose();
    vi.useRealTimers();
  });
  it("flushes before an action, retains edits during it and blocks the action on invalid/CAS refusal without retrying", async () => {
    const order: string[] = [];
    const action = deferred<void>();
    const write = vi.fn(async (c: Config, r: number) => {
      order.push("save");
      return snapshot(c, r + 1);
    });
    const queue = new ConfigAutosave(
      write,
      () => {},
      () => {},
    );
    queue.reset(snapshot(config, 7));
    queue.edit({ ...config, expected_output: 2 }, null);
    const run = queue.run(async () => {
      order.push("action");
      await action.promise;
    });
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
    expect(order).toEqual(["save", "action"]);
    queue.edit({ ...config, expected_output: 3 }, null);
    expect(write).toHaveBeenCalledTimes(1);
    action.resolve();
    await run;
    await queue.flush();
    expect(write.mock.calls[1][1]).toBe(8);
    const refusal = new Error("configuration_file_conflict");
    write.mockRejectedValueOnce(refusal);
    queue.edit({ ...config, expected_output: 0 }, null);
    const blocked = vi.fn();
    await expect(queue.run(blocked)).rejects.toBe(refusal);
    await expect(queue.flush()).rejects.toBe(refusal);
    expect(blocked).not.toHaveBeenCalled();
    expect(write).toHaveBeenCalledTimes(3);
    queue.edit({ ...config, expected_output: 4 }, null);
    await queue.flush();
    expect(write.mock.calls[3][1]).toBe(9);
    queue.dispose();
  });
  it("discards pending edits only after the in-flight accepted snapshot, and resets the CAS after external reload", async () => {
    const saved = deferred<Snapshot>();
    const write = vi
      .fn()
      .mockReturnValueOnce(saved.promise)
      .mockImplementation(async (c: Config, r: number) => snapshot(c, r + 1));
    const queue = new ConfigAutosave(
      write,
      () => {},
      () => {},
    );
    queue.reset(snapshot(config, 2));
    queue.edit({ ...config, expected_output: 2 }, null);
    const flush = queue.flush();
    queue.edit({ ...config, expected_output: 3 }, null);
    const discard = queue.discard();
    saved.resolve(snapshot({ ...config, expected_output: 2 }, 3));
    await flush;
    expect((await discard)?.config.expected_output).toBe(2);
    expect(write).toHaveBeenCalledTimes(1);
    queue.reset(snapshot(config, 20));
    queue.edit(config, { mode: "managed", model: "explicit-consent" });
    await queue.flush();
    expect(write.mock.calls[1][1]).toBe(20);
    expect(write.mock.calls[1][2]).toEqual({
      mode: "managed",
      model: "explicit-consent",
    });
    queue.dispose();
  });
});
