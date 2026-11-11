import { describe, expect, it } from "vitest";
import { Chat } from "@ai-sdk/react";
import type { UIMessage } from "ai";
import { NativeChatTransport, type NativeChatEvent } from "./chat-transport";

const receipt = {
  request_id: "receipt-fixture",
  status: "completed",
  model_requested: "vendor/exact",
  model_observed: "vendor/exact",
  upstream_status: 200,
};
const text = (role: "user" | "assistant", content: string): UIMessage => ({
  id: crypto.randomUUID(),
  role,
  parts: [{ type: "text", text: content }],
});

describe("native ChatTransport with the real SDK", () => {
  it("streams fragments visibly and sends the entire second turn without HTTP", async () => {
    const requests: Record<string, unknown>[] = [];
    let release!: () => void;
    let polls = 0;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const transport = new NativeChatTransport(
      "direct/connection/model",
      7,
      async (request) => {
        requests.push(request);
        if (request.command === "chat_start") {
          polls = 0;
          return true;
        }
        if (++polls === 1)
          return { events: [{ type: "text", text: "Bon" }], done: false };
        await gate;
        return {
          events: [
            { type: "text", text: "jour" },
            { type: "finish", receipt },
          ],
          done: true,
        };
      },
      () => {},
      0,
    );
    const chat = new Chat({ id: crypto.randomUUID(), transport });
    const first = chat.sendMessage({ text: "First" });
    await expect
      .poll(() => chat.messages[1]?.parts)
      .toEqual([{ type: "text", text: "Bon", state: "streaming" }]);
    expect(chat.status).toBe("streaming");
    release();
    await first;
    expect(chat.status).toBe("ready");
    await chat.sendMessage({ text: "Second" });
    const starts = requests.filter((r) => r.command === "chat_start");
    expect(starts).toHaveLength(2);
    expect(starts[1]).toMatchObject({
      model: "direct/connection/model",
      revision: 7,
      messages: [
        { role: "user", content: "First" },
        { role: "assistant", content: "Bonjour" },
        { role: "user", content: "Second" },
      ],
    });
    expect(await transport.reconnectToStream()).toBeNull();
  });

  it("does not label an incomplete reply ready or retry it", async () => {
    const commands: string[] = [];
    const transport = new NativeChatTransport("direct/c/m", 1, async (r) => {
      commands.push(String(r.command));
      return r.command === "chat_start"
        ? true
        : {
            events: [
              { type: "text", text: "partial" },
              { type: "error", code: "chat_refused", receipt },
            ],
            done: true,
          };
    });
    const chat = new Chat({ transport });
    await chat.sendMessage({ text: "Hello" });
    expect(chat.status).toBe("error");
    expect(chat.error?.message).toBe("chat_refused");
    expect(commands.filter((c) => c === "chat_start")).toHaveLength(1);
  });

  it("cancels native work even when stop races the start acknowledgement", async () => {
    const commands: string[] = [];
    let acknowledge!: () => void;
    const started = new Promise<void>((resolve) => {
      acknowledge = resolve;
    });
    const results: NativeChatEvent[] = [];
    const transport = new NativeChatTransport(
      "direct/c/m",
      1,
      async (r) => {
        commands.push(String(r.command));
        if (r.command === "chat_start") {
          await started;
          return true;
        }
        if (r.command === "chat_cancel") return true;
        return {
          events: [{ type: "error", code: "chat_cancelled" }],
          done: true,
        };
      },
      (event) => results.push(event),
      0,
    );
    const abort = new AbortController();
    const promise = transport.sendMessages({
      trigger: "submit-message",
      chatId: crypto.randomUUID(),
      messages: [text("user", "test")],
      messageId: undefined,
      abortSignal: abort.signal,
    });
    abort.abort();
    acknowledge();
    const stream = await promise;
    await stream.cancel();
    await expect.poll(() => commands.includes("chat_cancel")).toBe(true);
    await expect.poll(() => results.at(-1)?.code).toBe("chat_cancelled");
  });

  it("never labels a completed native race successful after user cancellation", async () => {
    let complete!: () => void;
    const gate = new Promise<void>((resolve) => {
      complete = resolve;
    });
    const results: NativeChatEvent[] = [];
    const transport = new NativeChatTransport(
      "direct/c/m",
      1,
      async (r) => {
        if (r.command !== "chat_poll") return true;
        await gate;
        return { events: [{ type: "finish", receipt }], done: true };
      },
      (event) => results.push(event),
      0,
    );
    const abort = new AbortController();
    const stream = await transport.sendMessages({
      trigger: "submit-message",
      chatId: crypto.randomUUID(),
      messages: [text("user", "test")],
      messageId: undefined,
      abortSignal: abort.signal,
    });
    abort.abort();
    await stream.cancel();
    complete();
    await expect.poll(() => results.at(-1)?.code).toBe("chat_cancelled");
  });

  it("rejects tools, regeneration and raw native errors without leaking them", async () => {
    const transport = new NativeChatTransport("direct/c/m", 1, async () => {
      throw new Error("private-secret-canary");
    });
    const options = {
      trigger: "submit-message" as const,
      chatId: crypto.randomUUID(),
      messages: [text("user", "hello")],
      messageId: undefined,
      abortSignal: undefined,
    };
    const stream = await transport.sendMessages(options);
    await expect(stream.getReader().read()).rejects.toThrow("chat_unavailable");
    await expect(
      transport.sendMessages({ ...options, trigger: "regenerate-message" }),
    ).rejects.toThrow("chat_invalid");
  });
});
