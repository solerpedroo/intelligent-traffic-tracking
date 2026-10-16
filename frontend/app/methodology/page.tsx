export default function MethodologyPage() {
  return (
    <main>
      <h1>Methodology</h1>
      <p className="intro">
        Detection, association, and counting do not share a denominator. A
        missing reference is not evaluated. It is not stored as zero, and it is
        not averaged as zero.
      </p>
      <section aria-labelledby="split-title">
        <h2 id="split-title">Frozen split</h2>
        <ul>
          <li>Test: MOT15-PETS09-S2L1</li>
          <li>Development: MOT15-TUD-Stadtmitte</li>
          <li>Validation: MOT15-KITTI-17</li>
        </ul>
        <p>
          The assignment used duration and the official sequence description
          before inference. The Stanford Drone Dataset was not available as a
          local archive.
        </p>
      </section>
      <section aria-labelledby="metrics-title">
        <h2 id="metrics-title">What this interface will not invent</h2>
        <ul>
          <li>
            MOT and confirmed ID switches require ground truth. A job without
            that reference stays not evaluated.
          </li>
          <li>
            Counting on the MOT15 sequences stays not evaluated because those
            files have no line-crossing annotations.
          </li>
          <li>
            Experiments A, B, and C changed one recorded factor at a time. Three
            sequences do not support a significance claim.
          </li>
          <li>
            The pages do not estimate physical congestion or a causal effect
            from two incompatible runs.
          </li>
        </ul>
      </section>
      <section aria-labelledby="sources-title">
        <h2 id="sources-title">Sources</h2>
        <p>
          The numeric protocol, the measured baseline, and the A/B/C report live
          in the repository documents evaluation-protocol, evaluation, and
          methodology. This page does not add article links that those notes do
          not record.
        </p>
      </section>
    </main>
  );
}
