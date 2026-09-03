# Feature plan: interactive widget gallery

**Status:** proposed
**Depends on:** [#62](https://github.com/pytincture/pytincture_example/pull/62) (store facade and editable UI)

## Goal

Turn this example from one book application into a **fully interactive display of
every dhxpyt widget and the workflow each one is for**. Not a screenshot wall:
each demo is a small working task, backed by the authenticated BFF, that shows
what the widget is *good at* and what it costs to wire up.

The example doubles as the reference implementation the `pytincture-dhxpyt` skill
points at, so every gotcha found while building a demo gets written back into
that skill's reference pages.

## Coverage today

dhxpyt 0.9.18 ships **24 widget packages** and **20 form controls**. The example
currently uses 8 widgets and 3 controls.

| | Covered | Not covered |
|---|---|---|
| **Widgets** (8/24) | layout, toolbar, sidebar, tabbar, grid, form, calendar, window | cardflow, cardpanel, chart, chat, colorpicker, combobox, kanban, listbox, menu, message, pagination, popup, ribbon, slider, timepicker, tree |
| **Form controls** (3/20) | Input, Datepicker, Button | Avatar, Checkbox, CheckboxGroup, Colorpicker, Combo, Container, Fieldset, RadioGroup, Select, SimpleVault, Slider, Spacer, Text, Textarea, Timepicker, Toggle, ToggleGroup |

### Mounting: a gap worth deciding early

`Layout` and `Tabbar` expose `add_*` helpers for 18 widgets. **Six have no
helper**: `colorpicker`, `combobox`, `slider`, `message`, `popup`, `window`.

Three of those are deliberate — `message`, `popup` and `window` are overlays that
own their own DOM and are constructed directly (as `form_window.py` already does
for `Window`). But `colorpicker`, `combobox` and `slider` are ordinary
cell-mountable widgets, and `timepicker` — which is the same shape — *does* have
a helper. That looks like an oversight in the widgetset rather than a design
decision.

**Decision needed in Phase 0:** either add `add_colorpicker`, `add_combobox` and
`add_slider` to `dhx_pytincture_widgetset` (preferred — it makes the widgetset
uniform and the demos honest), or mount those three via `Form` controls and
document the asymmetry. This plan assumes the former; if the helpers do not land,
the three demos in Phase 3 fall back to form controls.

## Shape: a demo registry

One shell, many demos. The current book app's grid, form and calendar work
becomes the Grid, Form and Calendar demos rather than being kept as a separate
front door.

```
example/
  py_ui.py            # shell: chrome + sidebar + content host. No demo logic.
  demos/
    __init__.py       # REGISTRY: ordered list of DemoSpec
    base.py           # Demo base class + DemoSpec
    grid.py
    chart.py
    kanban.py
    ...               # one module per widget
  store*.py           # unchanged from #62
  py_ui_data.py       # gains one BFF method per demo that needs server data
```

### The demo contract

Every demo module exposes one `Demo` subclass:

```python
class Demo:
    slug: str           # sidebar id and smoke-test hook
    title: str          # sidebar label
    widget: str         # dhxpyt module it demonstrates
    blurb: str          # one line: what this widget is for
    use_case: str       # the workflow being shown, in a sentence

    def build(self, cell) -> None:
        """Mount the widget into an existing layout cell. Sync only."""

    async def load(self) -> None:
        """Optional: fill it from the BFF after build() returns."""

    def teardown(self) -> None:
        """Optional: release handlers/proxies when navigating away."""
```

`build()` stays synchronous because the layout cell must exist before the widget
mounts; anything needing the BFF goes in `load()`, which the shell schedules with
`asyncio.ensure_future` after `build()`. This is the split that `#62` had to
discover the hard way for the grid — encoding it in the contract stops every new
demo rediscovering it.

`teardown()` matters more than it looks: `create_proxy` handlers leak across
navigation, and the smoke test's "widgets built exactly once" check will catch it.

### Navigation

The sidebar becomes the gallery index, grouped by what the widget is *for*:

- **Data** — grid, chart, kanban, tree, listbox, cardflow, cardpanel, pagination
- **Chrome** — layout, toolbar, ribbon, menu, sidebar, tabbar
- **Input** — form, combobox, slider, colorpicker, timepicker, calendar
- **Overlay** — window, popup, message, chat

Selecting an item tears down the current demo, clears the content cell, and
builds the new one. Each demo renders its `blurb`/`use_case` in a header strip
above the widget, so the page explains itself without a separate docs pane.

## Data: one catalog, many projections

Everything derives from the existing 69-book seed (padded to 10,000 rows). No new
seeds, no new schema, one store — so every demo genuinely exercises the BFF
instead of rendering a hardcoded fixture.

| Widget | Workflow shown | Derived from |
|---|---|---|
| **grid** | Browse, filter per column, double-click to edit, save | `dataset()` / `update_book()` *(exists)* |
| **pagination** | Page the catalog server-side, 10k rows | `dataset_page()` *(exists)* |
| **chart** | Ratings distribution; pages vs rating scatter | new `rating_histogram()` |
| **tree** | Publisher → author → title drill-down | new `catalog_tree()` |
| **kanban** | Move a book across To read / Reading / Read; the move persists | new `reading_status` column + `set_status()` |
| **listbox** | Authors, multi-select, drives the grid filter | new `authors()` |
| **cardflow** | Catalog as a horizontally flowing card strip | `dataset_page()` |
| **cardpanel** | Book cards with per-card actions | `dataset_page()` |
| **combobox** | Language / publisher picker that filters the catalog | new `distinct_values(field)` |
| **slider** | Minimum-rating filter, live against the grid | client-side over loaded rows |
| **calendar** | Publication dates; picking a date filters the catalog | `publication_date` |
| **timepicker** | "Remind me to read at…" on a per-book reminder | new `reminder` column |
| **colorpicker** | Shelf-label colour per book, persisted | new `shelf_color` column |
| **form** | Full book record edit — the control catalogue *(see Phase 5)* | `get_book()` / `update_book()` |
| **chat** | Reading notes threaded on one book | new `notes` table + `add_note()` |
| **window** | Modal book editor *(exists)* | `update_book()` |
| **popup** | Quick preview anchored to a grid row | loaded rows |
| **message** | Save confirmation / validation failure toasts | client-side |
| **menu**, **ribbon**, **toolbar**, **sidebar**, **tabbar**, **layout** | Three chrome idioms over the same catalog actions | n/a |

`reading_status`, `shelf_color` and `reminder` are three nullable columns on
`books`; `notes` is one new table. Both backends pick them up from
`store_schema.py` without divergence — that is what the shared-schema module in
#62 is for.

## Phases

Each phase is a PR. Phases 1–4 are independent of each other once Phase 0 lands,
so they can be worked in any order or in parallel.

### Phase 0 — groundwork *(blocking)*

- Resolve the missing-`add_*` decision above.
- Add `demos/base.py` (contract) and `demos/__init__.py` (registry).
- Rewrite `py_ui.py` as a shell: chrome, sidebar built from the registry,
  content host, and demo swap with teardown.
- Port the existing grid work to `demos/grid.py` as the reference demo — the one
  every later demo is copied from.
- Extend `ui_smoke.py` with a registry-driven loop: for every demo, navigate to
  it, assert its root widget rendered exactly once, assert no console errors.
  This is the harness that makes Phases 1–4 cheap to verify.

**Done when:** the gallery runs with one demo, and the smoke loop passes over a
registry of one.

### Phase 1 — data widgets

chart, tree, listbox, cardflow, cardpanel, pagination. Adds `rating_histogram()`,
`catalog_tree()`, `authors()` to the BFF.

Highest-risk phase: `PaginationConfig(data=...)` wants a live DHTMLX
`DataCollection`, not a Python list, so the pagination demo has to bind to
another widget's collection. Prove that one first.

### Phase 2 — chrome widgets

menu, ribbon, plus the existing toolbar/sidebar/tabbar/layout formalised as
demos. Shows the same four catalog actions (New, Edit, Export, Refresh) through
three different chrome idioms, which is the actual decision a user of this
library is making.

Watch for the `SeparatorConfig` collision — toolbar, sidebar and ribbon each
define a different class of that name.

### Phase 3 — input widgets

combobox, slider, colorpicker, timepicker, calendar. Adds `distinct_values()`,
`shelf_color` and `reminder` columns. Depends on the Phase 0 mounting decision.

Combo items go in `data`, not `options`.

### Phase 4 — overlay widgets

popup, message, chat. Adds the `notes` table and `add_note()`. `window` is
already covered by the existing modal; it moves into `demos/window.py`.

### Phase 5 — the form control catalogue

One demo covering all 20 form controls, grouped in `Fieldset`s: a book record
edit that uses the *right* control for each field rather than an `Input` for
everything — `Combo` for language, `Slider` for rating, `Toggle` for `in_store`,
`Textarea` for notes, `RadioGroup` for status, `Avatar`/`SimpleVault` for a cover
image. This is where the remaining 17 controls earn their place, and it is the
page most people will actually copy from.

### Phase 6 — documentation

- README section: what the gallery is, how to run it, one line per demo.
- Feed every gotcha found in Phases 0–5 back into
  `pytincture-skill/skills/pytincture-dhxpyt/references/dhxpyt.md`.
- Regenerate the per-widget reference pages against 0.9.18.

## Testing

The registry-driven smoke loop from Phase 0 is the backbone: every demo added to
the registry is automatically navigated to, rendered, and checked for console
errors, with no new test code.

On top of that, each demo that writes to the store gets one **persistence
assertion** in `ui_smoke.py` — perform the workflow, reload, confirm it stuck.
That is the check that separates a real demo from a decorative one, and it is why
the data strategy routes everything through the BFF.

Cost to keep an eye on: the smoke test already takes a Pyodide boot plus ~20
checks. Twenty-four demos in one browser session will be slow. If it gets
painful, split the loop into `--demos data,chrome,...` groups and fan out in CI.

## Risks

| Risk | Mitigation |
|---|---|
| `PaginationConfig` needs a live `DataCollection` | Prove the binding in Phase 1 before designing the rest of that demo |
| Three widgets have no mounting helper | Phase 0 decision; widgetset change preferred over a workaround |
| `create_proxy` handlers leak on navigation | `teardown()` in the contract; the build-once smoke check catches regressions |
| Kanban/chat/cardpanel config shapes are unverified | Each has a nested config family (`KanbanCardConfig`, `ChatMessageConfig`, `CardPanelCardConfig`); read the generated reference page before writing the demo |
| Smoke suite runtime grows past a usable CI slot | Group flag and CI fan-out, if needed |
| Scope: 24 demos is a lot of surface | Phases are independent PRs; the gallery is useful and shippable at any point after Phase 0 |

## Open questions

1. Should the gallery replace `py_ui` as the default application, or be served
   alongside it as a second entrypoint? This plan assumes it replaces it.
2. Do we want a "view source" panel per demo showing the module that built it?
   It would make the gallery self-teaching, at the cost of shipping demo source
   to the browser.
3. Kanban persistence implies a `reading_status` that the grid should probably
   show too. Does that column belong in the main grid demo as well?
