"use client";

/**
 * Workspace section: statements, each expandable to its evidence (ADR-010).
 * The evidence table is the "explore" affordance — nothing is a black box.
 */

import { useState } from "react";
import { CatalystAssessment, EvidenceItem, WorkspaceSection } from "@/lib/api";
import { theme } from "@/lib/theme";

function EvidenceTable({ items }: { items: EvidenceItem[] }) {
  return (
    <table
      style={{
        width: "100%",
        fontSize: 12,
        borderCollapse: "collapse",
        marginTop: 8,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      <thead>
        <tr style={{ color: theme.inkMuted, textAlign: "left" }}>
          <th style={{ padding: "3px 8px", fontWeight: 500 }}>Evidence</th>
          <th style={{ padding: "3px 8px", textAlign: "right", fontWeight: 500 }}>Value</th>
          <th style={{ padding: "3px 8px", fontWeight: 500 }}>As of</th>
          <th style={{ padding: "3px 8px", fontWeight: 500 }}>Source</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id} style={{ borderTop: `1px solid ${theme.grid}` }}>
            <td style={{ padding: "4px 8px", color: theme.inkSecondary }}>
              {item.url ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: theme.inkSecondary }}
                >
                  {item.label} ↗
                </a>
              ) : (
                item.label
              )}
            </td>
            <td
              style={{
                padding: "4px 8px",
                textAlign: "right",
                color: theme.inkPrimary,
                fontWeight: 600,
              }}
            >
              {item.display}
            </td>
            <td style={{ padding: "4px 8px", color: theme.inkMuted }}>{item.as_of}</td>
            <td style={{ padding: "4px 8px", color: theme.inkMuted }}>
              {item.source}
              {item.trust_level != null && (
                <span
                  title="Source trust level (provenance, not truth)"
                  style={{
                    marginLeft: 6,
                    padding: "1px 6px",
                    borderRadius: 999,
                    border: `1px solid ${theme.border}`,
                    fontSize: 10,
                    color: item.trust_level >= 9 ? theme.deltaGood : theme.inkSecondary,
                  }}
                >
                  {item.trust_level}/10
                </span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PlaybookField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 6 }}>
      <span
        style={{
          fontSize: 10,
          textTransform: "uppercase",
          letterSpacing: 0.6,
          color: theme.inkMuted,
        }}
      >
        {label}
      </span>
      <div style={{ fontSize: 12.5, lineHeight: 1.5, color: theme.inkSecondary }}>{children}</div>
    </div>
  );
}

function PlaybookCard({ assessment }: { assessment: CatalystAssessment }) {
  return (
    <div
      style={{
        marginTop: 8,
        padding: "10px 12px",
        borderLeft: `2px solid ${theme.border}`,
        background: "rgba(127, 127, 127, 0.06)",
        borderRadius: "0 8px 8px 0",
      }}
    >
      <div style={{ fontSize: 11, color: theme.inkMuted }}>
        AlphaLab playbook v{assessment.playbook_version} — editorial assessment, not evidence
        {assessment.typical_time_et ? ` · typically ${assessment.typical_time_et}` : ""}
        {` · typical reaction window: ${assessment.horizon.toLowerCase()}`}
      </div>
      <PlaybookField label="Why it matters">{assessment.why_it_matters}</PlaybookField>
      {assessment.transmission.length > 0 && (
        <PlaybookField label="Transmission chain">
          {assessment.transmission.join(" → ")}
        </PlaybookField>
      )}
      {assessment.watch.length > 0 && (
        <PlaybookField label="Watch">{assessment.watch.join(" · ")}</PlaybookField>
      )}
      <PlaybookField label="Supportive scenario">{assessment.supportive_scenario}</PlaybookField>
      <PlaybookField label="Adverse scenario">{assessment.adverse_scenario}</PlaybookField>
    </div>
  );
}

function StatementRow({
  text,
  evidence,
  assessment,
}: {
  text: string;
  evidence: EvidenceItem[];
  assessment?: CatalystAssessment | null;
}) {
  const [open, setOpen] = useState(false);
  const [playbookOpen, setPlaybookOpen] = useState(false);
  const toggleStyle: React.CSSProperties = {
    background: "transparent",
    color: theme.inkMuted,
    border: `1px solid ${theme.border}`,
    borderRadius: 6,
    padding: "2px 8px",
    fontSize: 11,
    cursor: "pointer",
    whiteSpace: "nowrap",
  };
  return (
    <li style={{ padding: "10px 0", borderTop: `1px solid ${theme.grid}` }}>
      <div style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: theme.inkSecondary, flex: 1 }}>
          {text}
        </p>
        {assessment && (
          <button
            onClick={() => setPlaybookOpen((v) => !v)}
            aria-expanded={playbookOpen}
            title="Editorial context from the versioned AlphaLab playbook — judgment, not evidence"
            style={toggleStyle}
          >
            {playbookOpen ? "Hide playbook" : "Playbook"}
          </button>
        )}
        {evidence.length > 0 && (
          <button
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            style={toggleStyle}
          >
            {open ? "Hide evidence" : `Evidence (${evidence.length})`}
          </button>
        )}
      </div>
      {playbookOpen && assessment && <PlaybookCard assessment={assessment} />}
      {open && <EvidenceTable items={evidence} />}
    </li>
  );
}

export default function EvidenceSectionCard({ section }: { section: WorkspaceSection }) {
  const byId = new Map(section.evidence.map((e) => [e.id, e]));
  return (
    <section
      style={{
        background: theme.surface,
        border: `1px solid ${theme.border}`,
        borderRadius: 12,
        padding: 16,
      }}
    >
      <h2 style={{ fontSize: 14, margin: 0, color: theme.inkPrimary }}>{section.title}</h2>
      <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0 }}>
        {section.statements.map((statement, index) => (
          <StatementRow
            key={index}
            text={statement.text}
            assessment={statement.assessment}
            evidence={statement.evidence_ids
              .map((id) => byId.get(id))
              .filter((item): item is EvidenceItem => item !== undefined)}
          />
        ))}
      </ul>
    </section>
  );
}
