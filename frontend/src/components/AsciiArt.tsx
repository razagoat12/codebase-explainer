"use client"

// AsciiArt — "minimal", made with the 21st.dev ASCII editor and baked
// to its exact rendered output (looping video + poster). Zero dependencies:
// one <video> that fills its parent. Drop it behind or inside your content:
// <div className="relative h-96"><AsciiArt className="absolute inset-0" /></div>
// Remix the source recipe (styles, animation, palette) in the editor:
// https://21st.dev/community/ascii/editor?from=3d30236a-1639-46d6-a37f-4bd39a231a89
export function AsciiArt({ className }: { className?: string }) {
  return (
    <video
      className={className}
      src={"https://assets.21st.dev/ascii-recipes/videos/user_3GdLUDAN6ieID1Fu8OTL6zl5Al1/92e01a9c-a576-4371-b992-48cec55b97be.mp4"}
      poster={"https://assets.21st.dev/ascii-recipes/thumbnails/user_3GdLUDAN6ieID1Fu8OTL6zl5Al1/a30f332e-8a73-4a79-b394-1dab72ea63b8.webp"}
      autoPlay
      loop
      muted
      playsInline
      aria-label={"minimal — animated ASCII art"}
      style={{
        display: "block",
        width: "100%",
        height: "100%",
        objectFit: "cover",
      }}
    />
  )
}
