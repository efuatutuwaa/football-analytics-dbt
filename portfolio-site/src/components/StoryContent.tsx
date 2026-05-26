import { loadStory } from "@/lib/story";
import { HeroSection } from "./HeroSection";
import { StorySectionBlock } from "./StoryRenderer";

export function StoryContent() {
  const story = loadStory();

  return (
    <>
      <HeroSection
        title={story.title}
        epigraph={story.epigraph}
        intro={story.intro}
      />
      {story.sections.map((section, index) => (
        <StorySectionBlock
          key={section.id}
          id={section.id}
          title={section.title}
          body={section.body}
          index={index}
          isClosing={section.id === "closing"}
        />
      ))}
    </>
  );
}
