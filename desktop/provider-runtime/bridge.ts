// One request per process. Secrets only enter through private stdin.
import { logger } from "@oh-my-pi/pi-utils";
import type { FetchImpl, SimpleStreamOptions } from "@oh-my-pi/pi-ai/types";
logger.setTransports({ console: false, file: false });

const metadata: {
  model: string | null;
  model_conflict: boolean;
  usage: Record<string, unknown>;
  status: number | null;
} = { model: null, model_conflict: false, usage: {}, status: null };
function emit(value: string | Uint8Array) {
  const bytes = Buffer.from(value);
  for (let i = 0; i < bytes.length; i += 49152) {
    process.stdout.write(
      JSON.stringify({
        chunk: bytes.subarray(i, i + 49152).toString("base64"),
      }) + "\n",
    );
  }
}
function observeWire(data: string) {
  try {
    const event = JSON.parse(data);
    for (const observed of [event, event.response, event.message]) {
      if (typeof observed?.model !== "string") continue;
      const model = observed.model;
      if (!/^[A-Za-z0-9_./:@+-]{1,256}$/.test(model)) {
        metadata.model_conflict = true;
      } else if (metadata.model === null) {
        metadata.model = model;
      } else if (metadata.model !== model) {
        metadata.model_conflict = true;
      }
    }
    const value = event.response ?? event.message ?? event;
    const usage = value.usage;
    if (!usage || typeof usage !== "object") return;
    for (const key of [
      "input_tokens",
      "output_tokens",
      "prompt_tokens",
      "completion_tokens",
      "total_tokens",
      "cache_creation_input_tokens",
      "cache_read_input_tokens",
    ]) {
      if (
        Number.isSafeInteger(usage[key]) &&
        usage[key] >= 0 &&
        usage[key] <= 1e12
      )
        metadata.usage[key] = usage[key];
    }
    for (const [key, child] of [
      ["input_tokens_details", "cached_tokens"],
      ["prompt_tokens_details", "cached_tokens"],
      ["output_tokens_details", "reasoning_tokens"],
      ["completion_tokens_details", "reasoning_tokens"],
    ]) {
      const number = usage[key]?.[child];
      if (Number.isSafeInteger(number) && number >= 0 && number <= 1e12)
        metadata.usage[key] = { [child]: number };
    }
  } catch {
    /* Non-JSON SSE markers carry no observations. */
  }
}

let began = false;
function head(status: number, type = "application/json") {
  began = true;
  process.stdout.write(JSON.stringify({ status, type }) + "\n");
}
function fail() {
  if (!began) head(502);
  emit('{"error":{"type":"pi_ai_error","message":"Provider request failed."}}');
}

class UnsupportedInput extends Error {}

type ObjectValue = Record<string, unknown>;
function object(value: unknown): value is ObjectValue {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function fields(value: unknown, keys: string[]): value is ObjectValue {
  return object(value) && Object.keys(value).every((key) => keys.includes(key));
}
function list(value: unknown, valid: (item: unknown) => boolean): boolean {
  return Array.isArray(value) && value.every(valid);
}
function text(value: unknown, types: string[]): boolean {
  return (
    fields(value, ["type", "text", "annotations"]) &&
    types.includes(String(value.type)) &&
    typeof value.text === "string" &&
    (value.annotations === undefined ||
      (Array.isArray(value.annotations) && value.annotations.length === 0))
  );
}
function content(value: unknown, types: string[]): boolean {
  return typeof value === "string" || list(value, (part) => text(part, types));
}

// Only the single-provider, no-fallback, zero-price Chat contract is qualified.
// Keep it outside parseRequest: the generic SDK parser drops this extension.
function qualifiedProvider(value: unknown): boolean {
  return (
    fields(value, ["only", "allow_fallbacks", "max_price"]) &&
    Array.isArray(value.only) &&
    value.only.length === 1 &&
    typeof value.only[0] === "string" &&
    value.only[0].length > 0 &&
    value.only[0].length <= 128 &&
    !/[^a-z0-9._/-]/.test(value.only[0]) &&
    value.allow_fallbacks === false &&
    fields(value.max_price, ["prompt", "completion"]) &&
    value.max_price.prompt === 0 &&
    value.max_price.completion === 0
  );
}

// Validate wire envelopes, not arbitrary JSON inside arguments/parameter schemas.
// The upstream parsers intentionally accept/flatten more variants than this
// text/function-only transport qualifies. Never let that become silent success.
function qualifiedInput(protocol: string, body: ObjectValue): boolean {
  if (
    body.tools !== undefined &&
    !list(body.tools, (tool) => {
      if (protocol === "chat")
        return (
          fields(tool, ["type", "function"]) &&
          tool.type === "function" &&
          fields(tool.function, ["name", "description", "parameters"])
        );
      if (protocol === "responses")
        return (
          fields(tool, [
            "type",
            "name",
            "description",
            "parameters",
            "strict",
          ]) && tool.type === "function"
        );
      return fields(tool, ["name", "description", "input_schema"]);
    })
  )
    return false;

  const choice = body.tool_choice;
  if (choice !== undefined) {
    if (protocol === "anthropic") {
      if (
        !fields(choice, ["type", "name"]) ||
        !["auto", "any", "none", "tool"].includes(String(choice.type)) ||
        (choice.type === "tool"
          ? typeof choice.name !== "string"
          : "name" in choice)
      )
        return false;
    } else if (typeof choice === "string") {
      if (!["auto", "none", "required"].includes(choice)) return false;
    } else if (protocol === "responses") {
      if (
        !fields(choice, ["type", "name"]) ||
        choice.type !== "function" ||
        typeof choice.name !== "string"
      )
        return false;
    } else if (!(
      (fields(choice, ["type", "function"]) &&
        choice.type === "function" &&
        fields(choice.function, ["name"]) &&
        typeof choice.function.name === "string") ||
      (fields(choice, ["type", "name"]) &&
        choice.type === "tool" &&
        typeof choice.name === "string")
    ))
      return false;
  }

  if (protocol === "responses") {
    if (typeof body.input === "string") return true;
    return list(body.input, (item) => {
      if (!object(item)) return false;
      if (item.type === "function_call")
        return (
          fields(item, [
            "type",
            "id",
            "call_id",
            "name",
            "arguments",
            "status",
          ]) && typeof item.arguments === "string"
        );
      if (item.type === "function_call_output")
        return (
          fields(item, ["type", "id", "call_id", "output", "status"]) &&
          content(item.output, ["text", "input_text"])
        );
      return (
        fields(item, ["type", "role", "content", "id", "status"]) &&
        (item.type === undefined || item.type === "message") &&
        ["system", "developer", "user", "assistant"].includes(
          String(item.role),
        ) &&
        content(
          item.content,
          item.role === "assistant"
            ? ["text", "output_text"]
            : ["text", "input_text"],
        )
      );
    });
  }
  if (protocol === "chat") {
    return list(body.messages, (message) => {
      if (
        !fields(message, [
          "role",
          "content",
          "tool_calls",
          "tool_call_id",
          "name",
        ]) ||
        !["system", "developer", "user", "assistant", "tool"].includes(
          String(message.role),
        ) ||
        !(
          content(message.content, ["text"]) ||
          (message.role === "assistant" && message.content == null)
        )
      )
        return false;
      if (message.tool_calls === undefined) return true;
      return (
        message.role === "assistant" &&
        list(
          message.tool_calls,
          (call) =>
            fields(call, ["id", "type", "function"]) &&
            call.type === "function" &&
            fields(call.function, ["name", "arguments"]) &&
            typeof call.function.arguments === "string",
        )
      );
    });
  }
  if (body.system !== undefined && !content(body.system, ["text"]))
    return false;
  return list(body.messages, (message) => {
    if (
      !fields(message, ["role", "content"]) ||
      !["user", "assistant"].includes(String(message.role))
    )
      return false;
    if (typeof message.content === "string") return true;
    return list(message.content, (block) => {
      if (text(block, ["text"])) return true;
      if (!object(block)) return false;
      if (message.role === "assistant" && block.type === "tool_use")
        return (
          fields(block, ["type", "id", "name", "input"]) && object(block.input)
        );
      if (message.role === "user" && block.type === "tool_result")
        return (
          fields(block, ["type", "tool_use_id", "content", "is_error"]) &&
          (block.content === undefined || content(block.content, ["text"]))
        );
      return false;
    });
  });
}

let control = false;
try {
  const request = JSON.parse(await Bun.stdin.text());
  if (request.action) {
    control = true;
    const { subscriptionAction } = await import("./subscriptions");
    await subscriptionAction(request);
  } else {
  const { protocol, url, key, body } = request;
  const codex = request.subscription === "codex";
  if (request.subscription && !codex) throw new Error();
  if (codex && (url !== "https://chatgpt.com/backend-api/codex" || !key)) throw new Error();
  const formats = {
    responses:
      await import("@oh-my-pi/pi-ai/providers/openai-responses-server"),
    chat: await import("@oh-my-pi/pi-ai/providers/openai-chat-server"),
    anthropic:
      await import("@oh-my-pi/pi-ai/providers/anthropic-messages-server"),
  };
  const format = formats[protocol as keyof typeof formats];
  if (!format) throw new Error();
  // Only fields explicitly carried by this bridge may pass. Fail closed rather
  // than let a format parser silently discard a client instruction.
  const allowed = {
    responses: [
      "model",
      "input",
      "instructions",
      "stream",
      "tools",
      "tool_choice",
      "max_output_tokens",
      "temperature",
      "top_p",
      "reasoning",
      "store",
    ],
    chat: [
      "model",
      "messages",
      "stream",
      "tools",
      "tool_choice",
      "max_tokens",
      "max_completion_tokens",
      "temperature",
      "top_p",
      "stop",
      "reasoning_effort",
      "stream_options",
      "provider",
      "store",
    ],
    anthropic: [
      "model",
      "messages",
      "system",
      "stream",
      "tools",
      "tool_choice",
      "max_tokens",
      "temperature",
      "top_p",
      "top_k",
      "stop_sequences",
    ],
  }[protocol as "responses" | "chat" | "anthropic"];
  const unsupportedReasoning =
    body.reasoning && Object.keys(body.reasoning).some((k) => k !== "effort");
  const unsupportedStreamOptions =
    body.stream_options &&
    Object.keys(body.stream_options).some((k) => k !== "include_usage");
  if (
    Object.keys(body).some((k) => !allowed.includes(k)) ||
    ("store" in body && body.store !== false) ||
    unsupportedReasoning ||
    unsupportedStreamOptions ||
    ("provider" in body && !qualifiedProvider(body.provider)) ||
    !qualifiedInput(protocol, body)
  ) {
    head(400);
    emit(
      '{"error":{"type":"unsupported_pi_ai_option","message":"Request option is not supported by this transport."}}',
    );
  } else {
    const parsed = (() => {
      try {
        return format.parseRequest(body, new Headers());
      } catch {
        throw new UnsupportedInput();
      }
    })();
    const { buildModel } = await import("@oh-my-pi/pi-catalog/build");
    const { streamSimple } = await import("@oh-my-pi/pi-ai/stream");
    const api = {
      responses: "openai-responses",
      chat: "openai-completions",
      anthropic: "anthropic-messages",
    }[protocol as "responses" | "chat" | "anthropic"];
    const model = buildModel({
      id: body.model,
      name: body.model,
      api: codex ? "openai-codex-responses" : api,
      provider: codex ? "openai-codex" : protocol === "anthropic" ? "anthropic" : "openai",
      baseUrl: url,
      reasoning: !!parsed.options.reasoning,
      input: ["text"],
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      contextWindow: 32000,
      maxTokens: 32000,
    });
    const endpoint =
      url +
      (codex ? "/responses" : {
        responses: "/responses",
        chat: "/chat/completions",
        anthropic: "/messages",
      }[protocol as "responses" | "chat" | "anthropic"]);
    let fetched = false;
    // Every retry/fallback is denied at the actual network boundary. No redirects,
    // ambient auth, proxy env, alternate URL, or second inference request.
    const guardedFetch: FetchImpl = async (input, init) => {
      const target = input instanceof Request ? input.url : String(input);
      if (fetched || target !== endpoint)
        throw new Error("pi_ai_network_policy");
      if (
        body.store === false &&
        (typeof init?.body !== "string" || JSON.parse(init.body).store !== false)
      )
        throw new UnsupportedInput();
      fetched = true;
      const headers = new Headers(
        init?.headers ?? (input instanceof Request ? input.headers : undefined),
      );
      if (!key) {
        headers.delete("authorization");
        headers.delete("x-api-key");
      }
      const response = await fetch(input, {
        ...init,
        headers,
        redirect: "manual",
      });
      metadata.status = response.status;
      return response;
    };
    const o = parsed.options;
    const options: SimpleStreamOptions = {
      preferWebsockets: false,
      apiKey: key || "omr-no-auth",
      fetch: guardedFetch,
      onSseEvent: (event) => observeWire(event.data),
      maxRetryDelayMs: 0,
      cacheRetention: "none",
      // This public hook runs after SDK request conversion, before serialization.
      onPayload:
        body.provider === undefined && body.store === undefined
          ? undefined
          : (payload) => {
              if (!object(payload)) throw new UnsupportedInput();
              if (body.provider !== undefined) payload.provider = body.provider;
              if (body.store === false) payload.store = false;
              return payload;
            },
      maxTokens: o.maxOutputTokens,
      temperature: o.temperature,
      topP: o.topP,
      topK: o.topK,
      stopSequences: o.stopSequences,
      reasoning: o.reasoning,
      disableReasoning: o.forceReasoningOff ?? o.disableReasoning,
      toolChoice:
        o.toolChoice &&
        typeof o.toolChoice === "object" &&
        !("type" in o.toolChoice)
          ? { type: "tool", name: o.toolChoice.name }
          : o.toolChoice,
    };
    const events = streamSimple(model, parsed.context, options);
    if (parsed.stream) {
      // Prime the adapter before emitting HTTP success. Failures never carry raw
      // provider bodies through pi-ai's error encoder.
      const iterator = events[Symbol.asyncIterator]();
      const first = await iterator.next();
      if (first.done || first.value.type === "error") throw new Error();
      head(200, "text/event-stream");
      const safeEvents = {
        async *[Symbol.asyncIterator]() {
          yield first.value;
          for (;;) {
            const next = await iterator.next();
            if (next.done) return;
            if (next.value.type === "error") throw new Error("pi_ai_error");
            yield next.value;
          }
        },
      };
      try {
        const response = format.encodeStream(
          safeEvents as never,
          model.id,
          parsed.options,
        );
        for await (const chunk of response) emit(chunk);
      } catch {
        emit(
          'event: error\ndata: {"type":"error","error":{"type":"pi_ai_error","message":"Provider stream failed."}}\n\n',
        );
      }
    } else {
      const message = await events.result();
      if (message.stopReason === "error" || message.stopReason === "aborted")
        throw new Error();
      head(200);
      emit(JSON.stringify(format.encodeResponse(message, model.id)));
    }
  }
  }
} catch (error) {
  if (control) {
    process.stdout.write('{"error":"subscription_failed"}\n');
    process.exitCode = 1;
  } else if (error instanceof UnsupportedInput && !began) {
    head(400);
    emit(
      '{"error":{"type":"unsupported_pi_ai_option","message":"Request option is not supported by this transport."}}',
    );
  } else fail();
} finally {
  if (!control) process.stdout.write(JSON.stringify({ metadata }) + "\n");
}
