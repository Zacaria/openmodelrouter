import type { Config, Snapshot } from "./types";
import type { deciderTarget } from "./components/onboarding";

export type Grant = ReturnType<typeof deciderTarget>;
export type SaveStatus = "saved" | "pending" | "saving" | "error";
type Edit = { config: Config; grant: Grant; version: number };

// One writer for both automatic edits and explicit onboarding persistence.
export class ConfigAutosave {
  private revision = 0;
  private version = 0;
  private pending: Edit | null = null;
  private running: Promise<void> | null = null;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private error: unknown = null;
  private accepted: Snapshot | null = null;
  private paused = 0;
  constructor(
    private write: (
      config: Config,
      revision: number,
      grant: Grant,
    ) => Promise<Snapshot>,
    private onSaved: (snapshot: Snapshot, current: boolean) => void,
    private onStatus: (status: SaveStatus, error?: unknown) => void,
  ) {}
  reset(snapshot: Snapshot) {
    this.dispose();
    this.pending = null;
    this.error = null;
    this.revision = snapshot.revision;
    this.accepted = snapshot;
    this.onStatus("saved");
  }
  edit(config: Config, grant: Grant) {
    this.pending = { config, grant, version: ++this.version };
    this.error = null;
    this.onStatus("pending");
    this.schedule();
  }
  private schedule() {
    this.dispose();
    if (this.paused || this.error || !this.pending) return;
    this.timer = setTimeout(() => {
      void this.flush().catch(() => {});
    }, 350);
  }
  dispose() {
    clearTimeout(this.timer);
    this.timer = undefined;
  }
  async run<T>(action: () => Promise<T>): Promise<T> {
    this.paused++;
    try {
      await this.flush();
      return await action();
    } finally {
      this.paused--;
      this.schedule();
    }
  }
  async discard() {
    this.dispose();
    this.pending = null;
    await this.running?.catch(() => {});
    this.error = null;
    this.onStatus("saved");
    return this.accepted;
  }
  async flush(): Promise<void> {
    this.dispose();
    if (this.running) {
      await this.running;
      return this.flush();
    }
    if (this.error) throw this.error;
    if (!this.pending) return;
    this.running = this.drain();
    try {
      await this.running;
    } finally {
      this.running = null;
    }
  }
  private async drain() {
    while (this.pending) {
      const edit = this.pending;
      this.onStatus("saving");
      let snapshot: Snapshot;
      try {
        snapshot = await this.write(edit.config, this.revision, edit.grant);
      } catch (error) {
        this.error = error;
        this.dispose();
        this.onStatus("error", error);
        throw error;
      }
      this.accepted = snapshot;
      this.revision = snapshot.revision;
      const current = this.pending?.version === edit.version;
      if (current) this.pending = null;
      this.onSaved(snapshot, current);
    }
    this.onStatus("saved");
  }
}
