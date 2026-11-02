# Initial development and evidence plan

Started 2 November 2026, Asia/Colombo. Owner: student developer. Future dates are provisional and should be updated to your actual availability and assignment deadline.

| Milestone | Target | Initial state |
| --- | --- | --- |
| M1 Requirements, scope and architecture | 2 Nov 2026 | Baseline written; user/client review pending |
| M2 Authenticated API, validation, SQLite | 2 Nov 2026 | Implemented; see actual test log |
| M3 Local dashboard and synthetic feeder | 2 Nov 2026 | Implemented; desktop/mobile browser checks passed, screenshots saved |
| M4 Wokwi transport | 3 Nov 2026 | Wokwi startup and three MQTT samples verified on 2 Nov through user-supplied Serial output and matching SQLite rows; broader warning/outage scenarios pending |
| M5 Consented participant tasks | 4 Nov 2026 | Not conducted |
| M6 Feedback-led changes and retests | 5 Nov 2026 | Awaiting genuine feedback |
| M7 Final evidence and evaluation | 6 Nov 2026 | Not complete; depends on preceding work |

Do not relabel this initial implementation as multiple feedback-led iterations. Record future changes with their actual trigger, date, source revision and retest evidence. No repository commits have been claimed.

| Risk | Likelihood / impact | Mitigation / residual risk |
| --- | --- | --- |
| Synthetic data mistaken for measurements | Medium / high | Source labels and prototype notice; field accuracy remains unknown |
| Simulator cannot reach laptop | High / medium | Private gateway and separate local feeder; Wokwi transport remains unverified |
| Wrong agricultural thresholds | High / high | Demo labels, human verification, no actuation; agronomist review needed |
| Credentials or data exposed | Medium / high | Ignored token, loopback binding, no token logs; remote access controls deferred |
| Stale or out-of-order data | Medium / high | Sample age, stale/disconnected state, sample-time ordering; no offline device queue yet |
| Missing weather service | High / medium | Explicit unavailable status; forecasting not implemented |
| Data loss / storage growth | Medium / medium | Local persistence and CSV export; scheduled backups and retention deferred |

All risks are initially owned by the student developer. Reassess likelihood and impact after experiments; this is a qualitative planning register, not a field safety assessment.
