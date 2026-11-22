---
name: design-md-library
description: Library of 84 ready-made DESIGN.md design-system analyses of real websites (Apple, Stripe, Linear, Vercel, Airbnb, Notion, Tesla, Nike, Spotify, Supabase, x.ai and more) with colors, typography, spacing, components and rules. Use when the user wants a page or UI to look like, or be inspired by, a named brand/site, wants to pick a visual direction or design reference, or needs a DESIGN.md for the project.
---

# DESIGN.md library

Source: VoltAgent/awesome-design-md (MIT, see `LICENSE`), commit `fcc7028`. Each file under
`designs/<site>/DESIGN.md` is a plain-markdown design system (Google Stitch DESIGN.md format):
visual theme, color tokens, typography, spacing, components, do/don't rules.

## How to use

1. Open `INDEX.md` in this folder to find the site(s) that match the request (one-line summary each).
   Do not read every DESIGN.md; read only the one(s) chosen.
2. If the user named a site, use `designs/<site>/DESIGN.md` directly. If no exact match exists,
   say so and offer the closest entries from `INDEX.md`.
3. Apply it:
   - **Build/restyle UI**: follow its tokens (colors, fonts, radii, spacing, shadows) and rules
     exactly; map them to the project's styling system (CSS variables, Tailwind theme, etc.).
   - **Set the project's design system**: copy the file to the project root as `DESIGN.md` only
     when the user asks, then adapt brand-specific names to the user's brand.
4. These are analyses "inspired by" real brands. Use them for visual language only: never copy
   the brand's logo, name, trademarks, product imagery or copy into the user's product, and do not
   present output as the real company's site.
5. Fonts named in a file may be proprietary; use the fallback listed in the file or a close free
   alternative (e.g. Google Fonts) and tell the user which substitute was used.
