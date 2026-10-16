import Link from "next/link";

const LINKS = [
  ["/", "Overview"],
  ["/workspace", "Workspace"],
  ["/jobs", "Jobs"],
] as const;

export function SiteNav() {
  return (
    <header className="site-header">
      <Link href="/" className="brand">
        Intelligent Traffic Tracking
      </Link>
      <nav aria-label="Primary">
        <ul>
          {LINKS.map(([href, label]) => (
            <li key={href}>
              <Link href={href}>{label}</Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
