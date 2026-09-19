/** Page-level error boundary. The Stage 1 + Stage 2 safety guarantees must
 *  never crash the entire UI. This boundary isolates a per-page failure
 *  so the sidebar, audit page, and other pages remain accessible even if
 *  one page throws (for example if a malformed API response leaks through
 *  and an array method is called on undefined).
 */
import { Component, type ErrorInfo, type ReactNode } from "react";

interface State { error: Error | null; }

export class PageErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Honest: log to the console. The page is now in a recoverable state.
    console.error("PageErrorBoundary caught:", error, info);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="page" role="alert" aria-live="polite">
          <header className="page__head">
            <h1 className="page__title">Page error</h1>
            <p className="page__lede">
              This view could not be rendered. The other pages remain
              available via the sidebar. The rest of the system is unaffected.
            </p>
          </header>
          <pre className="error-detail">{String(this.state.error.message ?? this.state.error)}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}
