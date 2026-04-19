"use client";

import type { TabConfig, TabAction } from "./lead-app-types";

interface LaTabStripProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  tabs: TabConfig[];
  actions: Record<string, TabAction>;
}

export function LaTabStrip({
  activeTab,
  setActiveTab,
  tabs,
  actions,
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
        {currentActions?.secondary && (
          <button className="btn btn-ghost btn-sm">
            {currentActions.secondary}
          </button>
        )}
        {currentActions?.primary && (
          <button className="btn btn-primary btn-sm">
            {currentActions.primary}
          </button>
        )}
      </div>
    </div>
  );
}
