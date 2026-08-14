# Worked example — telling a telemetry gap from a detection gap

The two look identical from the alert queue and have completely different owners, costs, and
fixes. Getting this wrong sends a year of budget to the wrong place.

## The observation
Purple executes T1098.001. No alert fires.

## The diagnostic question
> **Was the evidence present in the data?**

| | Evidence present | Evidence absent |
|---|---|---|
| **What it is** | **Detection gap** | **Telemetry gap** |
| Who fixes it | Green — write a detection | Green + Yellow — onboard a source, or emit the event |
| Cost | Days | Weeks to months, plus ingestion cost |
| Artifact | Detection Gap (A6) | Control Gap (A7) — and the detection work is **BLOCKED** |
| Metric | M-3 detection rate | **M-10 telemetry availability** |

## What went in the record
```
logged:  full     <- the directory audit event WAS there, with all required fields
alerted: no_alert
=> DETECTION GAP. Data exists. Green writes DET-0231. Estimated 2 days.
```

Had it read `logged: none`, the correct entry is a **Control Gap** for the missing log source,
and the detection request is marked blocked — because assigning detection work that cannot
succeed is how backlogs fill with items nobody can close.

## The rule
**Never accept a detection gap whose required data source does not exist.** Raise the telemetry
gap first. See [`../ARTIFACTS.md`](../ARTIFACTS.md) A6, and the M-10 caveat rule in
[§8](../../00-shared/07_metrics.md): any coverage claim made during a period when a critical
source was below 95% availability carries that caveat on the same slide as the number.
