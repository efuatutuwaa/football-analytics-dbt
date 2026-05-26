export function ScaleSectionChart() {
  return (
    <section>
      <h2
        id="scale"
        className="scroll-mt-28 mb-6 mt-16 border-t border-border pt-12 font-serif text-[clamp(1.5rem,4vw,2.25rem)] leading-[1.12] tracking-[-0.02em] text-charcoal first:mt-0 first:border-t-0 first:pt-0"
      >
        04 — Scale
      </h2>
      <h3 className="mb-4 mt-10 text-base font-semibold tracking-[-0.01em] text-charcoal">
        When the numbers grew, what actually happened
      </h3>
      <p className="mb-5 text-[0.9375rem] leading-[1.75] text-[#555]">
        Expanding from 9 competitions to 15 produced a runtime increase that initially looked
        alarming — until the underlying player volume change was measured alongside it.
      </p>

      <div className="my-6 space-y-6 rounded-xl border border-stone-200 bg-stone-50 p-6">
        {[
          {
            label: "INGESTION RUNTIME",
            rows: [
              { scope: "9 competitions", pct: 29, display: "12 min" },
              { scope: "15 competitions", pct: 56, display: "23 min" },
            ],
          },
          {
            label: "PLAYER VOLUME",
            rows: [
              { scope: "9 competitions", pct: 39, display: "~16,000" },
              { scope: "15 competitions", pct: 100, display: "~41,000" },
            ],
          },
        ].map((group) => (
          <div key={group.label}>
            <p className="mb-3 text-xs font-semibold tracking-widest text-stone-400">
              {group.label}
            </p>
            <div className="space-y-2">
              {group.rows.map((row) => (
                <div
                  key={row.scope}
                  className="grid grid-cols-[140px_1fr_80px] items-center gap-3"
                >
                  <span className="text-sm text-stone-500">{row.scope}</span>
                  <div className="h-6 overflow-hidden rounded bg-stone-200">
                    <div
                      className="h-full rounded bg-[#8fac9a]"
                      style={{ width: `${row.pct}%` }}
                    />
                  </div>
                  <span className="text-right text-sm font-medium text-stone-700">
                    {row.display}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
        <p className="border-t border-stone-200 pt-2 text-xs text-stone-400">
          Runtime grew 1.9× — volume grew 2.6×. Sub-linear scaling.
        </p>
      </div>

      <div className="mt-5 space-y-4 leading-[1.75] text-[#3a3830]">
        <p>
          Runtime grew 1.9×. Player volume grew 2.6×. The runtime scaling was
          sub-linear relative to data growth. That is a healthy system.
        </p>
        <p>
          Domestic cup competitions were the main driver of volume growth —
          lower-division squads introduce significant additional player records
          that do not appear in top-flight league data. Without the earlier
          runtime benchmark, this would have looked like a platform problem.
          It was the opposite.
        </p>
        <blockquote className="border-l-4 border-[#b8f046] pl-4 italic text-[#3a3830]">
          Benchmarks are not optional. Without a baseline, a healthy system and
          a broken one produce the same initial reaction: why is this slow? The
          number that matters is not the absolute runtime — it is whether growth
          is linear, sub-linear, or exponential relative to the data being
          processed.
        </blockquote>
      </div>
    </section>
  );
}
