# GreenMine design notes

The supplied four references informed the sage-gray architectural scene, translucent panels, rounded geometry, charcoal surfaces, lime accents and narrow chart bars. Solar panels replace wind turbines to reflect the actual project. The website defaults to Persian, using the supplied Anjoman variable font, with document-level RTL and Radix DirectionProvider. English uses LTR. Language and theme preferences persist on this device; plant settings and readings persist in the authenticated account.

## Interaction research

- Motion React: https://motion.dev/docs/react
- Motion + Radix tabs example: https://motion.dev/examples/react-radix-tabs
- Animate UI tab transitions: https://animate-ui.com/docs/components/radix/tabs
- Radix animation composition: https://www.radix-ui.com/primitives/docs/guides/animation
- Radix accessible tabs: https://www.radix-ui.com/primitives/docs/components/tabs

Custom components adapt these patterns rather than importing an entire visual template. Radix handles keyboard navigation and dialog focus trapping. Motion provides the spring-driven active-tab indicator, viewport reveals and chart entrance. CSS handles short button and dialog transitions. Reduced-motion preferences are respected.

## Generated asset

Built-in image generation produced `public/images/solar-scene.png`. Prompt: premium architectural 3D render of dark graphite photovoltaic arrays on pale concrete plinths, fine silver grid lines, small moss patches and a restrained olive tree; muted sage-gray atmosphere, diffuse sunlight, subtle lime glints, wide composition with negative space for a headline; no text, UI, logos, charts or wind turbines. This is a concept illustration, not a photograph of a pilot plant.

## Source fidelity

Project subject and pilot capacities come from the supplied 30-slide Mehrava Sharbati presentation. Marketing copy does not repeat unsupported market leadership, regulatory approval or precision claims. The landing's 2.88 t figure is explicitly a reported Tir–Mordad pilot result. The dashboard instead totals the actual supplied August and September CSV files: 3,930.115 kWh, giving 2.594 t avoided CO2 under the existing model. These are different reporting periods.

The engine uses 21 kg CO2/tree-year and 0.18 kWh/EV-km. The presentation uses different equivalences in places. Runtime outputs retain the engine's constants. VCT is described as a demo, off-chain accounting unit, never an issued or tradable credit.


## Blue reference revision

The later reference images take priority: desaturated blue atmosphere, rounded almost-white panels, thin orange charts and circular instruments. `public/images/solar-blue.png` was generated with the built-in image tool for this revision. Prompt: premium photorealistic 3D macro view of photovoltaic panels with powder-blue frames and sculptural supports, diagonal grid lines, misty periwinkle atmosphere, cool steel-blue monochrome palette, diffuse studio lighting, tactile satin surfaces, mobile-friendly composition and negative space; no turbine, text, UI, labels or charts.

The data visuals now use Motion for staggered bars, transitioning totals, a performance-ratio arc and an azimuth indicator. Coordinates drive the compass marker directly to avoid SVG transform-origin errors. Gauges are explicitly plant settings. Small text has a 12 px floor, with most labels at 13?16 px. Phone screenshots and instrumentation verification cover both language directions, native settings/dialogs and chart overflow. The source preserves the existing green scene as an unused prior asset.

### Single-column instruments and motion
Dashboard cards now share one full-width column on desktop and Android. Cards scale into place with staggered content and reverse their reveal on tab exit. Orientation and performance markers animate an angle, preserving the circular path; replay controls repeat the animation. Reduced-motion preferences disable spatial motion. The persisted light/dark switch expands from its button using the View Transition API, with a color-veil fallback for older WebViews.
Implementation references: https://motion.dev/docs/react-animate-presence and https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API/Using

Desktop layout correction: at widths of 1024px and above, the original side-by-side solar scene and compact three-column instrument grid are restored. Mobile retains one card per row. Chart bars now trigger on viewport entry so their animation is visible after scrolling. The theme circle transition is slowed to 1.5 seconds.
