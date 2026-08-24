"use client";

import { StepState, fmtMin } from "@/lib/api";

interface Props {
  steps: StepState[];
  capabilityId: string;
  targetSl: number;
  floorSl: number;
  currentIndex: number;
  onScrub: (index: number) => void;
}

export default function Timeline({ steps, capabilityId, targetSl, floorSl, currentIndex, onScrub }: Props) {
  if (!steps.length) return null;
  const w = 940;
  const h = 130;
  const pad = 34;
  const maxT = steps[steps.length - 1].t_minutes || 1;

  const x = (t: number) => pad + (t / maxT) * (w - pad - 8);
  const y = (sl: number) => 8 + (1 - sl / Math.max(targetSl, 0.001)) * (h - 30);

  const points = steps.map((s) => `${x(s.t_minutes)},${y(s.service_levels[capabilityId] ?? targetSl)}`).join(" ");
  const cur = steps[currentIndex];

  return (
    <div className="panel p-3" data-testid="timeline">
      <div className="mb-1 flex items-baseline justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)]">
          Service level timeline <span className="label-simulated normal-case">(simulated)</span>
        </h3>
        <div className="text-xs text-[var(--text-dim)]">
          t = <span className="font-semibold text-[var(--text)]">{fmtMin(cur.t_minutes)}</span> · service level{" "}
          <span className="font-semibold text-[var(--text)]">
            {((cur.service_levels[capabilityId] ?? targetSl) * 100).toFixed(1)}%
          </span>
          {cur.effective_actions.length > 0 && (
            <span className="ml-2 text-[var(--green)]">actions active: {cur.effective_actions.join(", ")}</span>
          )}
        </div>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
        <line x1={pad} y1={y(targetSl)} x2={w - 8} y2={y(targetSl)} stroke="var(--green)" strokeDasharray="3 5" strokeWidth="1" />
        <text x={2} y={y(targetSl) + 3} fontSize="9" fill="var(--green)">target</text>
        <line x1={pad} y1={y(floorSl)} x2={w - 8} y2={y(floorSl)} stroke="var(--red)" strokeDasharray="3 5" strokeWidth="1" />
        <text x={2} y={y(floorSl) + 3} fontSize="9" fill="var(--red)">floor</text>
        <polyline points={points} fill="none" stroke="var(--amber)" strokeWidth="1.8" />
        <line x1={x(cur.t_minutes)} y1={4} x2={x(cur.t_minutes)} y2={h - 18} stroke="var(--text)" strokeWidth="1" opacity="0.7" />
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <text key={f} x={x(f * maxT)} y={h - 4} fontSize="9" fill="var(--text-dim)" textAnchor="middle">
            {fmtMin(Math.round(f * maxT))}
          </text>
        ))}
      </svg>
      <input
        type="range"
        min={0}
        max={steps.length - 1}
        value={currentIndex}
        onChange={(e) => onScrub(Number(e.target.value))}
        className="w-full"
        aria-label="Timeline scrubber"
        data-testid="timeline-scrubber"
      />
    </div>
  );
}
