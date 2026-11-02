# Dashboard design update

Project: **Mahangu Guard – Smart Agriculture IoT Monitoring and Early Warning System**.

The dashboard uses Bootstrap 5.3.8 for controls, navigation and accessibility helpers, Bootstrap Icons 1.13.1 for navigation/sensor/action icons, and the Manrope variable font for headings, labels and readings. HTML, CSS, JavaScript, icons, fonts and the original SVG field illustration are served locally from `static/`; see `static/vendor/README.md` for upstream sources and licenses.

The updated layout uses a white sidebar with green navigation, a light grey canvas, a sensor snapshot card, a segmented semicircular condition gauge, compact sensor and history cards, a green trend chart, an illustrated field panel and bottom navigation on mobile. The full project name remains in the page and browser title.

All displayed measurements, warnings, sample counts and history come from the existing API. The gauge represents four actual software checks: moisture, temperature, pH and alkalinity; light has no configured warning threshold. Each category is coloured only when its latest recorded value is within demonstration limits. This is not a crop health score, production estimate or agronomic recommendation. Stale and disconnected states remain explicit. No yield, revenue, task or weather numbers were invented to populate the reference layout.

Interactive controls include the chart metric selector, 10/30/60-sample window, history search, expanded history, refresh, CSV export, navigation and expandable system information. The backend MQTT, HTTP and SQLite data contracts remain the same.

Run `python tests/redesign_preview.py` to exercise the layout with 16 intentionally generated `local_demo` readings through HTTP validation and SQLite storage. Browser checks cover rendered values, concurrent warnings, gauge count, history expansion/search, range selection, chart selection, viewport width, stale state and offline retention. Generated screenshots and traces stay in the ignored local `evidence/` directory. Synthetic fixtures do not establish field accuracy.
