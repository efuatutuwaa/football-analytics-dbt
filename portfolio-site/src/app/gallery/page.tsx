"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

type Screenshot = {
  src: string;
  alt: string;
};

type Group = {
  heading: string;
  description: string;
  images: Screenshot[];
};

const GROUPS: Group[] = [
  {
    heading: "League & Player Stats",
    description:
      "Club standings and player leaderboards across the big-five domestic leagues.",
    images: [
      {
        src: "/dashboards/club_season_epl.png",
        alt: "Premier League 2025 — colour-coded league table showing Champions League, Europa, Conference League and relegation zones",
      },
      {
        src: "/dashboards/club_season_laliga.png",
        alt: "La Liga 2025 — colour-coded league table",
      },
      { src: "/dashboards/player_season_goals.png", alt: "Player season — goals chart" },
      { src: "/dashboards/player_season_assists.png", alt: "Player season — assists chart" },
      { src: "/dashboards/player_season_leaderboard_goals.png", alt: "Player season — goals leaderboard" },
      { src: "/dashboards/player_season_leaderboard_assists.png", alt: "Player season — assists leaderboard" },
    ],
  },
  {
    heading: "Transfer Market",
    description:
      "Permanent fee movements, club spending, and squad valuation across 15 competitions.",
    images: [
      { src: "/dashboards/transfers_leagues.png", alt: "Transfers — league spending overview" },
      { src: "/dashboards/transfers_club_spending.png", alt: "Transfers — club spending trend" },
      { src: "/dashboards/transfer_club_signings.png", alt: "Transfers — club signings table" },
      { src: "/dashboards/transfers_top_fees.png", alt: "Transfers — top transfer fees" },
    ],
  },
  {
    heading: "Honours & Tournaments",
    description:
      "Club trophies, national team podium finishes, and European campaigns.",
    images: [
      {
        src: "/dashboards/club_honors.png",
        alt: "Club honours — trophy cabinet showing league titles, domestic cups and European trophies per club-season with Double and Treble labels",
      },
      { src: "/dashboards/national_team_honors_2024.png", alt: "National team honours — 2024 season" },
      { src: "/dashboards/national_team_honors_history.png", alt: "National team honours — historical podium" },
      { src: "/dashboards/ucl-club-campaign.png", alt: "UCL — club campaign summary" },
      { src: "/dashboards/ucl-top-clubs-by-goals.png", alt: "UCL — top clubs by goals" },
      { src: "/dashboards/cwc_club_campaign.png", alt: "Club World Cup — campaign summary" },
      { src: "/dashboards/cwc-top-clubs-by-goals.png", alt: "Club World Cup — top clubs by goals" },
    ],
  },
  {
    heading: "Squad Valuation",
    description:
      "Estimated squad fee footprint by club and season, with trend analysis.",
    images: [
      { src: "/dashboards/spending_by_club.png", alt: "Squad value — fee footprint by club" },
      {
        src: "/dashboards/Squad_value_premier_league_2024.png",
        alt: "Squad value — Premier League 2024",
      },
    ],
  },
  {
    heading: "Pipeline Observability",
    description:
      "Ingestion health, API quota usage, and run status — ops as a first-class concern.",
    images: [
      { src: "/dashboards/pipeline_health.png", alt: "Pipeline health — donut and heatmap" },
    ],
  },
];

export default function GalleryPage() {
  const [lightbox, setLightbox] = useState<Screenshot | null>(null);

  return (
    <>
      <div className="grain" aria-hidden="true" />

      {/* Lightbox */}
      {lightbox && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={lightbox.alt}
          onClick={() => setLightbox(null)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            background: "rgba(0,0,0,0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "2rem",
            cursor: "zoom-out",
          }}
        >
          <div style={{ position: "relative", maxWidth: "90vw", maxHeight: "90vh" }}>
            <Image
              src={lightbox.src}
              alt={lightbox.alt}
              width={1400}
              height={900}
              style={{
                objectFit: "contain",
                maxWidth: "90vw",
                maxHeight: "90vh",
                borderRadius: "8px",
              }}
              priority
            />
          </div>
        </div>
      )}

      <main
        style={{
          fontFamily: "var(--font-sans)",
          background: "var(--color-off-white)",
          minHeight: "100vh",
          color: "#444",
        }}
      >
        {/* Hero */}
        <div
          style={{
            borderBottom: "1px solid var(--color-border)",
            padding: "4rem 1.5rem 3rem",
          }}
        >
          <div style={{ maxWidth: "760px", margin: "0 auto" }}>
            <Link
              href="/"
              style={{
                fontSize: "0.8rem",
                color: "var(--color-muted)",
                textDecoration: "none",
                letterSpacing: "0.05em",
                textTransform: "uppercase",
              }}
            >
              ← Back
            </Link>

            <h1
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "clamp(2rem, 5vw, 3rem)",
                fontWeight: 400,
                color: "var(--color-charcoal)",
                margin: "1.25rem 0 0.75rem",
                lineHeight: 1.15,
              }}
            >
              Platform Gallery
            </h1>

            <p
              style={{
                fontSize: "1.05rem",
                lineHeight: 1.65,
                color: "#555",
                marginBottom: "0.75rem",
              }}
            >
              A walkthrough of the football analytics platform — 8 pages built on 18
              reporting marts and a Databricks Delta Lake warehouse.
            </p>

            <p
              style={{
                fontSize: "0.8rem",
                color: "var(--color-muted)",
                borderLeft: "3px solid var(--color-border)",
                paddingLeft: "0.75rem",
                marginBottom: "2rem",
              }}
            >
              Screenshots taken from the live application · Premier League · 2025 season
              unless noted
            </p>

            {/* CTAs */}
            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
              <a
                href="https://github.com/efuatutuwaa/football-analytics-dbt"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.35rem",
                  padding: "0.6rem 1.2rem",
                  background: "var(--color-charcoal)",
                  color: "#fff",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  textDecoration: "none",
                  letterSpacing: "0.01em",
                }}
              >
                View Repository ↗
              </a>
              <Link
                href="/"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "0.6rem 1.2rem",
                  border: "1px solid var(--color-border)",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  fontWeight: 500,
                  color: "var(--color-charcoal)",
                  textDecoration: "none",
                  background: "transparent",
                }}
              >
                ← Back to the story
              </Link>
            </div>
          </div>
        </div>

        {/* Groups */}
        <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "3rem 1.5rem 6rem" }}>
          {GROUPS.map((group) => (
            <section key={group.heading} style={{ marginBottom: "4rem" }}>
              <h2
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "1.5rem",
                  fontWeight: 400,
                  color: "var(--color-charcoal)",
                  marginBottom: "0.4rem",
                }}
              >
                {group.heading}
              </h2>
              <p
                style={{
                  fontSize: "0.875rem",
                  color: "var(--color-muted)",
                  marginBottom: "1.5rem",
                  lineHeight: 1.6,
                }}
              >
                {group.description}
              </p>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 480px), 1fr))",
                  gap: "1rem",
                }}
              >
                {group.images.map((img) => (
                  <button
                    key={img.src}
                    onClick={() => setLightbox(img)}
                    title="Click to enlarge"
                    style={{
                      all: "unset",
                      cursor: "zoom-in",
                      display: "block",
                      borderRadius: "8px",
                      overflow: "hidden",
                      border: "1px solid var(--color-border)",
                      background: "#fff",
                      boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
                      transition: "box-shadow 0.2s, transform 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.boxShadow =
                        "0 4px 16px rgba(0,0,0,0.12)";
                      (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.boxShadow =
                        "0 1px 4px rgba(0,0,0,0.06)";
                      (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)";
                    }}
                  >
                    <Image
                      src={img.src}
                      alt={img.alt}
                      width={960}
                      height={600}
                      style={{ width: "100%", height: "auto", display: "block" }}
                    />
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>

        <footer
          style={{
            borderTop: "1px solid var(--color-border)",
            padding: "2.5rem 1.5rem",
            textAlign: "center",
            fontSize: "0.75rem",
            color: "var(--color-muted)",
          }}
        >
          Football Analytics Platform · May 2026
        </footer>
      </main>
    </>
  );
}
