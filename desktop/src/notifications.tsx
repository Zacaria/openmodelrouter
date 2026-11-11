import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { Toast } from "radix-ui";
import { CheckCircle2, CircleAlert, X } from "lucide-react";

type Tone = "success" | "error";
type Notice = { id: number; message: string; tone: Tone };
type Notify = (message: string, tone?: Tone) => () => void;
const Notifications = createContext<Notify>(() => {
  throw new Error("NotificationsProvider is required");
});

export const useNotify = () => useContext(Notifications);

// State errors are announced on transition, not on every background poll.
export function useErrorToast(message: string | undefined) {
  const notify = useNotify();
  useEffect(() => {
    if (message) return notify(message, "error");
  }, [message, notify]);
}

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [queue, setQueue] = useState<Notice[]>([]);
  const [compact, setCompact] = useState(
    () => window.matchMedia("(max-height: 599px)").matches,
  );
  useEffect(() => {
    const query = window.matchMedia("(max-height: 599px)");
    const update = () => setCompact(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  const visibleCount = compact ? 1 : 3;
  const nextId = useRef(0);
  const notify = useCallback<Notify>((message, tone = "success") => {
    if (!message) return () => {};
    const notice = { id: ++nextId.current, message, tone };
    setQueue((current) => [...current, notice]);
    return () =>
      setQueue((items) => items.filter((item) => item.id !== notice.id));
  }, []);
  // New notices are visible immediately, even behind earlier errors. Overflow
  // is retained and gets its full duration when it returns to the visible set.
  return (
    <Notifications.Provider value={notify}>
      {children}
      {queue.length > 0 && (
        <Toast.Provider
          label="Notification"
          duration={6000}
          swipeDirection="right"
        >
          {queue.slice(-visibleCount).map((current, index) => (
            <Toast.Root
              key={current.id}
              className={`alert toast ${current.tone}`}
              style={{ pointerEvents: "auto" }}
              type={current.tone === "error" ? "foreground" : "background"}
              duration={current.tone === "error" ? 10000 : 6000}
              open
              onOpenChange={(open) => {
                if (!open)
                  setQueue((items) =>
                    items.filter((item) => item.id !== current.id),
                  );
              }}
            >
              {current.tone === "error" ? (
                <CircleAlert size={18} aria-hidden="true" />
              ) : (
                <CheckCircle2 size={18} aria-hidden="true" />
              )}
              <div className="toast-content">
                <Toast.Description className="toast-message">
                  {current.message}
                </Toast.Description>
                {index === visibleCount - 1 && queue.length > visibleCount && (
                  <small>
                    {queue.length - visibleCount} notification(s) en attente
                  </small>
                )}
              </div>
              <Toast.Close
                className="toast-close"
                aria-label={
                  current.tone === "error"
                    ? "Masquer l’erreur"
                    : "Masquer la notification"
                }
              >
                <X size={16} aria-hidden="true" />
              </Toast.Close>
            </Toast.Root>
          ))}
          {createPortal(
            <Toast.Viewport
              className="toast-viewport"
              label="Notifications ({hotkey})"
              aria-live="off"
            />,
            document.body,
          )}
        </Toast.Provider>
      )}
    </Notifications.Provider>
  );
}
