import { ApiHealth } from "@/components/api-health";

export default function HomePage() {
  return (
    <main>
      <header>
        <span className="eyebrow">Urban mobility · Computer vision</span>
        <span className="phase">Wave 0 · Foundation</span>
      </header>
      <section aria-labelledby="title">
        <p className="kicker">Intelligent Traffic Tracking</p>
        <h1 id="title">
          Understand movement.
          <br />
          Measure with evidence.
        </h1>
        <p className="intro">
          A foundation for reproducible vehicle and pedestrian tracking,
          crossing counts, and traffic analytics.
        </p>
        <ApiHealth />
      </section>
      <footer>
        The video pipeline, workspace, and scientific benchmarks will be
        delivered in the next implementation waves.
      </footer>
    </main>
  );
}
