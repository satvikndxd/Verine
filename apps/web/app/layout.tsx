import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "VERINE NERVE",
  description:
    "Capability-level crisis compiler (synthetic prototype). Simulation results, not real-world forecasts.",
};

const nav = [
  { href: "/", label: "Launcher" },
  { href: "/war-room", label: "War Room" },
  { href: "/scenarios", label: "Scenarios" },
  { href: "/cases", label: "Case Files" },
  { href: "/evidence", label: "Evidence" },
  { href: "/experiments", label: "Experiments" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b border-[var(--border)] bg-[var(--bg-panel)]">
          <div className="mx-auto flex max-w-[1500px] items-center gap-6 px-5 py-2.5">
            <Link href="/" className="text-sm font-bold tracking-[0.2em] text-[var(--text)]">
              VERINE <span className="text-[var(--amber)]">NERVE</span>
            </Link>
            <nav className="flex gap-4 text-[13px] text-[var(--text-dim)]">
              {nav.map((n) => (
                <Link key={n.href} href={n.href} className="hover:text-[var(--text)]">
                  {n.label}
                </Link>
              ))}
            </nav>
            <span className="ml-auto badge text-[var(--violet)]" title="All outputs are simulation results over a synthetic fixture graph">
              SYNTHETIC MODE · v0.1
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-5 py-5">{children}</main>
        <footer className="mx-auto max-w-[1500px] px-5 pb-6 text-[11px] text-[var(--text-dim)]">
          VERINE NERVE v0.1 — synthetic crisis war room. Simulated results are model outputs over a fixture
          graph and are never predictions about real organizations.
        </footer>
      </body>
    </html>
  );
}
