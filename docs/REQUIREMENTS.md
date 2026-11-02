# Initial requirements and acceptance criteria

Project started: 2 November 2026 (Asia/Colombo). Student-authored implementation baseline derived from Document 2 and the Unit 45 brief; not client sign-off.

| ID | Requirement | Acceptance / evidence |
| --- | --- | --- |
| FR1 | Ingest a timestamped sample for a registered device | Authenticated HTTP 201; T01 |
| FR2 | Reject malformed and impossible values | HTTP 400/415/413, no extra database row; T04/T05 and validation tests |
| FR3 | Persist accepted samples | Matching row survives application recreation; T07 |
| FR4 | Show the latest reading | API overview matches accepted ID; T01; matching browser screenshot captured |
| FR5 | Show dry, heat, pH, waterlogging and alkalinity warnings | Correct simultaneous rule output; T02/T03/T08 and boundary tests |
| FR6 | Show sample age and stale/disconnected state | API stale metadata T06; browser clock advance and offline-network checks passed |
| FR7 | Show recent history and export | Chronological endpoint and CSV values match stored records |
| FR8 | Support explicit synthetic mode | Feeder source label local_demo, clear UI source labels |
| FR9 | Represent separate alkalinity and light inputs | Alkalinity mg/L as CaCO₃ and relative light %, both synthetic |
| FR10 | Show upcoming weather context | Availability shown; live integration pending |
| FR11 | Optional MQTT broker-to-backend ingestion | Real public-broker Python test, same timestamp in database and dashboard; MQTT evidence folder |
| FR12 | Wokwi publishes MQTT sensor proxies | User-supplied Serial run matched by exact timestamp/values to SQLite IDs 22–24; broader scenarios and circuit screenshot evidence pending |
| NFR1–2 | Keep tokens outside source and logs | Ignored local token; no token in frontend or request logging |
| NFR3 | Preserve visibility when updates stop | Browser offline check retained last values; simulated elapsed-time stale check passed |
| NFR4 | Readable warning text | Warning title/action and connection text; participant evaluation pending |
| NFR5 | Document API behaviour | README schema, ranges, status codes and tests |
| NFR6 | Distinguish source provenance | local_demo / wokwi_simulation / physical_device; source is self-reported |
| NFR7 | Repeatable Windows tests | Standard-library unittest command, local temporary databases |
| NFR8 | Bound public MQTT demo input and keep the API token local | Exact topic, synthetic sources, range/schema validation, no retained messages, bounded queue and retry tests |

The warning limits are software demonstration rules, not validated crop requirements: moisture <30% or >85%; temperature >38°C; pH <5.5 or >7.5; alkalinity >200 mg/L. No light threshold is asserted. Alkalinity cannot be inferred from pH; salinity is not measured. Agronomic statements in the assignment scenario are not treated as independently validated advice.
