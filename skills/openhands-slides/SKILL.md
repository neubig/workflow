---
name: openhands-slides
description: Create branded reveal.js slide presentations with OpenHands styling. Generates self-contained HTML decks with warm beige/amber/dark-brown palette, flowcharts, diagram components, and PDF export.
triggers:
- create slides
- make a presentation
- slide deck
- presentation
- slides
---

# OpenHands Slides

Create polished reveal.js slide decks with OpenHands branding. Produces a single self-contained HTML file that can be served locally, opened in a browser, or exported to PDF.

## Quick Start

1. Create `index.html` using the template below
2. Serve it: `python3 -m http.server 12000`
3. Customize slides using the component library

## Branding & Palette

Use exactly these CSS variables — do not introduce extra colors:

| Variable | Hex | Usage |
|----------|-----|-------|
| `--oh-bg` | `#F9F0D9` | Warm beige slide background |
| `--oh-dark` | `#22150D` | Headings, primary boxes |
| `--oh-brown` | `#3D2B1F` | Secondary boxes, body text |
| `--oh-amber` | `#FFAB40` | Highlights, badges, accents |
| `--oh-amber-light` | `#FFD59E` | Label text on dark backgrounds |
| `--oh-gray` | `#595959` | Muted text, arrows, subtitles |
| `--oh-light` | `#EEEEEE` | Light cards, secondary backgrounds |

**Logo**: Use the OpenHands color logo (`openhands_logo_color_forwhite.png`) — yellow hands on transparent background, designed for light backgrounds. Do **not** apply CSS filters. The logo should be placed:
- Title slide: top-left at `height: 44px`
- Content slides: bottom-left footer at `height: 22px; opacity: 0.35`
- End slide: centered at `height: 52px`

If no logo file is available, omit the `<img>` tags rather than using a placeholder.

## Full HTML Template

Copy this template and modify the slide sections. It includes the complete CSS theme and all reusable component classes.

````html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Presentation Title — OpenHands</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/white.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --oh-bg: #F9F0D9;
  --oh-dark: #22150D;
  --oh-brown: #3D2B1F;
  --oh-gray: #595959;
  --oh-amber: #FFAB40;
  --oh-amber-light: #FFD59E;
  --oh-light: #EEEEEE;
}

.reveal {
  font-family: 'Inter', sans-serif;
  font-size: 28px;
  color: var(--oh-dark);
}
.reveal .slides { text-align: left; }
.reveal .slides section {
  padding: 40px 60px;
  box-sizing: border-box;
  height: 100%;
}
.reveal h1, .reveal h2, .reveal h3 {
  font-family: 'Inter', sans-serif;
  font-weight: 700;
  color: var(--oh-dark);
  text-transform: none;
  letter-spacing: -0.02em;
}
.reveal h1 { font-size: 2.4em; line-height: 1.1; }
.reveal h2 { font-size: 1.6em; margin-bottom: 0.6em; }
.reveal h3 { font-size: 1.2em; color: var(--oh-gray); font-weight: 600; }
.reveal p  { line-height: 1.6; color: var(--oh-brown); }

/* ── Title slide ── */
.title-slide {
  display: flex !important;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
}
.title-slide .logo    { height: 44px; margin-bottom: 40px; }
.title-slide h1       { margin-bottom: 16px; max-width: 80%; }
.title-slide .subtitle { font-size: 1.1em; color: var(--oh-gray); font-weight: 400; max-width: 70%; line-height: 1.5; }
.title-slide .meta    { margin-top: 40px; font-size: 0.75em; color: var(--oh-gray); font-weight: 500; }

/* ── Content slide ── */
.content-slide {
  display: flex !important;
  flex-direction: column;
  justify-content: flex-start;
  padding-top: 50px !important;
}
.content-slide .slide-header { display: flex; align-items: center; gap: 14px; margin-bottom: 10px; }
.content-slide .slide-header .step-badge {
  background: var(--oh-dark);
  color: var(--oh-amber);
  border-radius: 8px;
  padding: 4px 12px;
  font-size: 0.65em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

/* ── Pipeline (horizontal numbered steps) ── */
.pipeline { display: flex; align-items: center; justify-content: center; gap: 0; margin: 30px 0; flex-wrap: nowrap; }
.pipeline .step {
  background: var(--oh-dark); color: #fff; border-radius: 12px;
  padding: 16px 18px; text-align: center; font-size: 0.65em;
  font-weight: 600; line-height: 1.3; min-width: 120px; max-width: 140px;
}
.pipeline .step .num {
  display: inline-block; background: var(--oh-amber); color: var(--oh-dark);
  border-radius: 50%; width: 24px; height: 24px; line-height: 24px;
  font-size: 0.85em; font-weight: 700; margin-bottom: 6px;
}
.pipeline .arrow { font-size: 1.4em; color: var(--oh-gray); margin: 0 4px; flex-shrink: 0; }

/* ── Flowchart (vertical flow with colored boxes) ── */
.flowchart { display: flex; flex-direction: column; align-items: center; gap: 6px; margin: 16px 0; }
.flowchart .flow-row { display: flex; align-items: center; gap: 14px; width: 100%; justify-content: center; }
.flowchart .flow-box {
  border-radius: 10px; padding: 14px 22px; font-size: 0.75em;
  font-weight: 600; text-align: center; line-height: 1.3; min-width: 160px;
}
.flowchart .flow-arrow { font-size: 1.2em; color: var(--oh-gray); }
.flow-box.dark  { background: var(--oh-dark); color: #fff; }
.flow-box.mid   { background: var(--oh-brown); color: #fff; }
.flow-box.amber { background: var(--oh-amber); color: var(--oh-dark); }
.flow-box.light { background: var(--oh-light); color: var(--oh-dark); }

/* ── Diagram boxes (generic) ── */
.diagram-row { display: flex; align-items: center; justify-content: center; gap: 20px; margin: 20px 0; }
.diagram-box {
  border-radius: 12px; padding: 20px 24px; text-align: center;
  font-weight: 600; font-size: 0.85em; line-height: 1.4;
}
.diagram-box.primary   { background: var(--oh-dark); color: #fff; }
.diagram-box.secondary { background: var(--oh-light); color: var(--oh-dark); }
.diagram-box.highlight { background: var(--oh-amber); color: var(--oh-dark); }
.diagram-box .big-num  { font-size: 2em; font-weight: 700; display: block; line-height: 1; margin-bottom: 4px; }
.diagram-arrow { font-size: 1.6em; color: var(--oh-gray); }

/* ── Criteria cards (2×2 grid) ── */
.criteria-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20px 0; }
.criteria-card { border-radius: 12px; padding: 20px; display: flex; align-items: flex-start; gap: 12px; }
.criteria-card .icon  { font-size: 1.6em; flex-shrink: 0; line-height: 1; }
.criteria-card .label { font-weight: 600; font-size: 0.82em; line-height: 1.4; color: var(--oh-dark); }
.criteria-card .desc  { font-size: 0.7em; color: var(--oh-gray); margin-top: 4px; line-height: 1.4; font-weight: 400; }

/* ── Reference callout ── */
.paper-ref {
  background: var(--oh-light); border-left: 4px solid var(--oh-amber);
  border-radius: 0 10px 10px 0; padding: 16px 20px; margin: 16px 0; font-size: 0.75em;
}
.paper-ref .paper-title   { font-weight: 700; color: var(--oh-dark); margin-bottom: 4px; }
.paper-ref .paper-authors { color: var(--oh-gray); font-weight: 400; }
.paper-ref a { color: var(--oh-brown); text-decoration: underline; text-decoration-color: var(--oh-amber); text-underline-offset: 3px; font-weight: 600; }

/* ── Validation / metric cards ── */
.validation-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }
.validation-card { border-radius: 12px; padding: 24px; text-align: center; }
.validation-card .metric       { font-size: 1.8em; font-weight: 700; line-height: 1; margin-bottom: 8px; }
.validation-card .metric-label { font-size: 0.75em; font-weight: 500; line-height: 1.4; }

/* ── Outcome cards (3-col) ── */
.outcome-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin: 20px 0; }
.outcome-card { border-radius: 12px; padding: 20px; text-align: center; }
.outcome-card .o-icon  { font-size: 2em; margin-bottom: 8px; }
.outcome-card .o-label { font-weight: 700; font-size: 0.85em; margin-bottom: 4px; }
.outcome-card .o-desc  { font-size: 0.7em; font-weight: 400; line-height: 1.4; }

/* ── Two-column layout ── */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin: 16px 0; align-items: start; }
.two-col .col { display: flex; flex-direction: column; }

/* ── Footer logo ── */
.slide-footer { position: absolute; bottom: 24px; left: 60px; display: flex; align-items: center; gap: 8px; }
.slide-footer img { height: 22px; opacity: 0.35; }

/* ── End slide ── */
.end-slide {
  display: flex !important; flex-direction: column;
  justify-content: center; align-items: center; text-align: center;
}
.end-slide .logo { height: 52px; margin-bottom: 30px; }
.end-slide h2    { text-align: center; }
</style>
</head>
<body>
<div class="reveal">
<div class="slides">

<!-- ===== SLIDE 1: TITLE ===== -->
<section data-background-color="#F9F0D9" class="title-slide">
  <img src="assets/openhands-logo.png" class="logo" alt="OpenHands">
  <h1>Presentation Title</h1>
  <div class="subtitle">
    A concise description of what this presentation covers
  </div>
  <div class="meta">Prepared for Audience &nbsp;·&nbsp; OpenHands</div>
</section>

<!-- ===== SLIDE 2: PIPELINE / OVERVIEW ===== -->
<section data-background-color="#F9F0D9" class="content-slide">
  <h2>Pipeline Overview</h2>
  <div class="pipeline">
    <div class="step"><div class="num">1</div><br>First Step</div>
    <div class="arrow">→</div>
    <div class="step"><div class="num">2</div><br>Second Step</div>
    <div class="arrow">→</div>
    <div class="step"><div class="num">3</div><br>Third Step</div>
    <div class="arrow">→</div>
    <div class="step"><div class="num">4</div><br>Fourth Step</div>
  </div>

  <div class="diagram-row" style="margin-top:30px;">
    <div class="diagram-box primary" style="min-width:200px;">
      <span class="big-num">~1K</span>
      inputs in
    </div>
    <div class="diagram-arrow">→</div>
    <div class="diagram-box highlight" style="min-width:200px;">
      <span class="big-num">500</span>
      outputs out
    </div>
  </div>

  <div class="slide-footer"><img src="assets/openhands-logo.png" alt=""></div>
</section>

<!-- ===== SLIDE 3: CONTENT WITH CRITERIA CARDS ===== -->
<section data-background-color="#F9F0D9" class="content-slide">
  <div class="slide-header">
    <span class="step-badge">Step 1</span>
    <h2 style="margin:0;">Analysis</h2>
  </div>
  <h3>Key criteria for evaluation</h3>
  <div class="criteria-grid">
    <div class="criteria-card" style="background:var(--oh-light);">
      <div class="icon">📊</div>
      <div><div class="label">Metric A</div><div class="desc">Description of the first metric and what it measures</div></div>
    </div>
    <div class="criteria-card" style="background:var(--oh-light);">
      <div class="icon">🔍</div>
      <div><div class="label">Metric B</div><div class="desc">Description of the second metric and its purpose</div></div>
    </div>
    <div class="criteria-card" style="background:var(--oh-light);">
      <div class="icon">⚡</div>
      <div><div class="label">Metric C</div><div class="desc">Description of the third metric being tracked</div></div>
    </div>
    <div class="criteria-card" style="background:var(--oh-light);">
      <div class="icon">✅</div>
      <div><div class="label">Metric D</div><div class="desc">Description of the fourth metric and why it matters</div></div>
    </div>
  </div>
  <div class="slide-footer"><img src="assets/openhands-logo.png" alt=""></div>
</section>

<!-- ===== SLIDE 4: FLOWCHART ===== -->
<section data-background-color="#F9F0D9" class="content-slide">
  <div class="slide-header">
    <span class="step-badge">Step 2</span>
    <h2 style="margin:0;">Process Flow</h2>
  </div>
  <div class="flowchart">
    <div class="flow-row">
      <div class="flow-box dark">Input Data</div>
      <div class="flow-arrow">→</div>
      <div class="flow-box mid">Processing</div>
      <div class="flow-arrow">→</div>
      <div class="flow-box amber">Output</div>
    </div>
  </div>
  <h3 style="margin-top:20px;">Additional Details</h3>
  <div class="two-col">
    <div class="col">
      <p style="font-size:0.75em;">Left column content describing the first aspect of the process.</p>
    </div>
    <div class="col">
      <p style="font-size:0.75em;">Right column content describing the second aspect of the process.</p>
    </div>
  </div>
  <div class="slide-footer"><img src="assets/openhands-logo.png" alt=""></div>
</section>

<!-- ===== SLIDE 5: REFERENCE CALLOUT + VALIDATION METRICS ===== -->
<section data-background-color="#F9F0D9" class="content-slide">
  <h2>Results</h2>
  <div class="paper-ref">
    <div class="paper-title">"Relevant Paper or Source Title"</div>
    <div class="paper-authors">Author A, Author B &nbsp;·&nbsp; <a href="#">link</a></div>
  </div>
  <div class="validation-grid">
    <div class="validation-card" style="background:var(--oh-dark);color:#fff;">
      <div class="metric" style="color:var(--oh-amber);">95%</div>
      <div class="metric-label" style="color:rgba(255,255,255,0.7);">Accuracy</div>
    </div>
    <div class="validation-card" style="background:var(--oh-light);">
      <div class="metric" style="color:var(--oh-dark);">2.5×</div>
      <div class="metric-label" style="color:var(--oh-gray);">Speedup</div>
    </div>
  </div>
  <div class="slide-footer"><img src="assets/openhands-logo.png" alt=""></div>
</section>

<!-- ===== SLIDE 6: OUTCOME CARDS ===== -->
<section data-background-color="#F9F0D9" class="content-slide">
  <h2>Expected Outcomes</h2>
  <div class="outcome-grid">
    <div class="outcome-card" style="background:var(--oh-dark);color:#fff;">
      <div class="o-icon">🎯</div>
      <div class="o-label" style="color:var(--oh-amber);">Outcome A</div>
      <div class="o-desc" style="color:rgba(255,255,255,0.7);">Description of the first expected outcome</div>
    </div>
    <div class="outcome-card" style="background:var(--oh-brown);color:#fff;">
      <div class="o-icon">📊</div>
      <div class="o-label" style="color:var(--oh-amber-light);">Outcome B</div>
      <div class="o-desc" style="color:rgba(255,255,255,0.7);">Description of the second expected outcome</div>
    </div>
    <div class="outcome-card" style="background:var(--oh-amber);color:var(--oh-dark);">
      <div class="o-icon">⚖️</div>
      <div class="o-label">Outcome C</div>
      <div class="o-desc">Description of the third expected outcome</div>
    </div>
  </div>
  <div class="slide-footer"><img src="assets/openhands-logo.png" alt=""></div>
</section>

<!-- ===== SLIDE 7: END ===== -->
<section data-background-color="#F9F0D9" class="end-slide">
  <img src="assets/openhands-logo.png" class="logo" alt="OpenHands">
  <h2>Thank You</h2>
  <p style="color:var(--oh-gray);font-size:0.85em;text-align:center;">
    Questions & Discussion
  </p>
  <div style="margin-top:30px;font-size:0.7em;color:var(--oh-gray);">
    openhands.ai &nbsp;·&nbsp; github.com/OpenHands/OpenHands
  </div>
</section>

</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
<script>
Reveal.initialize({
  hash: true,
  controls: true,
  progress: true,
  center: false,
  transition: 'none',
  width: 1280,
  height: 720,
  margin: 0,
});
</script>
</body>
</html>
````

## Component Reference

### Pipeline (numbered horizontal steps)
```html
<div class="pipeline">
  <div class="step"><div class="num">1</div><br>Step Name</div>
  <div class="arrow">→</div>
  <div class="step"><div class="num">2</div><br>Step Name</div>
</div>
```

### Flowchart (colored boxes with arrows)
```html
<div class="flowchart">
  <div class="flow-row">
    <div class="flow-box dark">Input</div>
    <div class="flow-arrow">→</div>
    <div class="flow-box amber">Output</div>
  </div>
</div>
```
Box variants: `dark`, `mid`, `amber`, `light`

### Criteria Cards (2×2 grid with icons)
```html
<div class="criteria-grid">
  <div class="criteria-card" style="background:var(--oh-light);">
    <div class="icon">📊</div>
    <div>
      <div class="label">Title</div>
      <div class="desc">Description text</div>
    </div>
  </div>
  <!-- repeat for each card -->
</div>
```

### Metric Cards (validation results)
```html
<div class="validation-grid">
  <div class="validation-card" style="background:var(--oh-dark);color:#fff;">
    <div class="metric" style="color:var(--oh-amber);">95%</div>
    <div class="metric-label" style="color:rgba(255,255,255,0.7);">Label</div>
  </div>
</div>
```

### Outcome Cards (3-column)
```html
<div class="outcome-grid">
  <div class="outcome-card" style="background:var(--oh-dark);color:#fff;">
    <div class="o-icon">🎯</div>
    <div class="o-label" style="color:var(--oh-amber);">Title</div>
    <div class="o-desc" style="color:rgba(255,255,255,0.7);">Description</div>
  </div>
</div>
```

### Reference Callout
```html
<div class="paper-ref">
  <div class="paper-title">"Paper Title"</div>
  <div class="paper-authors">Authors &middot; <a href="#">link</a></div>
</div>
```

### Two-Column Layout
```html
<div class="two-col">
  <div class="col">Left content</div>
  <div class="col">Right content</div>
</div>
```

### Step Badge (section label)
```html
<div class="slide-header">
  <span class="step-badge">Step 1</span>
  <h2 style="margin:0;">Section Title</h2>
</div>
```

### Big Number Diagram
```html
<div class="diagram-row">
  <div class="diagram-box primary"><span class="big-num">~100K</span>items in</div>
  <div class="diagram-arrow">→</div>
  <div class="diagram-box highlight"><span class="big-num">50K</span>items out</div>
</div>
```

## PDF Export

Install Playwright and a color emoji font, then export using `?print-pdf`:

```bash
pip install playwright && python3 -m playwright install chromium
sudo apt-get install -y fonts-noto-color-emoji  # for emoji rendering
```

```python
import asyncio
from playwright.async_api import async_playwright

async def export_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('http://localhost:12000/?print-pdf', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        await page.pdf(
            path='presentation.pdf',
            width='1280px',
            height='720px',
            print_background=True,
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
        )
        await browser.close()

asyncio.run(export_pdf())
```

This produces one page per slide with backgrounds and emojis intact.

## Downloadable Zip

Bundle the presentation for sharing:

```python
import zipfile, os
with zipfile.ZipFile('presentation.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('index.html')
    zf.write('presentation.pdf')
    for f in os.listdir('assets'):
        zf.write(os.path.join('assets', f))
```

## Design Guidelines

- **Minimal palette**: Stay within the 4 core colors (dark, brown, amber, beige) plus gray and light neutrals. Do not add new accent colors.
- **Left-aligned text**: Body content is left-aligned; only end slides and diagram elements are centered.
- **Consistent slide structure**: Every content slide gets `data-background-color="#F9F0D9"` and `class="content-slide"`.
- **Footer on every content slide**: Add the logo footer to all slides except title and end.
- **No transitions**: Use `transition: 'none'` for a clean, professional feel.
- **Font**: Inter only — loaded from Google Fonts CDN.
