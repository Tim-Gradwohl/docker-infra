TIMOPOLY UI (Reusable Stylesheet)
================================

Files:
  - site/timopoly-ui.css   (shared stylesheet)
  - site/index.html        (landing page consuming the stylesheet)
  - site/services.json     (service list)

How to reuse in other projects:
  1) Copy `timopoly-ui.css` into your web root.
  2) Add this line in your HTML <head>:
       <link rel="stylesheet" href="/timopoly-ui.css" />

  3) Use the same CSS classes:
       .grid .card a.cardlink .top .name .desc .badge .url
     plus header/search helpers:
       .pill .search .subtitle .hint .kbd

Tip:
  - Keep the :root CSS variables; they make it easy to theme per-project.
  - If you want per-app theming, override variables in your app HTML:
       <style>:root{ --max: 1200px; }</style>
