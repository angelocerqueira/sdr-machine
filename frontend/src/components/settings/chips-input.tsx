"use client";

import { useState, type KeyboardEvent } from "react";

interface Props {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}

export function ChipsInput({ values, onChange, placeholder }: Props) {
  const [draft, setDraft] = useState("");

  function add() {
    const v = draft.trim();
    if (!v || values.includes(v)) { setDraft(""); return; }
    onChange([...values, v]);
    setDraft("");
  }

  function remove(idx: number) {
    onChange(values.filter((_, i) => i !== idx));
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add();
    } else if (e.key === "Backspace" && !draft && values.length) {
      remove(values.length - 1);
    }
  }

  return (
    <div className="settings-input" style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: 8, minHeight: 44 }}>
      {values.map((v, i) => (
        <span key={`${v}-${i}`} className="settings-chip">
          {v}
          <button type="button" onClick={() => remove(i)} aria-label={`Remover ${v}`}>×</button>
        </span>
      ))}
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKey}
        onBlur={add}
        placeholder={values.length === 0 ? placeholder : ""}
        style={{ flex: 1, minWidth: 80, border: 0, background: "transparent", outline: "none", fontSize: 14 }}
      />
    </div>
  );
}
