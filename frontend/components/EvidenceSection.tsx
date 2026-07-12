"use client";

/**
 * Workspace section: statements, each expandable to its evidence (ADR-010).
 * The evidence table is the "explore" affordance — nothing is a black box.
 */

import { useState } from "react";
import { EvidenceItem, WorkspaceSection } from "@/lib/api";
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

function StatementRow({
  text,
  evidence,
}: {
  text: string;
  evidence: EvidenceItem[];
}) {
  const [open, setOpen] = useState(false);
  return (
    <li style={{ padding: "10px 0", borderTop: `1px solid ${theme.grid}` }}>
      <div style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: theme.inkSecondary, flex: 1 }}>
          {text}
        </p>
        {evidence.length > 0 && (
          <button
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            style={{
              background: "transparent",
              color: theme.inkMuted,
              border: `1px solid ${theme.border}`,
              borderRadius: 6,
              padding: "2px 8px",
              fontSize: 11,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            {open ? "Hide evidence" : `Evidence (${evidence.length})`}
          </button>
        )}
      </div>
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
            evidence={statement.evidence_ids
              .map((id) => byId.get(id))
              .filter((item): item is EvidenceItem => item !== undefined)}
          />
        ))}
      </ul>
    </section>
  );
}
