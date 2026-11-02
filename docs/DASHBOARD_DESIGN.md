# Dashboard design update

Project: **Mahangu Guard – Smart Agriculture IoT Monitoring and Early Warning System**.

The project owner requested a dashboard similar to an attached agriculture UI reference, explicitly asking that the reference image itself not be used. The implementation uses independent HTML, CSS, JavaScript and a new original SVG field illustration. The attached JPG is not copied into the project or loaded by the dashboard.

The updated layout uses a white sidebar with green navigation, a light grey canvas, a sensor snapshot card, a segmented semicircular condition gauge, compact sensor and history cards, a green trend chart, an illustrated field panel and bottom navigation on mobile. The full project name remains in the page and browser title.

All displayed measurements, warnings, sample counts and history come from the existing API. The gauge represents four actual software checks: moisture, temperature, pH and alkalinity; light has no configured warning threshold. Each category is coloured only when its latest recorded value is within demonstration limits. This is not a crop health score, production estimate or agronomic recommendation. Stale and disconnected states remain explicit. No yield, revenue, task or weather numbers were invented to populate the reference layout.

Interactive controls include the chart metric selector, 10/30/60-sample window, history search, expanded history, refresh, CSV export, navigation and expandable system information. The backend MQTT, HTTP and SQLite data contracts remain the same.

Browser validation and desktop/mobile screenshots are in `evidence/07_iterations/dashboard_redesign/`. The screenshots use a separately stored fixture of 16 intentionally generated `local_demo` readings sent through real HTTP validation and SQLite storage. They demonstrate UI behaviour and are not Wokwi or field-measurement evidence. Tests verify actual rendered values, concurrent warnings, gauge count, history expansion/search, range selection, chart selection, viewport width, stale state and offline retention. This is a project-owner-requested design iteration, not a claim of a formal participant study.
