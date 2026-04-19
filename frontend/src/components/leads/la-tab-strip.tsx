"use client";

import type { TabConfig, TabAction } from "./lead-app-types";

interface LaTabStripProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  tabs: TabConfig[];
  actions: Record<string, TabAction>;
  onPrimaryAction?: () => void;
  actionLoading?: boolean;
}

export function LaTabStrip({
  activeTab,
  setActiveTab,
  tabs,
  actions,
  onPrimaryAction,
  actionLoading,
}: LaTabStripProps) {
  const currentActions = actions[activeTab];

  return (
    <div className="la-tabs">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          className={`la-tab ${activeTab === tab.key ? "active" : ""}`}
          onClick={() => setActiveTab(tab.key)}
        >
          {tab.label}
          {tab.count != null && (
            <span className="la-tab-count">
              {tab.count}
              {tab.suffix ?? ""}
            </span>
          )}
        </button>
      ))}
      <div className="la-tabs-spacer" />
      <div className="la-tabs-action">
        {currentActions?.primary && (
          <button
            className="btn btn-primary btn-sm"
            onClick={onPrimaryAction}
            disabled={actionLoading}
          >
            {actionLoading ? (
              <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : null}
            {currentActions.primary}
          </button>
        )}
      </div>
    </div>
  );
}
