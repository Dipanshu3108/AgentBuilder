# HTML visualization

Build standalone, single-file HTML visualizations (graphs, charts, diagrams) that open in any browser with no build step and no server.

## Rules

- One `.html` file. Inline all CSS and JavaScript. No local file references.
- Libraries only from a CDN (`https://cdnjs.cloudflare.com` or `https://cdn.jsdelivr.net`), pinned to an exact version. Good defaults: D3 v7 for force-directed graphs, Chart.js for charts, vis-network for quick node/edge graphs.
- Embed the data as a JSON object in a `<script>` tag so the file is self-contained.
- Responsive: `<meta name="viewport">`, container `width: 100%`, SVG uses `viewBox`.
- Readable defaults: system font stack, 14px minimum text, light background, a legend whenever color encodes meaning.
- Include a short title and a one-line caption describing what the reader is looking at.

## Graph-specific guidance

- Distinct relation types get distinct edge colors and appear in the legend.
- Label edges with the relation name; label nodes with their name.
- The hub node (the one with most edges) should be visually emphasized.
- Allow drag, zoom and pan; show a tooltip on hover with the node's connections.

## Delivery

Save the file with `write_file`, then report the path and a two-sentence description of what the visualization shows.
