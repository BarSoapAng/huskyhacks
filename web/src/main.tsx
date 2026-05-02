import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

declare const __BACKEND_URL__: string;

type SessionType = "productive" | "procrastination" | "allowed";

type ActivitySession = {
  id: string;
  type: SessionType;
  timestamp: string;
  active: boolean;
  duration: number;
  visitCount: number | null;
  visits: unknown[] | null;
};

type ActivityVisit = {
  id: string;
  timestamp: string;
  duration: number;
  url: string;
  pageTitle: string;
};

type ActivityResponse = {
  sessions: ActivitySession[];
  visits: ActivityVisit[];
};

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: ActivityResponse }
  | { status: "error"; message: string };

const SESSION_VISUALIZATION_URL = `${__BACKEND_URL__}/api/session-visualization`;
const CREATE_SESSION_URL = `${__BACKEND_URL__}/api/create-session`;

function App() {
  const [state, setState] = React.useState<LoadState>({ status: "loading" });
  const [markState, setMarkState] = React.useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [reloadKey, setReloadKey] = React.useState(0);

  React.useEffect(() => {
    let ignore = false;

    async function loadActivity() {
      try {
        const response = await fetch(SESSION_VISUALIZATION_URL);

        if (ignore) {
          return;
        }

        if (!response.ok) {
          setState({
            status: "error",
            message: "Unable to load session visualization data."
          });
          return;
        }

        const data = (await response.json()) as ActivityResponse;
        setState({ status: "ready", data });
      } catch {
        if (!ignore) {
          setState({
            status: "error",
            message: "Unable to load session visualization data."
          });
        }
      }
    }

    loadActivity();

    return () => {
      ignore = true;
    };
  }, [reloadKey]);

  async function markCurrentSessionAllowed() {
    setMarkState("loading");

    try {
      const response = await fetch(CREATE_SESSION_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ sessionType: "allowed" })
      });

      if (!response.ok) {
        setMarkState("error");
        return;
      }

      setMarkState("success");
      setReloadKey((current) => current + 1);
    } catch {
      setMarkState("error");
    }
  }

  return (
    <main className="activity-page" aria-label="Session activity">
      <header className="page-header">
        <div>
          <p className="eyebrow">Browsing Sessions</p>
          <h1>Session Activity</h1>
        </div>
        <div className="header-actions">
          <button
            className="primary-action"
            type="button"
            onClick={markCurrentSessionAllowed}
            disabled={markState === "loading"}
          >
            {markState === "loading"
              ? "Marking..."
              : "Mark current session as allowed"}
          </button>
          {markState === "success" && (
            <span className="action-status">Session marked as allowed.</span>
          )}
          {markState === "error" && (
            <span className="action-status error">
              Unable to mark session as allowed.
            </span>
          )}
        </div>
      </header>

      {state.status === "loading" && (
        <section className="state-panel" aria-live="polite">
          Loading session activity...
        </section>
      )}

      {state.status === "error" && (
        <section className="state-panel error">{state.message}</section>
      )}

      {state.status === "ready" && <ActivityView data={state.data} />}
    </main>
  );
}

function ActivityView({ data }: { data: ActivityResponse }) {
  const isEmpty = data.sessions.length === 0 && data.visits.length === 0;
  const activeSessions = data.sessions.filter((session) => session.active).length;
  const productiveDuration = sumDuration(data.sessions, "productive");
  const procrastinationDuration = sumDuration(data.sessions, "procrastination");
  const allowedDuration = sumDuration(data.sessions, "allowed");

  if (isEmpty) {
    return (
      <section className="state-panel">
        No recent sessions or visits yet.
      </section>
    );
  }

  return (
    <>
      <section className="summary-grid" aria-label="Session summary">
        <SummaryCard label="Active Sessions" value={String(activeSessions)} />
        <SummaryCard label="Productive Time" value={formatDuration(productiveDuration)} />
        <SummaryCard
          label="Procrastination Time"
          value={formatDuration(procrastinationDuration)}
        />
        <SummaryCard label="Allowed Time" value={formatDuration(allowedDuration)} />
        <SummaryCard label="Recent Visits" value={String(data.visits.length)} />
      </section>

      <section className="activity-section">
        <div className="section-heading">
          <h2>Recent Sessions</h2>
        </div>
        {data.sessions.length > 0 ? (
          <div className="session-list">
            {data.sessions.map((session) => (
              <article className="session-row" key={`${session.type}-${session.id}`}>
                <div className="row-main">
                  <div className="title-line">
                    <span className={`type-dot ${session.type}`} aria-hidden="true" />
                    <h3>{getSessionLabel(session.type)}</h3>
                    {session.active && <span className="active-badge">Active</span>}
                  </div>
                  <p>{formatDateTime(session.timestamp)}</p>
                </div>
                <div className="row-meta">
                  <span>{formatDuration(session.duration)}</span>
                  <span>
                    {session.visitCount === null
                      ? "Visits unavailable"
                      : `${session.visitCount} ${session.visitCount === 1 ? "visit" : "visits"}`}
                  </span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="inline-empty">No recent sessions.</div>
        )}
      </section>

      <section className="activity-section">
        <div className="section-heading">
          <h2>Latest Visits</h2>
        </div>
        {data.visits.length > 0 ? (
          <div className="visit-list">
            {data.visits.map((visit) => (
              <article className="visit-row" key={visit.id}>
                <div className="row-main">
                  <h3>{visit.pageTitle || visit.url}</h3>
                  <a href={visit.url} title={visit.url}>
                    {visit.url}
                  </a>
                </div>
                <div className="row-meta">
                  <span>{formatDuration(visit.duration)}</span>
                  <span>{formatDateTime(visit.timestamp)}</span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="inline-empty">No recent visits.</div>
        )}
      </section>
    </>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function sumDuration(sessions: ActivitySession[], type: SessionType): number {
  return sessions
    .filter((session) => session.type === type)
    .reduce((total, session) => total + (Number(session.duration) || 0), 0);
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "0s";
  }

  const totalSeconds = Math.round(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remainingSeconds = totalSeconds % 60;
  const parts: string[] = [];

  if (hours > 0) {
    parts.push(`${hours}h`);
  }

  if (minutes > 0) {
    parts.push(`${minutes}m`);
  }

  if (remainingSeconds > 0 || parts.length === 0) {
    parts.push(`${remainingSeconds}s`);
  }

  return parts.slice(0, 2).join(" ");
}

function formatDateTime(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "Unknown time";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function getSessionLabel(type: SessionType): string {
  const labels: Record<SessionType, string> = {
    productive: "Productive",
    procrastination: "Procrastination",
    allowed: "Allowed"
  };
  return labels[type];
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
