/** Common UI primitives. Typography-driven hierarchy, no decorative chrome. */
import type { ReactNode } from "react";
import { APIRequestError } from "../api/client";

export function StatusPill({ tone, children }: { tone: "ok" | "warn" | "bad" | "info"; children: ReactNode }): ReactNode {
  return <span className={`pill pill--${tone}`}>{children}</span>;
}

export function SeverityBadge({ severity }: { severity: string }): ReactNode {
  const s = (severity || "").toLowerCase();
  const cls = s === "critical" ? "bad" : s === "warning" ? "warn" : s === "watch" ? "info" : "neutral";
  return <span className={`status-text status-text--${cls}`}>{severity}</span>;
}

export function ErrorBanner({ error, title }: { error: unknown; title?: string }): ReactNode {
  if (!error) return null;
  const isAPI = error instanceof APIRequestError;
  return (
    <div className="banner banner--bad" role="alert">
      <strong>{title ?? (isAPI ? "API ERROR" : "ERROR")}</strong>
      <div className="banner__detail">
        {isAPI ? `HTTP ${error.status} on ${error.path}: ${error.detail}` : String((error as Error).message ?? error)}
      </div>
    </div>
  );
}

export function LoadingState({ rows = 3, label = "Loading…" }: { rows?: number; label?: string }): ReactNode {
  return (
    <div className="loading" aria-busy="true" aria-live="polite">
      <div className="loading__label">{label}</div>
      <div className="loading__bars">
        {Array.from({ length: rows }).map((_, i) => <div key={i} className="loading__bar" />)}
      </div>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }): ReactNode {
  return (
    <div className="empty">
      <div className="empty__title">{title}</div>
      {hint ? <div className="empty__hint">{hint}</div> : null}
    </div>
  );
}

export function Card({ title, subtitle, children, aside }: {
  title?: string; subtitle?: string; children: ReactNode; aside?: ReactNode;
}): ReactNode {
  return (
    <section className="card">
      {(title || subtitle || aside) ? (
        <div className="card__head">
          <div>
            {title ? <div className="card__title">{title}</div> : null}
            {subtitle ? <div className="card__subtitle">{subtitle}</div> : null}
          </div>
          {aside}
        </div>
      ) : null}
      <div className="card__body">{children}</div>
    </section>
  );
}

export function DataTable<T>({ columns, rows, keyFn, empty }: {
  columns: Array<{ key: string; label: string; render: (r: T) => ReactNode; align?: "left" | "right" | "center" }>;
  rows: T[]; keyFn: (r: T) => string; empty?: string;
}): ReactNode {
  const safe = Array.isArray(rows) ? rows : [];
  if (safe.length === 0) return <EmptyState title="No records" hint={empty} />;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>{columns.map((c) => (
            <th key={c.key} style={{ textAlign: c.align ?? "left" }}>{c.label}</th>
          ))}</tr>
        </thead>
        <tbody>
          {safe.map((r) => (
            <tr key={keyFn(r)}>
              {columns.map((c) => (
                <td key={c.key} style={{ textAlign: c.align ?? "left" }}>{c.render(r)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
