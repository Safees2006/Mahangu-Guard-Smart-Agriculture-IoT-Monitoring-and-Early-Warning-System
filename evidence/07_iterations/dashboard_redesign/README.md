# Dashboard redesign evidence

Requested by the project owner on 2 November 2026. The attached reference was used only to understand visual layout; no pixels from it are included in the dashboard. The field landscape is an independent SVG illustration.

- `redesigned_dashboard_desktop.png`: genuine Edge desktop capture at a 1440×1100 viewport.
- `redesigned_dashboard_mobile.png`: genuine Edge mobile capture at a 390×844 viewport. Fixed bottom navigation appears at the viewport bottom in a full-page screenshot.
- `browser_checks.txt`: actual interactive browser verification results.
- `synthetic_fixture.json`: exact fixture samples and overview response, with a timezone-aware capture timestamp.

The fixture uses a separate database and 16 synthetic `local_demo` samples. It does not modify the operational MQTT database and does not establish Wokwi execution, physical measurements or participant feedback. Screenshots are full-page captures, so their pixel height exceeds the viewport height.
