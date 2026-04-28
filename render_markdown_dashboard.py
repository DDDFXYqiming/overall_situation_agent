from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from urllib.parse import quote

CHART_COLORS = [
    "#0052FF",
    "#4D7CFF",
    "#7CA6FF",
    "#38BDF8",
    "#22C55E",
    "#94A3B8",
    "#0F172A",
]

CSS = """
:root {
  --bg: #f4f1ec;
  --bg-soft: #fbf8f3;
  --panel: #fffdfa;
  --panel-soft: #f8f4ee;
  --panel-strong: #fff4e6;
  --stroke: #ece2d4;
  --stroke-strong: #e1cfb7;
  --ink: #1f1a16;
  --muted: #7e7264;
  --muted-strong: #5e554a;
  --accent: #ff971c;
  --accent-strong: #f27c1f;
  --accent-soft: rgba(255, 151, 28, 0.14);
  --blue: #5b8cff;
  --blue-soft: rgba(91, 140, 255, 0.12);
  --teal: #4ec5b0;
  --danger: #e16a3d;
  --shadow: 0 18px 44px rgba(84, 63, 31, 0.08);
  --shadow-soft: 0 10px 22px rgba(84, 63, 31, 0.05);
  --radius-xl: 28px;
  --radius-lg: 20px;
  --radius-md: 14px;
  --radius-sm: 10px;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--ink);
  background:
    radial-gradient(circle at top right, rgba(255, 151, 28, 0.14), transparent 28%),
    radial-gradient(circle at top left, rgba(91, 140, 255, 0.1), transparent 24%),
    linear-gradient(180deg, #f7f3ed 0%, #f2eee8 100%);
  font-family: "Source Han Sans SC", "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
  line-height: 1.7;
}

img { max-width: 100%; display: block; }
a { color: inherit; text-decoration: none; }
code {
  padding: 0.12rem 0.42rem;
  border-radius: 999px;
  background: rgba(31, 26, 22, 0.06);
  font-size: 0.92em;
}

.progress-bar {
  position: fixed;
  inset: 0 auto auto 0;
  width: 100%;
  height: 4px;
  z-index: 80;
  background: transparent;
}

.progress-bar span {
  display: block;
  width: 0;
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #ffc468);
  box-shadow: 0 0 18px rgba(255, 151, 28, 0.4);
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 70;
  backdrop-filter: blur(18px);
  background: rgba(255, 252, 247, 0.9);
  border-bottom: 1px solid rgba(225, 207, 183, 0.72);
}

.topbar-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 18px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.brand-mark {
  position: relative;
  width: 44px;
  height: 24px;
}

.brand-mark::before,
.brand-mark::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: 999px;
  border: 3px solid var(--accent);
  transform-origin: center;
}

.brand-mark::before {
  transform: rotate(20deg) scaleX(0.92);
  clip-path: inset(0 42% 0 0);
}

.brand-mark::after {
  border-color: #ffc468;
  transform: rotate(-20deg) scaleX(0.92);
  clip-path: inset(0 0 0 42%);
}

.brand-copy strong {
  display: block;
  font-size: 18px;
  letter-spacing: 0.04em;
}

.brand-copy span {
  display: block;
  margin-top: 2px;
  color: var(--muted);
  font-size: 12px;
}

.tabs {
  display: flex;
  align-items: center;
  gap: 22px;
  color: var(--muted-strong);
  font-size: 14px;
  white-space: nowrap;
}

.tabs a {
  position: relative;
  padding: 12px 0;
}

.tabs a.active {
  color: var(--ink);
  font-weight: 700;
}

.tabs a.active::after {
  content: "";
  position: absolute;
  inset: auto 0 -18px;
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--accent), #ffc468);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  color: var(--muted);
  font-size: 13px;
}

.topbar-badge,
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 34px;
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: var(--panel);
  border: 1px solid var(--stroke);
  box-shadow: var(--shadow-soft);
}

.avatar {
  width: 34px;
  padding: 0;
  font-weight: 700;
  color: var(--accent-strong);
}

.app-shell {
  max-width: 1440px;
  margin: 0 auto;
  padding: 28px 24px 44px;
  display: grid;
  grid-template-columns: 312px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

.sidebar {
  position: sticky;
  top: 96px;
  display: grid;
  gap: 18px;
}

.sidebar-panel,
.hero-panel,
.workspace-panel,
.report-section {
  background: rgba(255, 253, 250, 0.94);
  border: 1px solid var(--stroke);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow);
}

.sidebar-panel {
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,244,238,0.98)),
    var(--panel);
}

.panel-title,
.section-label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 15px;
  margin-bottom: 14px;
}

.panel-title::before,
.section-label::before {
  content: "";
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: linear-gradient(135deg, var(--accent), #ffc468);
  box-shadow: 0 0 0 6px rgba(255, 151, 28, 0.08);
}

.sidebar-kpi {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.mini-card {
  padding: 12px;
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, #fff8ef, #fffdfa);
  border: 1px solid rgba(255, 151, 28, 0.2);
}

.mini-card strong {
  display: block;
  font-size: 22px;
  line-height: 1.15;
}

.mini-card span {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 12px;
}

.tag-stack,
.risk-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-chip,
.risk-chip,
.event-chip,
.hero-chip,
.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 12px;
}

.tag-chip,
.meta-chip {
  background: rgba(255, 151, 28, 0.09);
  border: 1px solid rgba(255, 151, 28, 0.18);
  color: var(--muted-strong);
}

.risk-chip {
  background: rgba(225, 106, 61, 0.08);
  border: 1px solid rgba(225, 106, 61, 0.16);
  color: #9d4624;
}

.toc {
  display: grid;
  gap: 6px;
}

.toc-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  color: var(--muted-strong);
  font-size: 13px;
  transition: background .22s ease, color .22s ease, transform .22s ease;
}

.toc-link.level-2 { padding-left: 18px; }
.toc-link.level-3,
.toc-link.level-4 { padding-left: 24px; font-size: 12px; }

.toc-link:hover,
.toc-link.is-active {
  color: var(--ink);
  background: rgba(255, 151, 28, 0.11);
  transform: translateX(2px);
}

.main {
  display: grid;
  gap: 24px;
}

.hero-panel {
  position: relative;
  overflow: hidden;
  padding: 30px;
  background:
    linear-gradient(135deg, rgba(255, 151, 28, 0.1), rgba(91, 140, 255, 0.06)),
    linear-gradient(180deg, rgba(255,255,255,0.96), rgba(249,245,239,0.94));
}

.hero-panel::after {
  content: "";
  position: absolute;
  right: -84px;
  top: -84px;
  width: 240px;
  height: 240px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 151, 28, 0.2), transparent 68%);
}

.hero-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 24px;
}

.hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 151, 28, 0.11);
  border: 1px solid rgba(255, 151, 28, 0.18);
  font-size: 12px;
  color: var(--muted-strong);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title {
  margin: 18px 0 10px;
  font-size: clamp(30px, 4vw, 44px);
  line-height: 1.16;
  letter-spacing: 0.01em;
}

.hero-title strong {
  color: var(--accent-strong);
}

.hero-copy p {
  margin: 0;
  max-width: 760px;
  color: var(--muted-strong);
  font-size: 15px;
}

.hero-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

.hero-chip {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(225, 207, 183, 0.82);
  color: var(--muted-strong);
  box-shadow: var(--shadow-soft);
}

.hero-side {
  display: grid;
  gap: 14px;
  align-content: start;
}

.hero-note {
  padding: 16px 18px;
  border-radius: var(--radius-lg);
  background: rgba(255,255,255,0.86);
  border: 1px solid rgba(225, 207, 183, 0.82);
  box-shadow: var(--shadow-soft);
}

.hero-note small {
  display: block;
  color: var(--muted);
  margin-bottom: 8px;
}

.hero-note strong {
  display: block;
  font-size: 18px;
}

.workspace-panel {
  padding: 22px 24px 26px;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.workspace-header h2 {
  margin: 0;
  font-size: 22px;
}

.workspace-header p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  position: relative;
  overflow: hidden;
  padding: 18px;
  border-radius: var(--radius-lg);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.96), rgba(249,245,239,0.96)),
    var(--panel);
  border: 1px solid var(--stroke);
  box-shadow: var(--shadow-soft);
}

.summary-card::after {
  content: "";
  position: absolute;
  inset: auto -20px -26px auto;
  width: 108px;
  height: 108px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(91, 140, 255, 0.14), transparent 68%);
}

.summary-card strong {
  position: relative;
  z-index: 1;
  display: block;
  font-size: 24px;
}

.summary-card span,
.summary-card small {
  position: relative;
  z-index: 1;
  display: block;
}

.summary-card span {
  color: var(--muted-strong);
  font-weight: 700;
}

.summary-card small {
  margin-top: 8px;
  color: var(--muted);
  font-size: 12px;
}

.report-section {
  padding: 24px;
}

.report-section.level-1 {
  padding: 28px;
}

.section-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.section-heading {
  margin: 0;
  line-height: 1.25;
}

.section-heading.level-1 { font-size: 30px; }
.section-heading.level-2 { font-size: 24px; }
.section-heading.level-3 { font-size: 20px; }
.section-heading.level-4 { font-size: 17px; }

.section-meta {
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
}

.section-body {
  display: grid;
  gap: 16px;
}

.report-section.level-1 + .report-section.level-1 {
  margin-top: 8px;
}

.report-section.level-2,
.report-section.level-3,
.report-section.level-4 {
  background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(249,245,239,0.94));
}

.text-paragraph {
  margin: 0;
  color: var(--muted-strong);
}

.text-list,
.text-olist {
  margin: 0;
  padding-left: 1.2rem;
  color: var(--muted-strong);
}

.text-list li,
.text-olist li {
  margin: 0.42rem 0;
}

.divider {
  height: 1px;
  margin: 6px 0;
  border: 0;
  background: linear-gradient(90deg, transparent, rgba(225, 207, 183, 0.9), transparent);
}

.quote-thread {
  display: grid;
  gap: 12px;
}

.quote-bubble {
  position: relative;
  max-width: 92%;
  margin: 0;
  padding: 15px 18px;
  border-radius: 18px;
  border: 1px solid rgba(225, 207, 183, 0.88);
  background: rgba(255, 255, 255, 0.9);
  color: var(--muted-strong);
  box-shadow: var(--shadow-soft);
}

.quote-bubble.right {
  justify-self: end;
  background: rgba(255, 245, 231, 0.95);
}

.quote-bubble::before {
  content: "";
  position: absolute;
  left: -9px;
  top: 14px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(91, 140, 255, 0.16), rgba(91, 140, 255, 0.04));
  border: 1px solid rgba(91, 140, 255, 0.18);
}

.quote-bubble.right::before {
  left: auto;
  right: -9px;
  background: linear-gradient(135deg, rgba(255, 151, 28, 0.18), rgba(255, 151, 28, 0.06));
  border-color: rgba(255, 151, 28, 0.2);
}

.chart-frame {
  padding: 18px;
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(249,245,239,0.96));
  border: 1px solid rgba(225, 207, 183, 0.86);
  box-shadow: var(--shadow-soft);
}

.chart-frame img {
  border-radius: 18px;
  border: 1px solid rgba(225, 207, 183, 0.88);
  background: white;
}

.chart-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.chart-topline strong {
  font-size: 15px;
}

.chart-caption {
  margin-top: 12px;
  color: var(--muted);
  font-size: 12px;
}

.event-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.event-chip {
  background: rgba(91, 140, 255, 0.09);
  border: 1px solid rgba(91, 140, 255, 0.16);
  color: #4568c6;
}

.table-wrap {
  overflow: auto;
  border-radius: 18px;
  border: 1px solid rgba(225, 207, 183, 0.86);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.75);
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 720px;
}

thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: rgba(255, 244, 230, 0.98);
  color: var(--ink);
}

th, td {
  padding: 12px 14px;
  border-bottom: 1px solid rgba(236, 226, 212, 0.9);
  text-align: left;
  vertical-align: top;
  font-size: 13px;
}

tbody tr:nth-child(even) {
  background: rgba(249, 245, 239, 0.65);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.overview-card {
  padding: 18px;
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, #fff8ef, #fffdfa);
  border: 1px solid rgba(255, 151, 28, 0.18);
  box-shadow: var(--shadow-soft);
}

.overview-card strong {
  display: block;
  margin-top: 10px;
  font-size: 22px;
}

.overview-card p,
.service-matrix p {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.service-matrix {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.service-box {
  padding: 18px;
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,244,238,0.96));
  border: 1px solid rgba(225, 207, 183, 0.86);
  box-shadow: var(--shadow-soft);
}

.service-box h4 {
  margin: 0 0 12px;
  font-size: 15px;
}

.service-box strong {
  display: block;
  font-size: 24px;
}

.service-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.service-tags span {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: rgba(255, 151, 28, 0.1);
  border: 1px solid rgba(255, 151, 28, 0.16);
}

.footer-note {
  padding: 20px 22px;
  border-radius: var(--radius-xl);
  background: linear-gradient(180deg, rgba(31, 26, 22, 0.96), rgba(53, 44, 35, 0.96));
  color: rgba(255,255,255,0.88);
  box-shadow: var(--shadow);
}

.footer-note p {
  margin: 0;
}

.js [data-reveal] {
  opacity: 0;
  transform: translateY(26px);
  transition: opacity .62s ease, transform .62s ease;
}

.js [data-reveal].is-visible {
  opacity: 1;
  transform: translateY(0);
}

@media (max-width: 1180px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: static;
    order: 2;
  }

  .main {
    order: 1;
  }

  .hero-grid,
  .summary-cards,
  .overview-grid,
  .service-matrix {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 920px) {
  .topbar-inner {
    padding: 16px 18px;
    flex-wrap: wrap;
  }

  .tabs {
    order: 3;
    width: 100%;
    overflow: auto;
    padding-bottom: 2px;
  }

  .app-shell {
    padding: 20px 14px 30px;
  }

  .hero-panel,
  .workspace-panel,
  .report-section {
    padding: 20px;
    border-radius: 22px;
  }

.section-heading.level-1 { font-size: 24px; }
  .section-heading.level-2 { font-size: 20px; }
  .section-heading.level-3 { font-size: 18px; }
  .section-heading.level-4 { font-size: 16px; }
}

/* Minimalist Modern: webpage_design_prompt.md reference, no sidebar */
:root {
  --bg: #fafafa;
  --bg-soft: #f1f5f9;
  --panel: #ffffff;
  --panel-soft: #f8fbff;
  --panel-strong: #0f172a;
  --stroke: #e2e8f0;
  --stroke-strong: #cbd5e1;
  --ink: #0f172a;
  --muted: #64748b;
  --muted-strong: #334155;
  --accent: #0052ff;
  --accent-strong: #1d4fff;
  --accent-secondary: #4d7cff;
  --accent-soft: rgba(0, 82, 255, 0.08);
  --blue: #4d7cff;
  --blue-soft: rgba(77, 124, 255, 0.12);
  --teal: #38bdf8;
  --danger: #f97316;
  --shadow: 0 24px 64px rgba(15, 23, 42, 0.08);
  --shadow-soft: 0 12px 30px rgba(15, 23, 42, 0.06);
  --radius-xl: 32px;
  --radius-lg: 24px;
  --radius-md: 16px;
  --radius-sm: 12px;
  --font-display: "Iowan Old Style", "Palatino Linotype", "Noto Serif SC", "Songti SC", serif;
  --font-body: "Inter", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-mono: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
}

body {
  color: var(--ink);
  background:
    radial-gradient(circle at top right, rgba(77, 124, 255, 0.18), transparent 28%),
    radial-gradient(circle at 12% 12%, rgba(0, 82, 255, 0.1), transparent 22%),
    linear-gradient(180deg, #fafafa 0%, #f8fafc 100%);
  font-family: var(--font-body);
}

code {
  background: rgba(15, 23, 42, 0.05);
  border-radius: 10px;
}

.progress-bar span {
  background: linear-gradient(90deg, var(--accent), var(--accent-secondary));
  box-shadow: 0 0 24px rgba(0, 82, 255, 0.32);
}

.topbar {
  background: rgba(250, 250, 250, 0.82);
  border-bottom: 1px solid rgba(226, 232, 240, 0.95);
}

.topbar-inner {
  max-width: 1280px;
}

.brand-mark::before {
  border-color: var(--accent);
}

.brand-mark::after {
  border-color: var(--accent-secondary);
}

.brand-copy strong {
  font-family: var(--font-display);
  font-size: 24px;
  letter-spacing: -0.02em;
}

.brand-copy span {
  margin-top: 0;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.tabs {
  gap: 18px;
  color: var(--muted);
  font-size: 13px;
}

.tabs a.active::after {
  background: linear-gradient(90deg, var(--accent), var(--accent-secondary));
}

.topbar-badge,
.avatar {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(226, 232, 240, 0.9);
  box-shadow: none;
}

.app-shell {
  display: block;
  max-width: none;
  margin: 0;
  padding: 0;
}

.sidebar {
  display: none !important;
}

.main {
  display: block;
}

.hero-panel {
  position: relative;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  overflow: hidden;
  background:
    radial-gradient(circle at 85% 18%, rgba(77, 124, 255, 0.28), transparent 18%),
    radial-gradient(circle at 72% 34%, rgba(56, 189, 248, 0.16), transparent 18%),
    linear-gradient(145deg, #0f172a 0%, #111c34 40%, #0f172a 100%);
}

.hero-panel::before,
.hero-panel::after {
  content: "";
  position: absolute;
  inset: auto;
  pointer-events: none;
}

.hero-panel::before {
  width: 420px;
  height: 420px;
  left: -120px;
  top: 84px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 82, 255, 0.18), transparent 66%);
  filter: blur(6px);
}

.hero-panel::after {
  inset: auto 0 0 0;
  height: 1px;
  background: linear-gradient(90deg, rgba(255,255,255,0.08), rgba(255,255,255,0.34), rgba(255,255,255,0.08));
}

.hero-shell {
  position: relative;
  z-index: 1;
  max-width: 1280px;
  min-height: calc(100svh - 72px);
  margin: 0 auto;
  padding: 74px 32px 52px;
  display: grid;
  grid-template-columns: 1.08fr 0.92fr;
  gap: 48px;
  align-items: center;
}

.hero-copy {
  max-width: 680px;
}

.hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: rgba(255, 255, 255, 0.76);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero-title {
  margin: 22px 0 16px;
  color: #fff;
  font-family: var(--font-display);
  font-size: clamp(46px, 7vw, 86px);
  line-height: 1.02;
  letter-spacing: -0.03em;
}

.hero-title strong {
  background: linear-gradient(90deg, #0052ff, #4d7cff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-copy p,
.hero-deck {
  margin: 0;
  max-width: 60ch;
  color: rgba(255, 255, 255, 0.76);
  font-size: 16px;
}

.hero-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 24px;
}

.hero-chip,
.meta-chip,
.tag-chip,
.event-chip {
  background: rgba(77, 124, 255, 0.12);
  border: 1px solid rgba(77, 124, 255, 0.2);
  color: #355ebf;
}

.hero-panel .hero-chip {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.14);
  color: rgba(255, 255, 255, 0.82);
}

.hero-visual {
  position: relative;
  min-height: 520px;
}

.hero-orb {
  position: absolute;
  inset: 50% auto auto 50%;
  width: 320px;
  height: 320px;
  margin: -160px 0 0 -160px;
  border-radius: 50%;
  background:
    radial-gradient(circle at 35% 35%, rgba(255, 255, 255, 0.86), rgba(255,255,255,0.16) 26%, transparent 27%),
    radial-gradient(circle, rgba(77, 124, 255, 0.42), rgba(0, 82, 255, 0.16) 40%, transparent 72%);
  filter: blur(2px);
}

.hero-ring {
  position: absolute;
  inset: 50% auto auto 50%;
  border-radius: 50%;
  border: 1px dashed rgba(148, 163, 184, 0.32);
  transform: translate(-50%, -50%);
  animation: spinSlow 60s linear infinite;
}

.hero-ring.ring-a {
  width: 430px;
  height: 430px;
}

.hero-ring.ring-b {
  width: 306px;
  height: 306px;
  animation-direction: reverse;
  animation-duration: 42s;
}

.hero-ring.ring-c {
  width: 224px;
  height: 224px;
  border-style: solid;
  border-color: rgba(77, 124, 255, 0.16);
}

.hero-grid-dots {
  position: absolute;
  right: 36px;
  bottom: 42px;
  display: grid;
  grid-template-columns: repeat(3, 10px);
  gap: 10px;
}

.hero-grid-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.34);
}

.floating-panel {
  position: absolute;
  padding: 18px 20px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(18px);
  color: rgba(255, 255, 255, 0.92);
}

.floating-panel span {
  display: block;
  color: rgba(255, 255, 255, 0.58);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.floating-panel strong {
  display: block;
  margin-top: 10px;
  font-size: 24px;
  line-height: 1.08;
  letter-spacing: -0.03em;
}

.floating-panel small {
  display: block;
  margin-top: 10px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
}

.floating-panel.panel-main {
  left: 8%;
  top: 15%;
  width: 320px;
  animation: floatPrimary 5.8s ease-in-out infinite;
}

.floating-panel.panel-side {
  right: 2%;
  top: 24%;
  width: 220px;
  animation: floatSecondary 4.6s ease-in-out infinite;
}

.floating-panel.panel-bottom {
  left: 18%;
  bottom: 12%;
  width: 260px;
  animation: floatPrimary 6.2s ease-in-out infinite reverse;
}

.anchor-band {
  position: relative;
  z-index: 4;
  max-width: 1280px;
  margin: -34px auto 0;
  padding: 0 32px;
}

.toc {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.toc-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.92);
  color: var(--muted-strong);
  font-size: 13px;
  transition: transform .22s ease, border-color .22s ease, background .22s ease, color .22s ease;
}

.toc-link small {
  display: none;
}

.toc-link:hover,
.toc-link.is-active {
  transform: translateY(-1px);
  border-color: rgba(77, 124, 255, 0.18);
  background: rgba(0, 82, 255, 0.08);
  color: var(--ink);
}

.workspace-panel {
  max-width: 1280px;
  margin: 28px auto 0;
  padding: 0 32px;
  background: transparent;
  border: 0;
  box-shadow: none;
}

.spotlight-card {
  padding: 32px;
  border-radius: 32px;
  background:
    radial-gradient(circle at top right, rgba(77, 124, 255, 0.1), transparent 22%),
    linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,251,255,0.98));
  border: 1px solid rgba(226, 232, 240, 0.94);
  box-shadow: var(--shadow);
}

.workspace-header {
  align-items: end;
  margin-bottom: 22px;
}

.workspace-header h2 {
  margin: 8px 0 0;
  font-family: var(--font-display);
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.08;
  letter-spacing: -0.03em;
}

.workspace-header p {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 14px;
}

.section-label,
.panel-title {
  align-items: center;
  gap: 12px;
  margin-bottom: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--accent);
}

.panel-title::before,
.section-label::before {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
  box-shadow: 0 0 0 7px rgba(0, 82, 255, 0.08);
  animation: pulseDot 2.2s ease-in-out infinite;
}

.summary-cards {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.summary-card {
  padding: 24px;
  border-radius: 26px;
  background: linear-gradient(180deg, #ffffff, #f8fbff);
  border: 1px solid rgba(226, 232, 240, 0.94);
  box-shadow: none;
}

.summary-card::after {
  background: radial-gradient(circle, rgba(77, 124, 255, 0.14), transparent 70%);
}

.summary-card span {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.summary-card strong {
  margin-top: 12px;
  font-family: var(--font-display);
  font-size: clamp(30px, 3vw, 42px);
  line-height: 1.04;
  letter-spacing: -0.03em;
}

.summary-card small {
  margin-top: 12px;
  color: var(--muted);
  font-size: 13px;
}

.report-stream {
  max-width: 1120px;
  margin: 0 auto;
  padding: 24px 32px 96px;
}

.report-section {
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.report-section.level-1 {
  padding-top: 88px;
}

.report-section.level-2 {
  padding-top: 46px;
}

.report-section.level-3,
.report-section.level-4 {
  padding-top: 28px;
}

.section-head {
  align-items: end;
  margin-bottom: 18px;
}

.section-meta {
  display: none;
}

.section-heading.level-1 {
  font-family: var(--font-display);
  font-size: clamp(40px, 5vw, 64px);
  line-height: 1.03;
  letter-spacing: -0.03em;
}

.section-heading.level-2 {
  font-family: var(--font-display);
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.section-heading.level-3 {
  font-size: 22px;
  line-height: 1.28;
  letter-spacing: -0.02em;
}

.section-heading.level-4 {
  font-size: 18px;
  line-height: 1.32;
}

.section-body {
  gap: 18px;
}

.text-paragraph,
.text-list,
.text-olist {
  max-width: 72ch;
  color: var(--muted-strong);
  font-size: 15px;
}

.text-list li,
.text-olist li {
  margin: 0.56rem 0;
}

.divider {
  margin: 18px 0;
  background: linear-gradient(90deg, transparent, rgba(148, 163, 184, 0.42), transparent);
}

.quote-thread {
  gap: 14px;
}

.quote-bubble {
  max-width: 86%;
  padding: 18px 20px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.94);
  color: var(--muted-strong);
  box-shadow: var(--shadow-soft);
}

.quote-bubble.right {
  background: rgba(241, 245, 249, 0.92);
}

.quote-bubble::before {
  background: linear-gradient(135deg, rgba(0, 82, 255, 0.16), rgba(77, 124, 255, 0.06));
  border-color: rgba(0, 82, 255, 0.16);
}

.chart-frame {
  padding: 22px;
  border-radius: 28px;
  background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,251,255,0.98));
  border: 1px solid rgba(226, 232, 240, 0.94);
  box-shadow: var(--shadow-soft);
}

.chart-topline strong {
  font-size: 16px;
  letter-spacing: -0.02em;
}

.chart-caption {
  margin-top: 14px;
  color: var(--muted);
}

.event-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.table-wrap {
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.94);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: var(--shadow-soft);
}

thead th {
  background: rgba(241, 245, 249, 0.96);
  color: var(--ink);
}

th,
td {
  border-bottom-color: rgba(226, 232, 240, 0.86);
}

tbody tr:nth-child(even) {
  background: rgba(248, 250, 252, 0.82);
}

.overview-grid,
.service-matrix {
  gap: 18px;
}

.overview-card,
.service-box {
  padding: 22px;
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff, #f8fbff);
  border: 1px solid rgba(226, 232, 240, 0.94);
  box-shadow: var(--shadow-soft);
}

.overview-card strong,
.service-box strong {
  font-family: var(--font-display);
  font-size: 34px;
  line-height: 1.04;
  letter-spacing: -0.03em;
}

.service-tags span {
  background: rgba(0, 82, 255, 0.08);
  border-color: rgba(0, 82, 255, 0.14);
  color: #355ebf;
}

.footer-note {
  max-width: 1280px;
  margin: 0 auto 48px;
  padding: 32px;
  border-radius: 32px;
  background:
    radial-gradient(circle at top right, rgba(77, 124, 255, 0.28), transparent 24%),
    linear-gradient(180deg, #0f172a, #16213d);
}

.footer-note p {
  max-width: 66ch;
  color: rgba(255, 255, 255, 0.84);
}

@keyframes spinSlow {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

@keyframes pulseDot {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.35); opacity: 0.66; }
}

@keyframes floatPrimary {
  0%, 100% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(0, -12px, 0); }
}

@keyframes floatSecondary {
  0%, 100% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(0, 10px, 0); }
}

@media (max-width: 1180px) {
  .hero-shell,
  .summary-cards,
  .overview-grid,
  .service-matrix {
    grid-template-columns: 1fr;
  }

  .hero-visual {
    min-height: 440px;
  }
}

@media (max-width: 920px) {
  .hero-shell {
    min-height: auto;
    padding: 60px 18px 44px;
    gap: 28px;
  }

  .anchor-band,
  .workspace-panel,
  .report-stream {
    padding-left: 14px;
    padding-right: 14px;
  }

  .spotlight-card,
  .footer-note {
    padding: 24px 20px;
    border-radius: 24px;
  }

  .hero-visual {
    min-height: 360px;
  }

  .floating-panel.panel-main,
  .floating-panel.panel-side,
  .floating-panel.panel-bottom {
    width: min(72vw, 280px);
  }

  .floating-panel.panel-main { left: 0; top: 8%; }
  .floating-panel.panel-side { right: 0; top: 42%; }
  .floating-panel.panel-bottom { left: 12%; bottom: 6%; }
}

@media (prefers-reduced-motion: reduce) {
  .hero-ring,
  .floating-panel,
  .panel-title::before,
  .section-label::before {
    animation: none !important;
  }
}
"""

JS = """
document.documentElement.classList.add("js");

const progressInner = document.querySelector(".progress-bar span");
const updateProgress = () => {
  const max = document.documentElement.scrollHeight - window.innerHeight;
  const ratio = max > 0 ? (window.scrollY / max) * 100 : 0;
  progressInner.style.width = `${ratio}%`;
};
updateProgress();
window.addEventListener("scroll", updateProgress, { passive: true });
window.addEventListener("resize", updateProgress);

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add("is-visible");
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

document.querySelectorAll("[data-reveal]").forEach((node) => revealObserver.observe(node));

const sectionNodes = [...document.querySelectorAll("[data-anchor-target]")];
const tocMap = new Map(
  [...document.querySelectorAll(".toc-link")].map((link) => [link.getAttribute("href"), link])
);

const sectionObserver = new IntersectionObserver((entries) => {
  let active = null;
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      active = entry.target;
    }
  });
  if (!active) {
    return;
  }
  const activeId = `#${active.id}`;
  tocMap.forEach((link) => link.classList.remove("is-active"));
  const current = tocMap.get(activeId);
  if (current) {
    current.classList.add("is-active");
  }
}, { rootMargin: "-30% 0px -55% 0px", threshold: [0.2, 0.5, 0.9] });

sectionNodes.forEach((node) => sectionObserver.observe(node));
"""


@dataclass
class Block:
    type: str
    text: str = ""
    level: int = 0
    items: list[str] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    ordered: bool = False


@dataclass
class Section:
    title: str
    level: int
    anchor: str
    blocks: list[Block] = field(default_factory=list)
    children: list["Section"] = field(default_factory=list)


def normalize_inline(text: str) -> str:
    text = text.replace("\\*", "*").replace("\u3000", " ")
    text = re.sub(r"\*{3,}", "**", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_markdown(text: str) -> str:
    text = normalize_inline(text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = text.replace("**", "").replace("*", "")
    return " ".join(text.split()).strip()


def render_inline(text: str) -> str:
    text = normalize_inline(text)
    tokens: list[str] = []

    def stash(fragment: str) -> str:
        index = len(tokens)
        tokens.append(fragment)
        return f"@@TOKEN{index}@@"

    text = escape(text)
    text = re.sub(r"`([^`]+)`", lambda m: stash(f"<code>{m.group(1)}</code>"), text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = text.replace("*", "")
    for index, fragment in enumerate(tokens):
        text = text.replace(f"@@TOKEN{index}@@", fragment)
    return text


def is_list_line(text: str) -> bool:
    return bool(re.match(r"^(?:-+\s+|\*\s+|\d+\.\s+)", text))


def strip_list_marker(text: str) -> tuple[bool, str]:
    if re.match(r"^\d+\.\s+", text):
        return True, re.sub(r"^\d+\.\s+", "", text, count=1)
    return False, re.sub(r"^(?:-+\s+|\*\s+)", "", text, count=1)


def is_table_separator(text: str) -> bool:
    return bool(re.fullmatch(r"\|?[\s:\-|]+\|?", text))


def split_table_row(text: str) -> list[str]:
    return [normalize_inline(cell) for cell in text.strip().strip("|").split("|")]


def parse_table(lines: list[str]) -> Block | None:
    if len(lines) < 2:
        return None
    headers = split_table_row(lines[0])
    start_row = 1
    if is_table_separator(lines[1]):
        start_row = 2
    rows = [split_table_row(line) for line in lines[start_row:]]
    width = len(headers)
    normalized_rows: list[list[str]] = []
    for row in rows:
        row = row[:width] + [""] * max(0, width - len(row))
        normalized_rows.append(row)
    return Block(type="table", headers=[strip_markdown(cell) for cell in headers], rows=normalized_rows)


def parse_markdown(text: str) -> list[Block]:
    blocks: list[Block] = []
    lines = text.replace("\ufeff", "").splitlines()
    index = 0
    heading_re = re.compile(r"^(#{1,6})\s*(.*?)\s*$")
    while index < len(lines):
        raw = lines[index].rstrip()
        stripped = raw.strip()
        if not stripped:
            index += 1
            continue

        heading_match = heading_re.match(stripped)
        if heading_match:
            title = strip_markdown(heading_match.group(2))
            if title:
                blocks.append(Block(type="heading", text=title, level=len(heading_match.group(1))))
            index += 1
            continue

        if re.fullmatch(r"-{3,}", stripped):
            blocks.append(Block(type="hr"))
            index += 1
            continue

        if stripped.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            table = parse_table(table_lines)
            if table:
                blocks.append(table)
            continue

        if stripped.startswith(">"):
            quotes: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                content = normalize_inline(lines[index].strip()[1:].strip())
                if content:
                    quotes.append(content)
                index += 1
            if quotes:
                blocks.append(Block(type="quote_group", items=quotes))
            continue

        if is_list_line(stripped):
            ordered = bool(re.match(r"^\d+\.\s+", stripped))
            items: list[str] = []
            while index < len(lines) and is_list_line(lines[index].strip()):
                _, item = strip_list_marker(lines[index].strip())
                items.append(normalize_inline(item))
                index += 1
            blocks.append(Block(type="list", ordered=ordered, items=items))
            continue

        paragraph_lines: list[str] = []
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if (
                heading_re.match(candidate)
                or candidate.startswith("|")
                or candidate.startswith(">")
                or is_list_line(candidate)
                or re.fullmatch(r"-{3,}", candidate)
            ):
                break
            paragraph_lines.append(normalize_inline(candidate))
            index += 1
        if paragraph_lines:
            blocks.append(Block(type="paragraph", text=" ".join(paragraph_lines)))
            continue
        index += 1
    return blocks


def semantic_heading_level(title: str, markdown_level: int) -> int:
    if re.match(r"^[一二三四五六七八九十]+、", title):
        return 1
    if re.match(r"^\d+\.\d+\.\d+\.\d+", title):
        return 4
    if re.match(r"^\d+\.\d+\.\d+", title):
        return 3
    if re.match(r"^\d+\.\d+", title):
        return 2
    if re.match(r"^(案例[一二三四五六七八九十]|短期策略|中期策略|长期策略)", title):
        return 3
    return min(max(markdown_level, 1), 4)


def build_section_tree(blocks: list[Block]) -> list[Section]:
    roots: list[Section] = []
    stack: list[Section] = []
    counter = 0
    for block in blocks:
        if block.type == "heading":
            counter += 1
            level = semantic_heading_level(block.text, block.level)
            section = Section(title=block.text, level=level, anchor=f"section-{counter}")
            while stack and stack[-1].level >= level:
                stack.pop()
            if stack:
                stack[-1].children.append(section)
            else:
                roots.append(section)
            stack.append(section)
            continue
        if stack:
            stack[-1].blocks.append(block)
    return roots


def flatten_sections(sections: list[Section]) -> list[Section]:
    result: list[Section] = []
    for section in sections:
        result.append(section)
        result.extend(flatten_sections(section.children))
    return result


def find_section(sections: list[Section], title: str) -> Section | None:
    for section in flatten_sections(sections):
        if section.title == title:
            return section
    return None


def first_table(section: Section | None) -> Block | None:
    if not section:
        return None
    for block in section.blocks:
        if block.type == "table":
            return block
    return None


def table_to_records(table: Block | None) -> list[dict[str, str]]:
    if not table or table.type != "table":
        return []
    records: list[dict[str, str]] = []
    for row in table.rows:
        record = {}
        for index, header in enumerate(table.headers):
            record[header] = strip_markdown(row[index]) if index < len(row) else ""
        records.append(record)
    return records


def parse_int(text: str) -> int:
    match = re.search(r"-?\d[\d,]*", text.replace("，", ","))
    return int(match.group(0).replace(",", "")) if match else 0


def parse_percent(text: str) -> float:
    match = re.search(r"(-?\d+(?:\.\d+)?)%", text)
    return float(match.group(1)) / 100 if match else 0.0


def extract_distribution(table: Block | None) -> list[dict[str, float | int | str]]:
    records = table_to_records(table)
    if not records:
        return []
    headers = table.headers
    label_key = headers[0]
    count_key = headers[1] if len(headers) > 1 else headers[0]
    share_key = headers[2] if len(headers) > 2 else None
    items = []
    for record in records:
        items.append(
            {
                "name": record.get(label_key, ""),
                "count": parse_int(record.get(count_key, "")),
                "share": parse_percent(record.get(share_key, "")) if share_key else 0.0,
            }
        )
    return items


def extract_top5(table: Block | None) -> list[dict[str, int | str]]:
    records = table_to_records(table)
    if not records:
        return []
    headers = table.headers
    label_key = headers[1] if len(headers) > 1 else headers[0]
    count_key = headers[2] if len(headers) > 2 else headers[-1]
    return [{"name": record.get(label_key, ""), "count": parse_int(record.get(count_key, ""))} for record in records]


def extract_trend(table: Block | None) -> list[dict[str, object]]:
    records = table_to_records(table)
    if not records:
        return []
    headers = table.headers
    date_key = headers[0]
    count_key = headers[1]
    negative_count_key = headers[2]
    negative_ratio_key = headers[3]
    matchday_key = headers[4] if len(headers) > 4 else None
    trend = []
    for record in records:
        trend.append(
            {
                "date": record.get(date_key, ""),
                "count": parse_int(record.get(count_key, "")),
                "negative_count": parse_int(record.get(negative_count_key, "")),
                "negative_ratio": parse_percent(record.get(negative_ratio_key, "")),
                "is_matchday": record.get(matchday_key, "") == "是" if matchday_key else False,
            }
        )
    return trend


def extract_events(section: Section | None, year_hint: int) -> list[dict[str, str]]:
    if not section:
        return []
    events: list[dict[str, str]] = []
    for block in section.blocks:
        if block.type != "list":
            continue
        for item in block.items:
            match = re.match(r"(\d{2}-\d{2})[：:](.+)", strip_markdown(item))
            if not match:
                continue
            date_key = f"{year_hint}-{match.group(1)}"
            events.append({"date": date_key, "summary": match.group(2).strip()})
    return events


def extract_service(records_table: Block | None) -> dict[str, list[dict[str, int | str]]]:
    grouped: dict[str, list[dict[str, int | str]]] = {}
    for record in table_to_records(records_table):
        dimension = record.get("维度", "")
        grouped.setdefault(dimension, []).append({"name": record.get("标签", ""), "count": parse_int(record.get("数量", ""))})
    return grouped


def extract_overview_cards(table: Block | None) -> list[dict[str, str]]:
    records = table_to_records(table)
    cards = []
    for record in records:
        cards.append(
            {
                "metric": record.get("指标", ""),
                "value": record.get("数值", ""),
                "desc": record.get("说明", ""),
            }
        )
    return cards


def extract_provinces(table: Block | None, limit: int = 10) -> list[dict[str, object]]:
    records = table_to_records(table)
    provinces = []
    for record in records[:limit]:
        provinces.append(
            {
                "name": record.get("省份", ""),
                "count": parse_int(record.get("问题总量", "")),
                "share": parse_percent(record.get("总量占比", "")),
                "emotion": record.get("主导情绪", ""),
                "focus": record.get("焦点关键词", ""),
            }
        )
    return provinces


def aggregate_items(items: list[dict[str, object]], limit: int = 6) -> list[dict[str, object]]:
    visible = [dict(item) for item in items if int(item.get("count", 0)) > 0]
    if len(visible) <= limit:
        return visible
    retained = visible[: limit - 1]
    remainder = visible[limit - 1 :]
    retained.append({"name": "其他", "count": sum(int(item.get("count", 0)) for item in remainder), "share": 0.0})
    return retained


def polar_to_xy(cx: float, cy: float, radius: float, angle_deg: float) -> tuple[float, float]:
    radians = math.radians(angle_deg - 90)
    return cx + radius * math.cos(radians), cy + radius * math.sin(radians)


def arc_path(cx: float, cy: float, outer_r: float, inner_r: float, start_angle: float, end_angle: float) -> str:
    start_outer = polar_to_xy(cx, cy, outer_r, start_angle)
    end_outer = polar_to_xy(cx, cy, outer_r, end_angle)
    start_inner = polar_to_xy(cx, cy, inner_r, end_angle)
    end_inner = polar_to_xy(cx, cy, inner_r, start_angle)
    large_arc = 1 if end_angle - start_angle > 180 else 0
    return (
        f"M {start_outer[0]:.2f} {start_outer[1]:.2f} "
        f"A {outer_r:.2f} {outer_r:.2f} 0 {large_arc} 1 {end_outer[0]:.2f} {end_outer[1]:.2f} "
        f"L {start_inner[0]:.2f} {start_inner[1]:.2f} "
        f"A {inner_r:.2f} {inner_r:.2f} 0 {large_arc} 0 {end_inner[0]:.2f} {end_inner[1]:.2f} Z"
    )


def nice_upper_bound(value: int) -> int:
    if value <= 0:
        return 1
    magnitude = 10 ** int(math.floor(math.log10(value)))
    normalized = value / magnitude
    if normalized <= 1:
        factor = 1
    elif normalized <= 2:
        factor = 2
    elif normalized <= 3:
        factor = 3
    elif normalized <= 4:
        factor = 4
    elif normalized <= 5:
        factor = 5
    elif normalized <= 6:
        factor = 6
    elif normalized <= 8:
        factor = 8
    else:
        factor = 10
    return factor * magnitude


def donut_chart_svg(title: str, items: list[dict[str, object]], total_label: str) -> str:
    visible = aggregate_items(items, limit=6)
    total = sum(int(item.get("count", 0)) for item in visible)
    width, height = 760, 430
    cx, cy, outer_r, inner_r = 200, 215, 120, 72
    legend_x = 404
    angle = 0.0
    slices = []
    legend_rows = []
    for index, item in enumerate(visible):
        count = int(item.get("count", 0))
        share = count / total if total else 0
        next_angle = angle + share * 360
        color = CHART_COLORS[index % len(CHART_COLORS)]
        if share >= 0.999:
            slices.append(f'<circle cx="{cx}" cy="{cy}" r="{outer_r}" fill="{color}" />')
        else:
            slices.append(f'<path d="{arc_path(cx, cy, outer_r, inner_r, angle, next_angle)}" fill="{color}" />')
        legend_y = 112 + index * 42
        legend_rows.append(
            f"""
            <g transform="translate({legend_x},{legend_y})">
              <rect width="12" height="12" rx="4" fill="{color}" />
              <text x="22" y="10" font-size="15" fill="#0f172a">{escape(str(item.get("name", "")))}</text>
              <text x="236" y="10" font-size="15" text-anchor="end" fill="#0f172a">{count}</text>
              <text x="310" y="10" font-size="13" text-anchor="end" fill="#64748b">{share * 100:.1f}%</text>
            </g>
            """
        )
        angle = next_angle
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="28" fill="#ffffff" stroke="#e2e8f0" />
  <text x="44" y="56" font-size="22" font-weight="700" fill="#0f172a">{escape(title)}</text>
  <text x="44" y="84" font-size="13" fill="#64748b">根据表格数据重建原图</text>
  {''.join(slices)}
  <circle cx="{cx}" cy="{cy}" r="{inner_r}" fill="#ffffff" />
  <text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="38" font-weight="700" fill="#0f172a">{total}</text>
  <text x="{cx}" y="{cy + 24}" text-anchor="middle" font-size="14" fill="#64748b">{escape(total_label)}</text>
  {''.join(legend_rows)}
</svg>
"""


def hbar_chart_svg(title: str, items: list[dict[str, object]], show_rank: bool = False) -> str:
    visible = [item for item in items if int(item.get("count", 0)) > 0]
    width = 900
    row_height = 54
    height = 132 + max(1, len(visible)) * row_height
    max_value = max((int(item.get("count", 0)) for item in visible), default=1)
    rows = []
    for index, item in enumerate(visible):
        y = 100 + index * row_height
        count = int(item.get("count", 0))
        width_ratio = count / max_value if max_value else 0
        fill_width = 420 * width_ratio
        rows.append(
            f"""
            <g transform="translate(0,{y})">
              <text x="52" y="16" font-size="14" fill="#0f172a">{index + 1:02d}</text>
              <text x="104" y="16" font-size="15" fill="#0f172a">{escape(str(item.get("name", "")))}</text>
              <rect x="338" y="0" width="430" height="16" rx="8" fill="#e2e8f0" />
              <rect x="338" y="0" width="{fill_width:.1f}" height="16" rx="8" fill="url(#barGradient)" />
              <text x="810" y="15" font-size="14" text-anchor="end" fill="#64748b">{count}</text>
            </g>
            """
        )
    rank_note = "TOP 排名图" if show_rank else "横向条形图"
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="barGradient" x1="0%" x2="100%">
      <stop offset="0%" stop-color="#0052FF" />
      <stop offset="100%" stop-color="#4D7CFF" />
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="28" fill="#ffffff" stroke="#e2e8f0" />
  <text x="44" y="56" font-size="22" font-weight="700" fill="#0f172a">{escape(title)}</text>
  <text x="44" y="84" font-size="13" fill="#64748b">原图类型：{rank_note}</text>
  {''.join(rows)}
</svg>
"""


def trend_chart_svg(title: str, days: list[dict[str, object]], events: dict[str, str]) -> str:
    width, height = 1180, 470
    left, right, top, bottom = 78, 92, 72, 72
    plot_width = width - left - right
    plot_height = height - top - bottom
    count_max = nice_upper_bound(max((int(day["count"]) for day in days), default=1))
    denom = max(1, len(days) - 1)

    def x_at(index: int) -> float:
        return left + index * plot_width / denom

    def y_count(value: float) -> float:
        return top + (1 - value / count_max) * plot_height

    def y_ratio(value: float) -> float:
        return top + (1 - value) * plot_height

    count_points = [(x_at(index), y_count(float(day["count"]))) for index, day in enumerate(days)]
    ratio_points = [(x_at(index), y_ratio(float(day["negative_ratio"]))) for index, day in enumerate(days)]
    count_path = " ".join(f"{x:.1f},{y:.1f}" for x, y in count_points)
    ratio_path = " ".join(f"{x:.1f},{y:.1f}" for x, y in ratio_points)
    area_path = f"M {left:.1f},{top + plot_height:.1f} L {count_path} L {left + plot_width:.1f},{top + plot_height:.1f} Z"

    peak = max(days, key=lambda day: int(day["count"]))
    peak_index = days.index(peak)

    grid_lines = []
    for tick in range(6):
        y = top + tick * plot_height / 5
        count_value = count_max * (1 - tick / 5)
        ratio_value = 1 - tick / 5
        grid_lines.append(
            f"""
            <line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="rgba(148,163,184,0.22)" />
            <text x="{left - 16}" y="{y + 5:.1f}" text-anchor="end" font-size="12" fill="#64748b">{int(round(count_value))}</text>
            <text x="{width - right + 16}" y="{y + 5:.1f}" font-size="12" fill="#64748b">{ratio_value * 100:.0f}%</text>
            """
        )

    x_labels = []
    label_step = max(1, math.ceil(len(days) / 8))
    for index, day in enumerate(days):
        if index % label_step == 0 or index == len(days) - 1:
            x_labels.append(
                f'<text x="{x_at(index):.1f}" y="{height - 28}" text-anchor="middle" font-size="12" fill="#7e7264">{escape(str(day["date"])[5:])}</text>'
            )

    event_marks = []
    point_marks = []
    for index, day in enumerate(days):
        x = x_at(index)
        if bool(day["is_matchday"]):
            event_marks.append(
                f"""
                <rect x="{x - 7:.1f}" y="{top}" width="14" height="{plot_height}" fill="rgba(255,151,28,0.08)" />
                <line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height - bottom}" stroke="rgba(0,82,255,0.26)" stroke-dasharray="4 8" />
                """
            )
        point_marks.append(
            f"""
            <circle cx="{count_points[index][0]:.1f}" cy="{count_points[index][1]:.1f}" r="4.6" fill="#0f172a" />
            <circle cx="{ratio_points[index][0]:.1f}" cy="{ratio_points[index][1]:.1f}" r="4.6" fill="#0052FF" />
            """
        )

    peak_x = x_at(peak_index)
    peak_y = y_count(float(peak["count"]))
    peak_label = f"峰值 {str(peak['date'])[5:]} | {peak['count']} 件"
    if bool(peak["is_matchday"]):
        peak_label += " | 赛事日"

    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="countLine" x1="0%" x2="100%">
      <stop offset="0%" stop-color="#0F172A" />
      <stop offset="100%" stop-color="#334155" />
    </linearGradient>
    <linearGradient id="countArea" x1="0%" x2="0%" y1="0%" y2="100%">
      <stop offset="0%" stop-color="rgba(15,23,42,0.18)" />
      <stop offset="100%" stop-color="rgba(15,23,42,0.02)" />
    </linearGradient>
    <linearGradient id="ratioLine" x1="0%" x2="100%">
      <stop offset="0%" stop-color="#0052FF" />
      <stop offset="100%" stop-color="#4D7CFF" />
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="28" fill="#ffffff" stroke="#e2e8f0" />
  <text x="44" y="56" font-size="22" font-weight="700" fill="#0f172a">{escape(title)}</text>
  <text x="44" y="84" font-size="13" fill="#64748b">问题量与负向情绪占比双轴重建图</text>
  {''.join(grid_lines)}
  <line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="rgba(148,163,184,0.28)" />
  <line x1="{width - right}" y1="{top}" x2="{width - right}" y2="{height - bottom}" stroke="rgba(148,163,184,0.28)" />
  <line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="rgba(148,163,184,0.28)" />
  {''.join(event_marks)}
  <path d="{area_path}" fill="url(#countArea)" />
  <polyline points="{count_path}" fill="none" stroke="url(#countLine)" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  <polyline points="{ratio_path}" fill="none" stroke="url(#ratioLine)" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
  {''.join(point_marks)}
  <rect x="{min(max(peak_x - 84, left + 10), width - right - 188):.1f}" y="{max(24, peak_y - 48):.1f}" width="188" height="34" rx="10" fill="rgba(0,82,255,0.08)" stroke="rgba(0,82,255,0.16)" />
  <text x="{min(max(peak_x - 84, left + 10), width - right - 188) + 94:.1f}" y="{max(24, peak_y - 48) + 22:.1f}" text-anchor="middle" font-size="13" fill="#0f172a">{escape(peak_label)}</text>
  <text x="{left}" y="42" font-size="13" fill="#64748b">问题量</text>
  <text x="{width - right}" y="42" text-anchor="end" font-size="13" fill="#64748b">负向情绪占比</text>
  {''.join(x_labels)}
</svg>
"""


def province_chart_svg(title: str, provinces: list[dict[str, object]]) -> str:
    return hbar_chart_svg(title, provinces, show_rank=False)


def write_asset(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def pct_text(value: float) -> str:
    return f"{value * 100:.1f}%"


def metric_lookup(grouped: dict[str, list[dict[str, int | str]]], dimension: str, label: str) -> int:
    for item in grouped.get(dimension, []):
        if item["name"] == label:
            return int(item["count"])
    return 0


def render_chart_frame(title: str, src: str, note: str = "", extra_html: str = "") -> str:
    caption = f'<p class="chart-caption">{escape(note)}</p>' if note else ""
    return f"""
    <div class="chart-frame" data-reveal>
      <div class="chart-topline">
        <strong>{escape(title)}</strong>
        <span class="meta-chip">数据重建图</span>
      </div>
      <img src="{src}" alt="{escape(title)}" />
      {extra_html}
      {caption}
    </div>
    """


def render_table(block: Block) -> str:
    head = "".join(f"<th>{render_inline(header)}</th>" for header in block.headers)
    body_rows = []
    for row in block.rows:
        cells = "".join(f"<td>{render_inline(strip_markdown(cell))}</td>" for cell in row[: len(block.headers)])
        body_rows.append(f"<tr>{cells}</tr>")
    return f"""
    <div class="table-wrap" data-reveal>
      <table>
        <thead><tr>{head}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </div>
    """


def render_quotes(block: Block) -> str:
    parts = []
    for index, item in enumerate(block.items):
        bubble_class = "quote-bubble right" if index % 2 else "quote-bubble"
        parts.append(f'<blockquote class="{bubble_class}">{render_inline(item)}</blockquote>')
    return f'<div class="quote-thread" data-reveal>{"".join(parts)}</div>'


def render_block(block: Block) -> str:
    if block.type == "paragraph":
        return f'<p class="text-paragraph" data-reveal>{render_inline(block.text)}</p>'
    if block.type == "list":
        tag = "ol" if block.ordered else "ul"
        cls = "text-olist" if block.ordered else "text-list"
        items = "".join(f"<li>{render_inline(item)}</li>" for item in block.items)
        return f'<{tag} class="{cls}" data-reveal>{items}</{tag}>'
    if block.type == "quote_group":
        return render_quotes(block)
    if block.type == "table":
        return render_table(block)
    if block.type == "hr":
        return '<hr class="divider" data-reveal />'
    return ""


def render_overview_cards(cards: list[dict[str, str]]) -> str:
    items = []
    for card in cards:
        items.append(
            f"""
            <article class="overview-card" data-reveal>
              <span class="meta-chip">{render_inline(card["metric"])}</span>
              <strong>{render_inline(card["value"])}</strong>
              <p>{render_inline(card["desc"])}</p>
            </article>
            """
        )
    return f'<div class="overview-grid">{"".join(items)}</div>'


def render_service_matrix(grouped: dict[str, list[dict[str, int | str]]]) -> str:
    titles = ["服务类型", "退费诉求", "升级投诉倾向"]
    cards = []
    for title in titles:
        items = grouped.get(title, [])
        top_count = max((int(item["count"]) for item in items), default=0)
        cards.append(
            f"""
            <article class="service-box" data-reveal>
              <h4>{escape(title)}</h4>
              <strong>{top_count}</strong>
              <p>当前维度的头部单项量级</p>
              <div class="service-tags">
                {"".join(f"<span>{escape(str(item['name']))} {int(item['count'])}</span>" for item in items)}
              </div>
            </article>
            """
        )
    return f'<div class="service-matrix">{"".join(cards)}</div>'


def heading_tag(level: int) -> str:
    return {1: "h2", 2: "h3", 3: "h4", 4: "h5"}.get(level, "h4")


def render_section(
    section: Section,
    chart_html: dict[str, str],
    overview_cards: list[dict[str, str]],
    service_grouped: dict[str, list[dict[str, int | str]]],
) -> str:
    tag = heading_tag(section.level)
    section_parts = [
        f'<section class="report-section level-{section.level}" id="{section.anchor}" data-anchor-target>',
        '<div class="section-head">',
        f'<div><div class="section-label">{"章节概览" if section.level == 1 else "报告内容"}</div><{tag} class="section-heading level-{section.level}">{render_inline(section.title)}</{tag}></div>',
        f'<div class="section-meta">{escape("一级模块" if section.level == 1 else "子模块")}</div>',
        "</div>",
        '<div class="section-body">',
    ]

    if section.title in chart_html:
        section_parts.append(chart_html[section.title])

    skip_first_table = False
    if section.title == "概览卡片" and overview_cards:
        section_parts.append(render_overview_cards(overview_cards))
        skip_first_table = True
    if section.title == "1.2.3 服务类型与升级风险" and service_grouped:
        section_parts.append(render_service_matrix(service_grouped))
        skip_first_table = True

    for block in section.blocks:
        if skip_first_table and block.type == "table":
            skip_first_table = False
            continue
        section_parts.append(render_block(block))

    for child in section.children:
        section_parts.append(render_section(child, chart_html, overview_cards, service_grouped))

    section_parts.extend(["</div>", "</section>"])
    return "".join(section_parts)


def build_toc(sections: list[Section]) -> str:
    links = []
    for section in flatten_sections(sections):
        if section.level > 2:
            continue
        links.append(
            f'<a class="toc-link level-{section.level}" href="#{section.anchor}"><span>{escape(section.title)}</span><small>{section.level}</small></a>'
        )
    return "".join(links)


def build_sidebar(
    total: int,
    refund_count: int,
    escalation_count: int,
    matchday_avg: float,
    non_matchday_avg: float,
    tag_items: list[str],
    toc_html: str,
) -> str:
    tags_html = "".join(f'<span class="tag-chip">{escape(item)}</span>' for item in tag_items if item)
    risk_html = "".join(
        [
            f'<span class="risk-chip">退费诉求 {refund_count}</span>',
            f'<span class="risk-chip">升级倾向 {escalation_count}</span>',
            f'<span class="risk-chip">赛事日日均 {matchday_avg:.1f}</span>',
            f'<span class="risk-chip">非赛事日日均 {non_matchday_avg:.1f}</span>',
        ]
    )
    return f"""
    <aside class="sidebar">
      <section class="sidebar-panel" data-reveal>
        <div class="panel-title">速览指标</div>
        <div class="sidebar-kpi">
          <article class="mini-card"><strong>{total}</strong><span>问题样本</span></article>
          <article class="mini-card"><strong>{refund_count}</strong><span>明确退费诉求</span></article>
          <article class="mini-card"><strong>{escalation_count}</strong><span>升级投诉倾向</span></article>
          <article class="mini-card"><strong>6</strong><span>已重建图表</span></article>
        </div>
      </section>

      <section class="sidebar-panel" data-reveal>
        <div class="panel-title">用户标签</div>
        <div class="tag-stack">{tags_html}</div>
      </section>

      <section class="sidebar-panel" data-reveal>
        <div class="panel-title">风险提示</div>
        <div class="risk-stack">{risk_html}</div>
      </section>

      <section class="sidebar-panel" data-reveal>
        <div class="panel-title">章节导航</div>
        <nav class="toc">{toc_html}</nav>
      </section>
    </aside>
    """


def build_summary_cards(
    top_primary: dict[str, object],
    top_tertiary: dict[str, object],
    peak_day: dict[str, object],
) -> str:
    cards = [
        {
            "value": f"{top_primary.get('name', '无')}",
            "label": f"一级主问题 · {int(top_primary.get('count', 0))} 条",
            "desc": "一级标签头部类型，适合作为专项治理的首要入口。",
        },
        {
            "value": f"{top_tertiary.get('name', '无')}",
            "label": f"三级热点 · {int(top_tertiary.get('count', 0))} 条",
            "desc": "细分问题中最高频的投诉焦点，建议优先建立闭环动作。",
        },
        {
            "value": f"{str(peak_day.get('date', ''))[5:] or '无'}",
            "label": f"投诉峰值 · {int(peak_day.get('count', 0))} 件",
            "desc": "按日投诉量的最高点，用于对齐赛事节点和运营动作。",
        },
    ]
    parts = []
    for card in cards:
        parts.append(
            f"""
            <article class="summary-card" data-reveal>
              <span>{escape(card["label"])}</span>
              <strong>{escape(card["value"])}</strong>
              <small>{escape(card["desc"])}</small>
            </article>
            """
        )
    return "".join(parts)


def build_html(
    sections: list[Section],
    chart_html: dict[str, str],
    overview_cards: list[dict[str, str]],
    service_grouped: dict[str, list[dict[str, int | str]]],
    total: int,
    period_text: str,
    top_primary: dict[str, object],
    top_tertiary: dict[str, object],
    peak_day: dict[str, object],
    refund_count: int,
    escalation_count: int,
    matchday_avg: float,
    non_matchday_avg: float,
    tag_items: list[str],
) -> str:
    toc_html = build_toc(sections)
    summary_cards = build_summary_cards(top_primary, top_tertiary, peak_day)
    report_sections = "".join(render_section(section, chart_html, overview_cards, service_grouped) for section in sections)
    spotlight_tags = "".join(f'<span class="meta-chip">{escape(item)}</span>' for item in tag_items if item)
    hero_peak_label = escape(str(peak_day.get("date", ""))[5:]) or "无"
    hero_top_primary = escape(str(top_primary.get("name", "无")))
    hero_top_tertiary = escape(str(top_tertiary.get("name", "无")))

    html_parts = [
        "<!doctype html><html lang=\"zh-CN\"><head>",
        '<meta charset="utf-8" />',
        '<meta name="viewport" content="width=device-width, initial-scale=1" />',
        "<title>整体情况报告</title>",
        "<style>",
        CSS,
        "</style></head><body>",
        '<div class="progress-bar"><span></span></div>',
        '<header class="topbar"><div class="topbar-inner">',
        '<div class="brand"><div class="brand-mark" aria-hidden="true"></div><div class="brand-copy"><strong>Service Insight</strong><span>Minimalist Modern Report View</span></div></div>',
        '<nav class="tabs" aria-label="主导航">',
        '<a href="javascript:void(0)" class="active">Overall</a>',
        '<a href="javascript:void(0)">Trend</a>',
        '<a href="javascript:void(0)">Cluster</a>',
        '<a href="javascript:void(0)">Action</a>',
        "</nav>",
        '<div class="topbar-actions"><span class="topbar-badge">2026 CSL</span><span class="avatar">A</span><span>Analyst</span></div>',
        "</div></header>",
        '<div class="app-shell">',
        '<main class="main">',
        '<section class="hero-panel">',
        '<div class="hero-shell">',
        '<div class="hero-copy">',
        '<span class="hero-kicker">CSL season complaint intelligence</span>',
        '<h1 class="hero-title">把 <strong>峰值、结构与地域短板</strong> 放进一张可直接浏览的洞察页</h1>',
        f'<p class="hero-deck">{escape(period_text)} 共纳入 {total} 条相关问题样本。一级主问题为 {hero_top_primary}，最高频三级问题为 {hero_top_tertiary}，投诉峰值出现在 {hero_peak_label}。</p>',
        '<div class="hero-chip-row">',
        f'<span class="hero-chip">样本总量 {total}</span>',
        f'<span class="hero-chip">一级主问题 {hero_top_primary}</span>',
        f'<span class="hero-chip">峰值日期 {hero_peak_label}</span>',
        f'<span class="hero-chip">退费诉求 {refund_count}</span>',
        f'<span class="hero-chip">升级倾向 {escalation_count}</span>',
        "</div></div>",
        '<div class="hero-visual" aria-hidden="true">',
        '<div class="hero-orb"></div>',
        '<div class="hero-ring ring-a"></div>',
        '<div class="hero-ring ring-b"></div>',
        '<div class="hero-ring ring-c"></div>',
        f'<div class="floating-panel panel-main"><span>Top issue</span><strong>{hero_top_tertiary}</strong><small>{int(top_tertiary.get("count", 0))} 条提及</small></div>',
        f'<div class="floating-panel panel-side"><span>Peak day</span><strong>{hero_peak_label}</strong><small>{int(peak_day.get("count", 0))} 件 / 赛事日峰值</small></div>',
        f'<div class="floating-panel panel-bottom"><span>Matchday lift</span><strong>{matchday_avg:.1f} : {non_matchday_avg:.1f}</strong><small>赛事日日均问题量 vs 非赛事日</small></div>',
        '<div class="hero-grid-dots"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>',
        "</div></div></section>",
        f'<section class="anchor-band" data-reveal><nav class="toc" aria-label="章节导航">{toc_html}</nav></section>',
        '<section class="workspace-panel" data-reveal><div class="spotlight-card">',
        '<div class="workspace-header"><div><div class="section-label">Selected KPIs</div><h2>重建图表与关键指标</h2><p>参考 Minimalist Modern 视觉方向，保留图表数据真实性，把重点信息前置在单列阅读流里。</p></div><span class="meta-chip">无侧边栏版</span></div>',
        f'<div class="summary-cards">{summary_cards}</div>',
        f'<div class="event-strip" style="margin-top:18px;">{spotlight_tags}</div>',
        "</div></section>",
        '<div class="report-stream">',
        report_sections,
        "</div>",
        '<section class="footer-note" data-reveal><p>这版页面改成了单列叙事结构，移除了侧边栏，视觉方向参考 `webpage_design_prompt.md` 的 Minimalist Modern：蓝色渐变、深浅反差段落、显示型标题和更轻的工作台信息层级。SVG 图表仍由 Markdown 中的数据直接生成。</p></section>',
        "</main></div>",
        "<script>",
        JS,
        "</script></body></html>",
    ]
    return "".join(html_parts)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    default_md = script_dir / "outputs" / "整体情况报告.md"
    source_md = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_md
    output_html = (
        Path(sys.argv[2]).resolve()
        if len(sys.argv) > 2
        else source_md.with_name("整体情况报告_极简现代无侧栏版.html")
    )
    asset_dir = source_md.parent / "report_dashboard_assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    markdown_text = source_md.read_text(encoding="utf-8")
    blocks = parse_markdown(markdown_text)
    sections = build_section_tree(blocks)

    primary = extract_distribution(first_table(find_section(sections, "1.1.1 一级标签类型分布")))
    secondary = extract_distribution(first_table(find_section(sections, "1.1.2 二级标签类型分布")))
    tertiary = extract_distribution(first_table(find_section(sections, "1.1.3 三级标签类型分布")))
    top5 = extract_top5(first_table(find_section(sections, "1.1.4 TOP5 三级问题提及量")))
    trend = extract_trend(first_table(find_section(sections, "1.2.1.3 折线图数据表")))
    year_hint = int(str(trend[0]["date"])[:4]) if trend else 2026
    emotion = extract_distribution(first_table(find_section(sections, "1.2.2 情绪分布")))
    service_grouped = extract_service(first_table(find_section(sections, "1.2.3 服务类型与升级风险")))
    overview_cards = extract_overview_cards(first_table(find_section(sections, "概览卡片")))
    provinces = extract_provinces(first_table(find_section(sections, "省份问题分布明细表")))
    event_items = extract_events(find_section(sections, "1.2.1.2 赛事日标注"), year_hint)
    event_map = {item["date"]: item["summary"] for item in event_items}

    top_primary = primary[0] if primary else {}
    top_tertiary = top5[0] if top5 else {}
    peak_day = max(trend, key=lambda day: int(day["count"])) if trend else {}
    total = sum(int(item.get("count", 0)) for item in primary)
    refund_count = metric_lookup(service_grouped, "退费诉求", "是")
    escalation_count = metric_lookup(service_grouped, "升级投诉倾向", "是")

    matchday_days = [day for day in trend if bool(day["is_matchday"])]
    non_matchday_days = [day for day in trend if not bool(day["is_matchday"])]
    matchday_avg = sum(int(day["count"]) for day in matchday_days) / len(matchday_days) if matchday_days else 0.0
    non_matchday_avg = sum(int(day["count"]) for day in non_matchday_days) / len(non_matchday_days) if non_matchday_days else 0.0
    period_text = f"{trend[0]['date']} 至 {trend[-1]['date']}" if trend else "未识别到日期"

    chart_paths = {
        "1.1.1 一级标签类型分布": asset_dir / "primary_donut.svg",
        "1.1.2 二级标签类型分布": asset_dir / "secondary_donut.svg",
        "1.1.3 三级标签类型分布": asset_dir / "tertiary_donut.svg",
        "1.1.4 TOP5 三级问题提及量": asset_dir / "top5_bar.svg",
        "1.2.1 每日问题提及量与负向情绪占比": asset_dir / "trend_line.svg",
        "1.2.2 情绪分布": asset_dir / "emotion_bar.svg",
    }

    write_asset(chart_paths["1.1.1 一级标签类型分布"], donut_chart_svg("一级标签类型分布", primary, "一级标签提及量"))
    write_asset(chart_paths["1.1.2 二级标签类型分布"], donut_chart_svg("二级标签类型分布", secondary, "二级标签提及量"))
    write_asset(chart_paths["1.1.3 三级标签类型分布"], donut_chart_svg("三级标签类型分布", tertiary, "三级标签提及量"))
    write_asset(chart_paths["1.1.4 TOP5 三级问题提及量"], hbar_chart_svg("TOP5 三级问题提及量", top5, show_rank=True))
    write_asset(chart_paths["1.2.1 每日问题提及量与负向情绪占比"], trend_chart_svg("每日问题提及量与负向情绪占比", trend, event_map))
    write_asset(chart_paths["1.2.2 情绪分布"], hbar_chart_svg("情绪分布", emotion, show_rank=False))

    province_asset = asset_dir / "province_bar.svg"
    if provinces:
        write_asset(province_asset, province_chart_svg("省份问题分布", provinces))

    chart_html: dict[str, str] = {}
    for title, path in chart_paths.items():
        rel_path = quote(path.relative_to(source_md.parent).as_posix())
        note = "按 Markdown 表格中的数据生成 SVG 图。" if title != "1.2.1 每日问题提及量与负向情绪占比" else "按折线图数据表重建双轴趋势图，并在赛事日打点。"
        extra_html = ""
        if title == "1.2.1 每日问题提及量与负向情绪占比" and event_items:
            chips = "".join(
                f'<span class="event-chip">{escape(item["date"][5:])} · {escape(item["summary"])}</span>' for item in event_items
            )
            extra_html = f'<div class="event-strip">{chips}</div>'
        chart_html[title] = render_chart_frame(strip_markdown(title), rel_path, note, extra_html)

    if provinces:
        rel_path = quote(province_asset.relative_to(source_md.parent).as_posix())
        chart_html["2.1 区域聚类分析"] = render_chart_frame("省份问题分布", rel_path, "补充生成的区域分布图，帮助减少表格阅读负担。")

    tag_items = [
        str(top_primary.get("name", "")),
        str(top_tertiary.get("name", "")),
        str(secondary[0]["name"]) if secondary else "",
        str(tertiary[0]["name"]) if tertiary else "",
        "比赛日波峰",
        "退费争议",
        "权益兑换",
    ]

    html = build_html(
        sections=sections,
        chart_html=chart_html,
        overview_cards=overview_cards,
        service_grouped=service_grouped,
        total=total,
        period_text=period_text,
        top_primary=top_primary,
        top_tertiary=top_tertiary,
        peak_day=peak_day,
        refund_count=refund_count,
        escalation_count=escalation_count,
        matchday_avg=matchday_avg,
        non_matchday_avg=non_matchday_avg,
        tag_items=tag_items,
    )
    output_html.write_text(html, encoding="utf-8")
    output_markdown = output_html.with_suffix(".md")
    if output_markdown.resolve() != source_md.resolve():
        output_markdown.write_text(markdown_text, encoding="utf-8")

    print(output_html)
    print(output_markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
