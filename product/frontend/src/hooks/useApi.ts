/** Lightweight hooks wrapping the typed API client. They never read files
 *  directly and never call fetch() outside the client. Loading / error states
 *  are explicit so each view can render the spec-mandated empty / error UI.
 */
import { useEffect, useState, useCallback } from "react";
import { APIRequestError, api } from "../api/client";

export type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: APIRequestError | null;
};

/** Calls the given function on mount (and when `deps` change). */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null });
  useEffect(() => {
    let alive = true;
    setState({ data: null, loading: true, error: null });
    fn().then((data) => alive && setState({ data, loading: false, error: null }))
        .catch((error) => alive && setState({ data: null, loading: false,
                                                error: error instanceof APIRequestError
                                                  ? error
                                                  : new APIRequestError(0, String(error), "", null) }));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

/** Returns true when the API is reachable, false otherwise. Refresh every 15s.
 *  Treats `{ status: "ok" }` as a positive signal. Never throws. */
export function useApiHealth(): { online: boolean; lastChecked: number } {
  const [online, setOnline] = useState(false);
  const [lastChecked, setLastChecked] = useState(0);
  const check = useCallback(async () => {
    try {
      const h = await api.health();
      setOnline(Boolean(h && typeof h === "object" && h.status === "ok"));
    } catch {
      setOnline(false);
    } finally {
      setLastChecked(Date.now());
    }
  }, []);
  useEffect(() => {
    const t = setInterval(check, 15000);
    return () => clearInterval(t);
  }, [check]);
  return { online, lastChecked };
}
