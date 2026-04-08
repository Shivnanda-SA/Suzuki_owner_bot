"use client";

import type { CSSProperties } from "react";
import { useCallback, useMemo, useState } from "react";

/** Same-origin `/api-backend` avoids CORS during local dev (see next.config rewrites). Set NEXT_PUBLIC_API_URL for direct API (e.g. production). */
const API = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "/api-backend";

type Citation = {
  title: string;
  doc_type: string;
  source_url: string;
  section_title?: string | null;
  excerpt: string;
};

type CTA = { type: string; label: string; payload?: Record<string, unknown> };

type ChatResponse = {
  intent: string;
  answer: string;
  citations: Citation[];
  confidence: string;
  cta: CTA | null;
  needs_handoff: boolean;
  disclaimer?: string | null;
  session_id?: string | null;
};

const MODELS = ["Access 125", "Gixxer SF 250", "Other / not listed"];

const QUICK_PROMPTS: { label: string; text: string }[] = [
  { label: "First service", text: "When is my first service due for my Suzuki scooter?" },
  { label: "Warranty", text: "What does Suzuki warranty cover and what is excluded?" },
  { label: "Service center", text: "How do I find an authorized Suzuki service center in Pune?" },
  { label: "Campaign", text: "How do I check if my vehicle has a service campaign?" },
  { label: "Support", text: "How do I contact Suzuki customer support in India?" },
];

export function OwnerDashboard() {
  const [model, setModel] = useState(MODELS[0]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string; meta?: ChatResponse }[]>(
    []
  );
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const send = useCallback(
    async (text: string) => {
      const q = text.trim();
      if (!q) return;
      setError(null);
      setLoading(true);
      setMessages((m) => [...m, { role: "user", text: q }]);
      try {
        const res = await fetch(`${API}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: q,
            session_id: sessionId,
            vehicle_model: model === MODELS[2] ? null : model,
          }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error((err as { detail?: string }).detail || res.statusText);
        }
        const data = (await res.json()) as ChatResponse;
        if (data.session_id) setSessionId(data.session_id);
        setMessages((m) => [...m, { role: "assistant", text: data.answer, meta: data }]);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Request failed");
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            text: "Sorry — I could not reach the support service. Check API URL and network.",
          },
        ]);
      } finally {
        setLoading(false);
        setInput("");
      }
    },
    [model, sessionId]
  );

  const lastMeta = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && messages[i].meta) return messages[i].meta;
    }
    return undefined;
  }, [messages]);

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <div style={styles.kicker}>Suzuki Motorcycle India</div>
          <h1 style={styles.title}>
            Owner <span style={styles.titleAccent}>Support</span>
          </h1>
          <p style={styles.sub}>
            Post-purchase help: manuals, service, warranty, and service centers. PoC — answers cite synthetic /
            public-style seed content.
          </p>
        </div>
        <div style={styles.headerCard}>
          <div style={styles.muted}>Selected vehicle</div>
          <select value={model} onChange={(e) => setModel(e.target.value)} style={styles.select}>
            {MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <div style={{ marginTop: 12 }}>
            <a href="https://www.suzukimotorcycle.co.in/" target="_blank" rel="noreferrer" style={styles.linkBtn}>
              Official site
            </a>
          </div>
        </div>
      </header>

      <div style={styles.grid}>
        <section style={styles.panel}>
          <h2 style={styles.h2}>Quick actions</h2>
          <div style={styles.quickRow}>
            {QUICK_PROMPTS.map((p) => (
              <button key={p.label} type="button" style={styles.quickBtn} onClick={() => void send(p.text)}>
                {p.label}
              </button>
            ))}
          </div>
          <div style={styles.chat}>
            <div style={styles.chatInner}>
              {messages.length === 0 && (
                <div style={styles.placeholder}>
                  Ask about first service, warranty, booking, campaigns, or nearest authorized service center.
                </div>
              )}
              {messages.map((msg, i) => (
                <div
                  key={i}
                  style={{
                    ...styles.bubble,
                    ...(msg.role === "user" ? styles.bubbleUser : styles.bubbleBot),
                  }}
                >
                  {msg.text}
                </div>
              ))}
              {loading && <div style={{ ...styles.bubble, ...styles.bubbleBot }}>Thinking…</div>}
            </div>
            {error && <div style={styles.err}>{error}</div>}
            <div style={styles.inputRow}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && void send(input)}
                placeholder="Type your question…"
                style={styles.input}
              />
              <button type="button" style={styles.send} disabled={loading} onClick={() => void send(input)}>
                Send
              </button>
            </div>
          </div>
        </section>

        <aside style={styles.aside}>
          <h2 style={styles.h2}>Sources & next step</h2>
          {lastMeta ? (
            <>
              <div style={styles.metaRow}>
                <span style={styles.badge}>Intent</span>
                <code style={styles.code}>{lastMeta.intent}</code>
              </div>
              <div style={styles.metaRow}>
                <span style={styles.badge}>Confidence</span>
                <span>{lastMeta.confidence}</span>
              </div>
              {lastMeta.needs_handoff && (
                <div style={styles.handoff}>Consider human support for this query.</div>
              )}
              {lastMeta.disclaimer && <div style={styles.disclaimer}>{lastMeta.disclaimer}</div>}
              <div style={{ marginTop: 16 }}>
                <div style={styles.muted}>Citations</div>
                <ul style={styles.citeList}>
                  {lastMeta.citations.map((c, idx) => (
                    <li key={idx} style={styles.citeItem}>
                      <div style={styles.citeTitle}>{c.title}</div>
                      <div style={styles.citeType}>{c.doc_type}</div>
                      <div style={styles.excerpt}>{c.excerpt}</div>
                      <a href={c.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 13 }}>
                        Source link
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
              {lastMeta.cta && (
                <div style={styles.cta}>
                  <div style={styles.muted}>Suggested action</div>
                  <button type="button" style={styles.ctaBtn}>
                    {lastMeta.cta.label}
                  </button>
                  <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 6 }}>Type: {lastMeta.cta.type}</div>
                </div>
              )}
            </>
          ) : (
            <p style={{ color: "var(--muted)", lineHeight: 1.6 }}>
              After you ask a question, retrieved sources and structured metadata appear here. This builds trust
              for stakeholder demos.
            </p>
          )}
        </aside>
      </div>

      <footer style={styles.footer}>
        Demo only — not affiliated with Suzuki. Replace seed data with crawled public pages and approved legal
        copy before production.
      </footer>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: { maxWidth: 1120, margin: "0 auto", padding: "32px 20px 48px" },
  header: {
    display: "grid",
    gridTemplateColumns: "1fr minmax(240px, 280px)",
    gap: 24,
    alignItems: "start",
    marginBottom: 28,
  },
  kicker: { fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)" },
  title: {
    fontFamily: '"Instrument Serif", Georgia, serif',
    fontSize: "clamp(2rem, 4vw, 2.75rem)",
    fontWeight: 400,
    margin: "8px 0 12px",
    lineHeight: 1.15,
  },
  titleAccent: { color: "var(--accent-dim)" },
  sub: { color: "var(--muted)", maxWidth: 560, lineHeight: 1.6, margin: 0 },
  headerCard: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: 16,
    padding: 20,
    boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
  },
  muted: { fontSize: 12, color: "var(--muted)" },
  select: {
    width: "100%",
    marginTop: 8,
    padding: "10px 12px",
    borderRadius: 10,
    border: "1px solid var(--border)",
    background: "var(--surface-2)",
    color: "var(--text)",
  },
  linkBtn: {
    display: "inline-block",
    padding: "8px 12px",
    borderRadius: 10,
    border: "1px solid var(--border)",
    fontSize: 14,
  },
  grid: { display: "grid", gridTemplateColumns: "1fr 340px", gap: 20 },
  panel: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: 16,
    padding: 20,
    minHeight: 520,
  },
  aside: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: 16,
    padding: 20,
    alignSelf: "start",
    position: "sticky",
    top: 24,
  },
  h2: { fontSize: 16, margin: "0 0 14px", fontWeight: 600 },
  quickRow: { display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 },
  quickBtn: {
    padding: "8px 12px",
    borderRadius: 999,
    border: "1px solid var(--border)",
    background: "var(--surface-2)",
    color: "var(--text)",
    cursor: "pointer",
    fontSize: 13,
  },
  chat: { display: "flex", flexDirection: "column", gap: 12 },
  chatInner: {
    minHeight: 280,
    maxHeight: 420,
    overflowY: "auto",
    padding: 12,
    borderRadius: 12,
    background: "var(--bg)",
    border: "1px solid var(--border)",
  },
  placeholder: { color: "var(--muted)", fontSize: 14, lineHeight: 1.5 },
  bubble: { padding: "10px 12px", borderRadius: 12, marginBottom: 8, maxWidth: "92%", lineHeight: 1.5 },
  bubbleUser: {
    marginLeft: "auto",
    background: "linear-gradient(135deg, var(--accent), #0f4fd6)",
    color: "#fff",
  },
  bubbleBot: { marginRight: "auto", background: "var(--surface-2)", border: "1px solid var(--border)" },
  inputRow: { display: "flex", gap: 8 },
  input: {
    flex: 1,
    padding: "12px 14px",
    borderRadius: 12,
    border: "1px solid var(--border)",
    background: "var(--surface-2)",
    color: "var(--text)",
    fontSize: 15,
  },
  send: {
    padding: "12px 18px",
    borderRadius: 12,
    border: "none",
    background: "var(--accent)",
    color: "#fff",
    fontWeight: 600,
    cursor: "pointer",
  },
  err: { color: "#ff8a8a", fontSize: 13 },
  metaRow: { display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" },
  badge: {
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    color: "var(--muted)",
  },
  code: {
    fontSize: 13,
    background: "var(--surface-2)",
    padding: "4px 8px",
    borderRadius: 8,
    border: "1px solid var(--border)",
  },
  handoff: {
    marginTop: 8,
    padding: 10,
    borderRadius: 10,
    background: "rgba(255, 193, 77, 0.12)",
    border: "1px solid rgba(255, 193, 77, 0.35)",
    fontSize: 13,
  },
  disclaimer: {
    marginTop: 8,
    fontSize: 12,
    color: "var(--muted)",
    lineHeight: 1.5,
  },
  citeList: { listStyle: "none", padding: 0, margin: "8px 0 0" },
  citeItem: {
    padding: 12,
    borderRadius: 12,
    border: "1px solid var(--border)",
    marginBottom: 10,
    background: "var(--bg)",
  },
  citeTitle: { fontWeight: 600, fontSize: 14 },
  citeType: { fontSize: 12, color: "var(--accent-dim)", marginBottom: 6 },
  excerpt: { fontSize: 12, color: "var(--muted)", lineHeight: 1.45 },
  cta: { marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)" },
  ctaBtn: {
    marginTop: 8,
    width: "100%",
    padding: "10px 12px",
    borderRadius: 12,
    border: "1px solid var(--accent)",
    background: "transparent",
    color: "var(--accent-dim)",
    fontWeight: 600,
    cursor: "pointer",
  },
  footer: { marginTop: 32, fontSize: 12, color: "var(--muted)", lineHeight: 1.5 },
};
