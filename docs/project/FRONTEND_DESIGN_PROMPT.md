# Outreach -- Frontend Design Prompt

## The Problem

Mental health need across London is deeply unequal, but invisible. The data that reveals this inequality -- prescribing rates, deprivation scores, disability rates, service locations -- sits fragmented across a dozen government sources, each with its own format, geography, and vintage. No single tool lets a researcher, council officer, or community organiser see the full picture for a neighbourhood.

**Outreach** makes that picture visible. It is an interactive geospatial tool that assembles 120 indicators across 4,994 London neighbourhoods (LSOAs) into a single, explorable dataset -- linking mental health need (SAMHI), socioeconomic deprivation (IMD), health and disability (Census), and community service accessibility into one view.

The audience is **not** data scientists. It is:
- Local authority public health teams deciding where to place a new talking therapy service
- Mental health researchers exploring the spatial relationship between deprivation and prescribing rates
- Charity programme managers identifying underserved neighbourhoods for outreach
- Lived experience experts examining whether the data matches what they see in their communities
- Policymakers preparing evidence briefs for council meetings

The tool must be legible to someone who has never used a GIS tool, while being rigorous enough that a researcher trusts the data behind it.

---

## Design Identity

### Name and Positioning
**Outreach** -- a tool for seeing what's hidden in plain sight. Not a dashboard. Not a platform. A lens.

The name evokes both the act of reaching out (community outreach, mental health outreach) and the act of extending vision (seeing further than the raw data allows). The product should feel like opening a well-designed report, not logging into a SaaS tool.

### Visual DNA

Draw from the design language of organisations like:
- **London Community Foundation** (londoncf.org.uk) -- warm, generous, human
- **Public health publications** -- editorial rigour with visual confidence
- **The Guardian's data journalism** -- narrative-driven, map-forward, explanatory
- **Our World in Data** -- clear, unhurried, deeply informative

Avoid the aesthetics of:
- Corporate BI dashboards (Tableau, Power BI default skins)
- Dark-mode data terminals
- Startup landing pages with gradients and blob shapes
- Clinical/medical interfaces

### Emotional Register

The content is serious -- we're mapping mental health suffering. The design should be:
- **Respectful**: This is about real communities. No gamification, no "scores" presented like leaderboards.
- **Warm but sober**: Approachable without being cheerful. The data can be grim; the presentation should not flinch from that, but it should not be alarmist either.
- **Authoritative**: Every number has provenance. The design should communicate: "you can trust this."
- **Inviting**: A council officer with 15 minutes should feel confident clicking around, not intimidated.

---

## Colour System

### Primary Palette -- Teal

| Token | Hex | Usage |
|---|---|---|
| `teal-900` | `#0a3d3d` | Headlines, hero text |
| `teal-800` | `#0d5252` | KPI values, active states |
| `teal-700` | `#107070` | Primary buttons, links |
| `teal-500` | `#17a2a2` | Map accents, interactive elements |
| `teal-200` | `#a8e6e6` | Hover highlights, light fills |
| `teal-50` | `#eefafa` | Section backgrounds, card tints |

### Warm Neutrals (not grey -- warm)

| Token | Hex | Usage |
|---|---|---|
| `warm-50` | `#faf9f7` | Page background |
| `warm-100` | `#f5f3f0` | Card backgrounds, alternating rows |
| `warm-200` | `#ece9e4` | Borders, dividers |
| `warm-600` | `#78716c` | Secondary text, captions |
| `warm-900` | `#2d2822` | Body text |

### Semantic / Choropleth

For the map's need-level colouring, use a **sequential teal-to-red** ramp -- not traffic-light colours. The gradient should feel continuous, not categorical:

| Level | Hex | Meaning |
|---|---|---|
| Lowest need | `#d4f3f3` | Light teal |
| Low-moderate | `#6dd3d3` | Medium teal |
| Moderate | `#f5c542` | Warm amber |
| High | `#e87040` | Deep orange |
| Highest need | `#b91c1c` | Dark red |

Use this ramp for SAMHI, antidepressant rate, bad health %, disability %, and IMD score layers. The user should intuitively read "darker/warmer = more need" across all layers.

### What Colour Is Not

- Colour is not decoration. Every colour application should encode information or indicate interactivity.
- No gradients for aesthetics. No coloured backgrounds on cards unless the colour means something.
- The map is the hero colour element. The surrounding UI should be near-monochrome (warm neutrals + teal accents only) so the map's choropleth reads clearly.

---

## Typography

### Font Pairing

| Role | Font | Weight | Usage |
|---|---|---|---|
| Headlines, KPIs, pull-quotes | **Source Serif 4** | 300, 600, 700 | Page title, section headers, large numbers, narrative titles |
| Body text, UI labels, controls | **DM Sans** | 400, 500, 600 | Paragraphs, sidebar data, buttons, form elements, tooltips |

### Scale

| Element | Size | Font | Weight |
|---|---|---|---|
| Page title | `clamp(2rem, 5vw, 3.5rem)` | Source Serif 4 | 700 |
| Subtitle / Tagline | `clamp(1rem, 2vw, 1.25rem)` | Source Serif 4 | 300 italic |
| Section heading | `1.5rem` | Source Serif 4 | 600 |
| Narrative body | `1rem` / `1.6 line-height` | DM Sans | 400 |
| KPI value | `clamp(1.8rem, 4vw, 2.8rem)` | Source Serif 4 | 700 |
| KPI label | `0.75rem` uppercase | DM Sans | 500 |
| Control labels | `0.7rem` uppercase | DM Sans | 600 |
| Data values (sidebar) | `0.85rem` | DM Sans | 500 |
| Map tooltips | `0.8rem` | DM Sans | 400 |

### Typography Rules
- Serif for anything editorial: headlines, narrative paragraphs, large numbers.
- Sans for anything functional: buttons, dropdowns, table cells, map controls.
- Never use more than 2 weights of the same font in a single component.
- `letter-spacing: -0.02em` on large serif headlines. `letter-spacing: 0.06em` on uppercase labels.

---

## Layout and Information Architecture

### Page Structure (scrolling editorial, not fixed dashboard)

The page is a **single vertical scroll** -- like a long-form article with an interactive map embedded in it. This is deliberate: it invites exploration rather than demanding expertise.

```
1. HEADER
   - "Outreach" wordmark
   - Subtitle: "Mapping mental health need across London's neighbourhoods"
   - Meta line: "4,994 neighbourhoods | 120 indicators | Data to 2022"
   - Project branding (small, understated)

2. KPI STRIP
   - 6 headline numbers, edge-to-edge
   - SAMHI mean | Antidepressant rate | Depression prevalence |
     Bad health % | Disability % | Adults in high-need areas

3. NARRATIVE SECTION: "The geography of need"
   - 2-3 paragraphs of editorial narrative (pre-computed insights)
   - Key finding pulled out as a large quote/callout
   - Smooth scroll into the map

4. INTERACTIVE MAP (the centrepiece)
   - Full-width, ~70vh height
   - Choropleth of 4,994 LSOAs
   - Layer selector (SAMHI, antidepressant rate, depression,
     bad health, disability, unpaid care, IMD)
   - Borough filter dropdown
   - Click LSOA → sidebar panel slides in from right

5. NARRATIVE SECTION: "The deprivation-mental health nexus"
   - Scatter plot: SAMHI vs IMD score
   - Correlation narrative
   - Callout: what this means for policy

6. NARRATIVE SECTION: "The pandemic's lasting shadow"
   - Before/after comparison (2019 vs 2022 SAMHI)
   - Borough-level bar chart ranked by COVID deterioration
   - Narrative on structural deepening

7. BOROUGH RANKINGS
   - Horizontal bar chart: mean SAMHI by borough
   - Sortable by different indicators
   - Click borough → filters map to that borough

8. CRITICAL AREAS TABLE
   - Top 20 neighbourhoods by SAMHI need
   - Columns: name, borough, SAMHI, antidepressant rate, depression %, IMD
   - Click row → map zooms to that LSOA

9. METHODOLOGY + DATA SOURCES
   - Collapsible section
   - Brief description of each dataset with provenance
   - Link to full References_and_Research_Data.md
   - "How to cite this tool"

10. FOOTER
    - "Built with open data. Code available on GitHub."
    - "Built with open data. Code available on GitHub."
    - Data last updated date
    - Contact / feedback link
```

### Map Interaction Model

The map is not a separate "page" -- it is embedded in the narrative flow. As the user scrolls past it, it stays visible (sticky positioning) until the next section pushes it out. This creates the feeling of reading a story that hands you a magnifying glass halfway through.

**Map controls** (overlay on the map, top-left):
- Layer selector: dropdown or pill-toggle for the 7 available choropleth layers
- Borough filter: dropdown, "All London" default
- Both controls are minimal, not a "control panel"

**Map interactions**:
- Hover LSOA: subtle highlight + tooltip (name, borough, current layer value)
- Click LSOA: right sidebar slides in with full neighbourhood profile
- Click borough in rankings section: map auto-scrolls into view and zooms

**Sidebar (LSOA detail)**:
- Neighbourhood name + borough
- SAMHI score with decile badge (visual, not just a number)
- Spark indicators: small horizontal bars for each key metric, normalised to London range
- Community services section: nearest service of each type, with distance
- "Compare to London average" contextual framing for every metric
- Close button returns to full map view

### Responsive Behaviour

- **Desktop (1200px+)**: Full editorial layout, map at ~70vh, sidebar overlays map
- **Tablet (768-1199px)**: Slightly compressed, sidebar becomes bottom sheet
- **Mobile (<768px)**: Single column, map at 60vh, narrative sections stack, sidebar becomes full-screen overlay. Borough rankings become a scrollable horizontal strip. Scatter plot simplified or hidden.

---

## Content Tone

### Headlines
Headlines should read like a quality newspaper feature, not a software product:
- "The geography of mental health need" -- not "Mental Health Dashboard"
- "The deprivation-mental health nexus" -- not "Correlation Analysis"
- "The pandemic's lasting shadow" -- not "COVID-19 Impact"
- "Where support falls short" -- not "Service Gap Analysis"

### Narrative Text
Write in the third person. Present tense. Direct. No hedging. No "data suggests" -- say what the data shows:

> *"Across London's 4,994 neighbourhoods, mental health burden is profoundly unequal. The boroughs bearing the heaviest burden -- Barking and Dagenham, Newham, Lewisham -- score significantly above the London mean."*

Not:

> *"Our analysis indicates that there may be significant variation in mental health outcomes across different geographical areas of London."*

### Numbers
- Always contextualise: "24.1 per 1,000" not just "24.1"
- Use comparisons: "2.3x the rate of the least deprived areas"
- Round appropriately: one decimal for rates, whole numbers for populations
- Use comma separators for populations: "423,000 adults"

### Terminology
- "Neighbourhoods" not "LSOAs" (explain LSOA in methodology section only)
- "Mental health need" not "mental health risk" (avoids implying prediction)
- "Deprivation" is fine (it's the official ONS term)
- "People" and "communities" not "data points" or "observations"
- "The data shows" not "the model predicts"

---

## Key Components

### KPI Cards
Edge-to-edge strip beneath the header. 6 cards separated by 1px warm-200 dividers. Each card:
- Large serif number (teal-800)
- Uppercase sans label below (warm-600)
- No icons, no background colours, no borders. Let the numbers breathe.

### Choropleth Map
- Leaflet with OpenStreetMap Carto Light basemap (not satellite, not dark)
- LSOA polygons with 1px white stroke, 0.75 opacity fill
- Sequential colour ramp (teal-to-red) as defined in colour system
- Legend: bottom-left, minimal, showing the continuous ramp with 5 labelled breakpoints
- On hover: polygon stroke thickens to 2px, fill opacity to 0.9
- On click: polygon gets teal-700 stroke, sidebar opens

### Narrative Insight Cards
Each narrative section is a "card" with:
- Serif headline (1.5rem, teal-900)
- 2-3 paragraphs of DM Sans body text (1rem, warm-900)
- One pull-quote or key statistic highlighted: large serif number in teal-800 with a left teal-500 border accent
- Optional accompanying chart (scatter, bar) below the text

### Borough Bar Chart
Horizontal bars, sorted by selected metric (default: SAMHI mean). Each bar:
- Borough name on left (DM Sans, 0.85rem)
- Teal fill bar, proportional to value
- Value label on the right edge of the bar
- Current borough highlighted in teal-700; others in teal-200
- Clicking a bar filters the map

### Scatter Plot
SAMHI (y-axis) vs IMD score (x-axis). Each dot is one LSOA:
- Dot colour: by borough (muted palette) or single teal with opacity
- Size: uniform and small (3-4px radius)
- Trend line: dashed warm-600 with r-value annotation
- Axis labels in DM Sans, tick marks minimal
- Tooltip on hover: neighbourhood name, borough, both values

### Critical Areas Table
Clean, minimal table. No zebra stripes -- use warm-50 background on hover:
- Fixed header, scrollable body
- Columns: Rank, Neighbourhood, Borough, SAMHI (2022), Antidepressant Rate, Depression %, IMD Score
- SAMHI column colour-coded with the sequential ramp
- Row click zooms map to that LSOA

### LSOA Detail Sidebar
Slides in from the right (380px width on desktop). Contains:

```
┌──────────────────────────────────────┐
│ [X close]                            │
│                                      │
│ Hackney 001A                         │
│ Hackney · E01001684                  │
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ SAMHI: 3.21  ·  Decile 10       │ │
│ │ ████████████████████░░ High need │ │
│ └──────────────────────────────────┘ │
│                                      │
│ MENTAL HEALTH                        │
│ Antidepressant rate  ████████░ 34.2  │
│ Depression prev.     ██████░░░ 12.1% │
│ MH hospital rate     █████████ 2.41  │
│ DLA/PIP claims       ████░░░░  4.7%  │
│                                      │
│ HEALTH & DISABILITY                  │
│ Bad/very bad health  ██████░░  8.3%  │
│ Disability rate      ████████░ 19.2% │
│ Unpaid care rate     █████░░░  9.4%  │
│                                      │
│ DEPRIVATION                          │
│ IMD score            ████████░ 42.3  │
│ Income rate          ██████░░  0.21  │
│ Employment rate      █████░░░  0.14  │
│                                      │
│ NEAREST SERVICES                     │
│ Mind branch           1.2 km         │
│ NHS Talking Therapy   0.8 km         │
│ Citizens Advice       1.5 km         │
│ Foodbank              2.1 km         │
│ NHS CMHT              4.3 km         │
│                                      │
│ ── London comparison ──              │
│ This neighbourhood's SAMHI score is  │
│ higher than 98% of London areas.     │
│ Antidepressant prescribing is 1.4x   │
│ the London average.                  │
└──────────────────────────────────────┘
```

Every metric bar is normalised to the London min-max range, so the user sees relative position at a glance. The "London comparison" section at the bottom provides human-readable context.

---

## Accessibility

- All text meets WCAG 2.1 AA contrast ratios (4.5:1 body, 3:1 large text)
- Choropleth colours are distinguishable for the three most common forms of colour vision deficiency (test with Viz Palette)
- Map has keyboard navigation: tab to focus, arrow keys to move, enter to select
- All charts have `aria-label` descriptions summarising the key finding
- Sidebar is keyboard-dismissible (Escape key)
- Font sizes use `clamp()` for fluid scaling -- never below 14px for body text
- Reduced-motion preference respected: disable map fly-to animations, sidebar slide transitions

---

## What This Is Not

- **Not a dashboard**: There is no "admin panel" feel. No grid of widgets. No 12 charts fighting for attention.
- **Not a report PDF**: It is interactive and explorable, not static.
- **Not a data portal**: Users do not download CSVs or run queries. They read, explore, and understand.
- **Not an app**: There is no login, no user accounts, no saved states. It is a public, open tool.

The closest analogy: **an interactive feature article in The Guardian's data journalism section, but built around a map instead of a scrolling timeline.**

---

## Summary: The One-Sentence Brief

Build a warm, editorial, map-centred web tool that lets anyone -- from a council officer to a charity director to a lived experience expert -- explore the geography of mental health need across London, neighbourhood by neighbourhood, with the trust that comes from rigorous, transparent data and the accessibility that comes from clear, human design.
