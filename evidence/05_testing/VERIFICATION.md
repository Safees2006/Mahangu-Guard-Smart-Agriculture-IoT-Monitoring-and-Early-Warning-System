# Actual verification — 2 November 2026

Timezone: Asia/Colombo. Read the adjacent raw logs for exact timestamps and outcomes.

| Check | Actual scope | Evidence |
| --- | --- | --- |
| Automated backend suite | Isolated SQLite databases; ingestion, validation, source, auth, duplicate, boundaries, persistence, freshness, export | automated_tests.txt |
| JavaScript syntax | Node syntax check of static/app.js | Command completed successfully; no syntax errors |
| Wokwi diagram syntax | JSON parse only; not electrical validation or compilation | diagram.json parsed successfully |
| Real HTTP data trace | Synthetic request sent over loopback HTTP; accepted ID/time/values matched the actual SQLite row and overview response | P09_local_http_trace.json |
| Desktop browser | Edge 1440×1100 viewport; rendered 18% moisture and 42°C; two concurrent warnings; source label; chart selector | browser_checks.txt and P09_local_demo_dashboard_desktop.png |
| Mobile browser | Edge 390×844 viewport; document width equals viewport width | browser_checks.txt and P09_local_demo_dashboard_mobile.png |
| Stale UI | Advanced browser Date.now by 30 seconds; checked stale text | browser_checks.txt; this is a controlled clock experiment, not a timed field outage |
| Disconnected UI | Switched the browser network offline; checked disconnected text and retained 18% value | browser_checks.txt; backend-stop experiment not separately performed |

Screenshots show the same isolated local-demo sample as the HTTP trace. No credentials were included. The separate interactive demo database receives its own synthetic normal samples; screenshot IDs need not match that database. The test database is temporary and removed after the run; its captured row is retained in the trace file.

The initial test attempt encountered Windows sandbox access restrictions on temporary databases; tests were actually rerun outside the sandbox. An error in the browser verification script was corrected before its successful rerun. The passing results are from executed checks, not inferred from implementation.

Pending: Wokwi compile/simulation and authenticated delivery, physical sensor calibration, live weather, representative participant feedback, feedback-led iterations and final evaluation. These logs and local screenshots do not establish those outcomes.
