# Policy Assistant: Chatbot UX Fix

---

## The Problem

> [!bug] Raw markdown leaks into the user experience
> While the AI generates its response, users see **unformatted markdown syntax** streaming in real-time: `**bold markers**`, `## headers`, `- bullet dashes`, all rendered as plain text.

**What the user saw during a response:**

```
## Borough Analysis

**Hackney** ranks among the highest-need boroughs in London:

- SAMHI index: 0.87 (decile 9)
- Health deprivation score: 1.12
- Antidepressant rate: 28.4 per 1,000

### Key Drivers

1. **Income deprivation** — ranked 15th most deprived
2. **Barriers to services** — limited GP access
```

That raw text sat on screen for the **entire duration** of the response (5-15 seconds), then snapped into formatted HTML at the very end.

---

## Why It Matters

- **First impression** -- the chatbot is the most interactive part of Outreach. If it looks broken, the whole tool loses credibility.
- **Cognitive load** -- users have to mentally parse markdown syntax instead of reading content. Policymakers aren't developers.
- **Jarring transition** -- the sudden snap from raw text to formatted HTML feels like a glitch, not a feature.

---

## The Fix

> [!success] Thinking indicator with contextual status phrases

Instead of streaming raw text, the chatbot now shows an **animated thinking state** while the AI works:

1. **Typing dots** appear immediately (connection confirmed)
2. **Thinking indicator** takes over with a rotating phrase:
   - *"Analysing borough data"*
   - *"Cross-referencing indicators"*
   - *"Consulting policy frameworks"*
   - *"Mapping neighbourhood patterns"*
   - 10 phrases total, cycling every ~3 seconds
3. **Formatted response** fades in once the full answer is ready -- headers, bold, lists, entity links all rendered cleanly from the start

The phrases are domain-specific to Outreach, so the wait feels purposeful rather than empty.

---

## Before vs After

| | Before | After |
|---|---|---|
| **During generation** | Raw markdown text streaming in | Animated thinking indicator |
| **User perception** | "Is this broken?" | "It's working on my question" |
| **Transition** | Jarring snap to formatted | Smooth fade-in reveal |
| **Markdown rendering** | Only after stream ends | Clean from first appearance |
| **Professional feel** | No | Yes |

---

## Technical Summary

Two files changed:

- **`chat.js`** -- tokens now accumulate silently; thinking indicator rotates phrases via `setInterval`; formatted markdown renders once on completion
- **`chat.css`** -- shimmer animation, phrase fade transitions, dot pulse, reveal animation

No backend changes. No new dependencies. Pure frontend fix.

---

## Demo Script

> Open the Outreach dashboard. Click the chat toggle. Ask: **"Which boroughs should we prioritise?"**
>
> Watch the thinking indicator cycle through phrases while the AI works. When the response appears, note that headers, bold text, bullet lists, and borough links are all formatted from the first frame. Click a borough link to confirm map navigation still works.
