import { StoryContent } from "@/components/StoryContent";
import { Navigation } from "@/components/Navigation";
import { ProgressBar } from "@/components/ProgressBar";

export default function HomePage() {
  return (
    <>
      <ProgressBar />
      <Navigation />
      <main>
        <StoryContent />
      </main>
      <footer className="border-t border-border py-12 text-center text-xs text-muted">
        Football Analytics Platform · May 2026
      </footer>
    </>
  );
}
