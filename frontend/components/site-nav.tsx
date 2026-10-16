"use client";

import {
  Activity,
  FlaskConical,
  GitCompare,
  LayoutDashboard,
  ListVideo,
  type LucideIcon,
  ScrollText,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS: { href: string; label: string; icon: LucideIcon }[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/workspace", label: "Workspace", icon: FlaskConical },
  { href: "/jobs", label: "Jobs", icon: ListVideo },
  { href: "/analytics", label: "Analytics", icon: Activity },
  { href: "/experiments", label: "Compare", icon: GitCompare },
  { href: "/methodology", label: "Methodology", icon: ScrollText },
];

function active(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteNav() {
  const pathname = usePathname();
  return (
    <>
      <aside className="sidebar-chrome fixed inset-y-0 left-0 z-40 hidden w-[260px] flex-col border-r border-sidebar-border lg:flex">
        <div className="flex h-16 items-center border-b border-sidebar-border px-5">
          <div className="min-w-0 leading-tight">
            <p className="truncate text-sm font-semibold tracking-tight">
              Traffic Tracking
            </p>
            <p className="truncate text-[11px] text-muted-foreground">
              Evidence, not guesses
            </p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Primary">
          <p className="sidebar-section-label px-3 pb-2">Workspace</p>
          {LINKS.map(({ href, label, icon: Icon }) => {
            const current = active(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={current ? "page" : undefined}
                className={cn(
                  "relative flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-[13px] transition-colors",
                  current
                    ? "nav-active font-medium text-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent hover:text-foreground",
                )}
              >
                <Icon className={cn("size-4", current && "text-brand")} />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <nav
        className="sticky top-0 z-30 flex gap-2 overflow-x-auto border-b border-sidebar-border bg-sidebar/90 px-3 py-2 backdrop-blur lg:hidden"
        aria-label="Primary"
      >
        {LINKS.map(({ href, label }) => {
          const current = active(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={current ? "page" : undefined}
              className={cn(
                "shrink-0 rounded-lg px-3 py-2 text-[13px]",
                current
                  ? "nav-active font-medium text-foreground"
                  : "text-muted-foreground",
              )}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
