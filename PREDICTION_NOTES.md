# Prediction model and measured-error evaluation

## Confirmed pilot

- DC array: **11.4 kWp**; KACO inverter AC rating: **15 kW**.
- User confirmed tilt **30°**, azimuth **180° (south)**.
- Approximate sample coordinates: 35.756256 N, 51.431395 E. Exact plant GPS is still unconfirmed.
- Inverter rating is not substituted for DC array capacity. Aggregate performance ratio is 0.8; it includes conversion, temperature and other aggregate losses. No separate temperature multiplier or inverter clipping model is applied.

Read the supplied presentation, coefficient document, both KACO CSVs and Azar spreadsheet. The original Python engine and original coefficients remain available unchanged; the application uses the versioned physical adapter in `server/plant_model.py`.

## What the supplied sources say

| Observation | Measured energy | Role |
|---|---:|---|
| Gregorian 2025, screenshot | 20,637 kWh | Pilot annual calibration anchor |
| Azar 1404, 2025-11-22 through 2025-12-21 | 892.209 kWh | Pilot winter calibration anchor; overlaps the annual anchor |
| 202608.CSV | 2,052.741 kWh, 31 days | Later evaluation/history |
| 202609.CSV | 1,877.374 kWh, 30 days | Later evaluation/history |
| Shahrivar 1405 extracted from both CSVs, 2026-08-23 through 2026-09-22 | 1,986.523 kWh, 31 days | Calendar-aligned evaluation |

The spreadsheet contains one daily value twice (a semicolon string in column A and the same number in B). Count each day once, divide Wh by 1,000, and exclude the final 892209 total row from the daily sum. The supplied reference snapshot contains the extracted daily readings and hashes of its source files.

Slide 15's “under 8%” is a target/earlier prediction claim, not measured validation. Slide 17 gives 1,774 predicted versus 1,968 actual: 9.858% underprediction using the slide's own denominator. The supplied daily CSVs instead sum to 1,986.523 kWh for Shahrivar, making the same 1,774 estimate 10.698% low. Do not silently substitute one actual total for the other. No monthly measurements were inferred from the screenshot's bar heights.

Specific annual yield is 20,637 / 11.4 = **1,810.263 kWh/kWp/year**, inside the user-supplied Tehran benchmark of 1,700–1,850. That benchmark implies 19,380–21,090 kWh for 11.4 kWp, and 23,800–25,900 kWh for 14 kWp. An annual average is not a constant monthly prediction: seasonal variation remains essential.

## Model and calibration

1. Obtain location-specific daily GHI climatology from NASA POWER; use available Open-Meteo predictions only for the future dates in its horizon.
2. Disaggregate daily GHI into a daylight profile, conserving its daily energy. Use pvlib solar geometry, Erbs decomposition and Hay–Davies transposition to estimate irradiation on the actual tilted plane.
3. Multiply plane-of-array irradiation by **DC** capacity and the aggregate performance ratio. Panel-type efficiency is not multiplied again on top of nameplate kWp. The coefficients document itself notes the legacy geometry factor's weak winter tilt response; retaining its extra panel/temperature multipliers would double-count some assumptions.
4. The default profile remains the physical model. An explicit **Tehran KACO pilot** profile adds a limited empirical seasonal correction. It is not automatically applied to every user/site.
5. For that pilot, fit two coefficients `a + b*w(day)` to the 2025 annual total and Azar total. `w` is a smooth raised-cosine winter bump within 60 days of Azar's centre, zero outside that interval. This local support avoids extrapolating one measured winter month across the entire summer. The profile is an empirical two-aggregate fit, not a uniquely identified physical loss model or a generally validated winter model.
6. Eligible prior history can supply a recent multiplicative bias correction (21+ valid prior days, up to 90 days, freshness gate, bounded factor 0.5–1.5). Its denominator uses the **frozen measured configuration**, not the user's newly changed scenario. Changing capacity, PR or direction therefore retains its physical effect.
7. Annual output is identified as a climate baseline before the recent-history factor. The API separately returns `recent_bias_annual_kwh`; do not confuse a summer-fitted annual extrapolation with independently measured annual accuracy.

The annual and Azar calibration outputs match their inputs by construction. Zero residual on those two fitting aggregates is **not** independent validation. Azar is part of the annual total, not a separate full year. Parameter coefficients are fitted only from those prior anchors; the CSV target month's measured production is never used to fit that month's prediction.

## Reproducible retrospective results

Using the packaged NASA climatology snapshot, corrected site specifications, pilot profile and chronological prior-history correction:

| Test period | Actual kWh | Estimated kWh | Absolute total error | Raw physical model error |
|---|---:|---:|---:|---:|
| August 2026 (no eligible earlier 2026 history) | 2,052.741 | 2,260.880 | 10.140% | 1.182% |
| Shahrivar 1405 (training ends 2026-08-22, 22 days) | 1,986.523 | 2,003.985 | 0.879% | 0.077% |
| September 2026 (training ends 2026-08-31, 31 days) | 1,877.374 | 1,907.607 | 1.610% | 0.409% |

The raw physical model is better on these supplied summer periods. Pilot calibration improves the known annual/winter fitting aggregates and can be useful as a site-specific prior, but must not be presented as a universal improvement. All comparison rows remain visible, including the worse August result. The profile is opt-in, and no coefficients are selected dynamically using target-month error. These are retrospective development tests; an untouched future test set is still needed.

Monthly absolute error = `abs(predicted_total - actual_total) / actual_total * 100`. Signed bias uses the signed numerator. Daily MAE, RMSE and WAPE are also returned because monthly positive/negative daily errors can cancel. Zero-generation days are retained; percent error is null when total actual production is zero, rather than infinity or a fabricated zero. MAPE excludes individual zero denominators and reports their count.

Historical daily NASA data for 2025 and 2026 were also examined during investigation. They are post-event resource data, not archived weather forecasts. They are not substituted into the displayed backtest to claim operational forecast accuracy. Future uncertainty cannot be derived reliably from only these few months.

## Issued forecasts and accounts

The service stores each issued forecast's original daily values, issue time and scenario status in the additive `forecast_runs` table. On later forecast requests it scores stored predictions only when complete actual readings for the entire original target period are available. Pending windows have no error percentage. Hypothetical changed-configuration scenarios are not scored against the old installation as if they were measured outcomes.

`calibration_references` stores each account's measured baseline separately. Saving scenarios retains it once readings exist. The explicit measured-configuration checkbox rebases it. The pilot profile uses the confirmed pilot reference geometry. Production history is still isolated by user and inverter source; incomplete multi-source days are excluded from calibration and full-month validation.

When a user deliberately selects the pilot profile but has no readings, the bundled reference CSV readings are used for the labeled pilot comparison and calibration without importing them into the account. The API exposes `history_source='bundled_pilot_reference'`. These are not invented account readings.

## Use and deployment

In Plant settings, choose **Load confirmed 11.4 kW pilot settings**, then save/generate. The forecast page contains the measured-error panel, raw-model comparison, calibration inputs and saved forecast status. The PDF forecast report includes the latest retrospective comparison. English and Persian formatting share the same values.

Deploy all server Python modules, `server/reference_data/*.json` and the Next.js build. The reference data directory is included in output tracing. Preserve `/data/accounts.sqlite3` and private mail configuration. Existing original Python files were not modified. The installed local USB Android app loads this same UI/backend; the public website still requires deployment. The phone was disconnected during this task, so new on-device UI verification could not run.

Sources: supplied presentation/CSV/XLSX/DOCX and user screenshot/corrections; NASA daily API documentation at https://power.larc.nasa.gov/docs/services/api/temporal/daily/ ; pvlib transposition documentation at https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.get_total_irradiance.html .
