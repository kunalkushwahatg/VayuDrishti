# VayuDrishti: An Integrated AI Platform for Urban Air Quality Intelligence
### Implementation Plan

---

## 1. Executive Summary

VayuDrishti ("Vayu" = air, "Drishti" = vision) is a unified, multi-agent AI platform that fuses CAAQMS sensor data, satellite imagery, mobility feeds, meteorological forecasts, and geospatial land-use layers into a single intelligence layer for city administrators. Rather than building five disconnected tools, VayuDrishti implements the five capability areas from the challenge brief — source attribution, hyperlocal forecasting, enforcement prioritisation, multi-city comparison, and citizen advisories — as cooperating agents sitting on one shared data spine, plus **two additional agents (Section 4, Agents 6–7)** that were added not to pad the count but because they fill two real gaps: a genuine reasoning layer where a trained classifier isn't actually possible with available data, and a natural-language interface that makes the whole platform usable in a live demo. This lets each agent's output feed the others (e.g., the forecast feeds the citizen advisory; the attribution engine feeds the enforcement agent), which is where most of the platform's value comes from — the brief explicitly calls out that no existing solution combines attribution + forecasting + enforcement, and that combination is the core differentiator here.

This document is the implementation plan only — architecture, data design, agent logic, tech stack, phased build plan, and evaluation mapping. It does not include the working prototype, deck, or demo video, which are separate deliverables to follow this plan.

**A note on data sources:** every API in Section 6 has been checked (July 2026) to confirm it is (a) free — no-cost tier sufficient for a pilot/hackathon build, (b) currently live and India-covering, and (c) has a working key/registration path. Two genuine gaps exist in India's open-data landscape — real-time traffic feeds and construction-permit/industrial-registry APIs — and Section 6 and Section 10 are explicit about the fallback for each rather than assuming they exist.

**A note on honesty about "AI" here:** not every agent below is a trained machine-learning model, and this plan is deliberately explicit about which is which — see the **Method Type** row in each agent's table in Section 4, and the summary in Section 4.8. Overclaiming "AI" where it's really a rule-based lookup or a plain statistical test is the kind of thing that falls apart under an expert evaluator's questioning, so this plan calls it out upfront instead.

---

## 2. Problem Recap (from brief)

- 24 of India's 50 most polluted cities are Tier 1/2 urban centres; ~1.67M premature deaths/year attributed to air pollution nationally.
- India has 900+ CAAQMS stations, but a 2024 CAG audit found only 31% of cities with monitoring data have any actionable, multi-agency response protocol tied to those readings.
- The gap is not data — it's the intelligence layer: knowing *which source* is responsible *where*, what AQI will be *tomorrow* at ward level, and *where to send inspectors* for maximum impact.

VayuDrishti is designed to close exactly that gap, end-to-end, rather than adding another dashboard.

---

## 3. Solution Architecture

### 3.1 Layered Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 4 — DELIVERY                                                │
│  City Ops Console (+ NL query bar) · Citizen Mobile/Web App ·     │
│  Public Displays · IVR (regional languages)                       │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 3 — ORCHESTRATION (Agent Coordinator)                      │
│  Task routing · shared context store · inter-agent messaging ·    │
│  confidence propagation · human-in-the-loop review queue          │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 2 — AGENT LAYER (7 specialised agents)                     │
│  1. Source Attribution   2. Hyperlocal Forecasting                │
│  3. Enforcement Prioritisation   4. Multi-City Comparison          │
│  5. Citizen Health Advisory   6. Anomaly Investigation (NEW)       │
│  7. Natural-Language Query (NEW)                                   │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 1 — DATA & INGESTION SPINE                                 │
│  CAAQMS (real-time) · Sentinel-5P/MODIS (AOD, fire/thermal) ·     │
│  Open-Meteo forecasts · OSM roads · land-use +                    │
│  cadastral maps · construction permits · industrial stack         │
│  registries · population/vulnerability layers                     │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Why one platform, not five tools

- **Shared spatial index**: all five agents key off the same ward/1km-grid geometry, so outputs overlay without reconciliation.
- **Attribution → Enforcement**: the enforcement agent doesn't just rank hotspots, it ranks them *by attributed source*, so recommendations are evidence-backed rather than generic "AQI is high here."
- **Forecast → Citizen Advisory**: advisories are generated from the 24-72h forecast, not just current readings, so citizens (and hospitals/schools) get advance warning, not a same-day alert.
- **Attribution + Forecast + Enforcement → Multi-City Dashboard**: the comparative layer becomes a "what worked in city A that could work in city B" engine because it has attribution and outcome data to compare, not just AQI numbers.

### 3.3 The Dashboard Is the Product — Agents Are the Engine Behind It

To be explicit: **no one interacts with an "agent" directly.** The five agents in Section 4 are backend intelligence services; what a city official, inspector, or citizen actually opens is one of these interfaces:

**A. City Operations Dashboard** (the primary deliverable — this is what a municipal commissioner or SPCB officer logs into every morning)
- **Map view (default screen)**: city map, ward/1km-grid overlay, colour-coded by current + forecast AQI, click any ward to drill in.
- **Source Attribution panel**: for the selected ward — a source-mix breakdown (vehicular/construction/industrial/burning/dust %) with confidence score, powered by Agent 1.
- **Forecast panel**: 24/48/72h AQI trend line + heatmap toggle for the selected ward, powered by Agent 2.
- **Enforcement Worklist tab**: today's ranked, evidence-backed inspection list (from Agent 3) — each row expandable into the map snippet + source evidence + one-click "mark actioned."
- **Multi-City Comparison tab**: cross-city leaderboard and intervention playbook (Agent 4) — e.g. "Cities with similar source-mix that tried X."
- **Anomaly feed**: a running log of flagged spikes with Agent 6's plain-language investigation notes, so an officer sees *why* something looks off without digging through raw numbers.
- **"Ask VayuDrishti" query bar**: a persistent natural-language input at the top of the dashboard, powered by Agent 7 — type "why is ward 12 bad today?" or "which wards need inspectors most this week?" and get a synthesised, cited answer instead of clicking through tabs. This is also the strongest live-demo moment on the platform.
- **Admin/audit trail**: who actioned what, when — needed for the CAG-style accountability gap the brief calls out.

**B. Citizen-Facing Surface** (mobile app + web + public displays + IVR) — a much simpler, single-purpose view: today's AQI, tomorrow's forecast, a plain-language health advisory in the local language, powered by Agent 5. No source attribution or enforcement detail here — that's for officials only.

**C. Public Display Feed** — the same citizen advisory, formatted for outdoor LED displays at bus stops/metro stations (text-only, high-contrast, auto-refreshing).

So the mapping is: **7 backend agents → 1 primary dashboard (city ops, with an embedded NL query interface) + 1 lightweight citizen surface**, not seven separate screens. Section 8's roadmap prioritises building the core architecture and backend agents first, testing them manually, and only introducing the frontend interfaces in later phases to ensure the intelligence layer is fully robust.

### 3.4 When Computation Actually Happens (this matters for both cost and architecture)

This is a distinction that's easy to get wrong when scoping the build, so it's spelled out explicitly here.

**Almost the entire dashboard is a read, not a computation.** Agents 1, 2, 3, 4, 5, and 6 each run on their own independent schedule (see the cadence table in Section 5.1), and every time they run, they write their output into the database (schema in Section 6.1) — they do not run "on demand" when a person opens a screen. When an official opens the dashboard, selects a city, and clicks a ward, the frontend is simply issuing a database read (via the API endpoints in Section 7.1) against rows that were already computed, sometimes hours earlier. There is no agent execution, no ML inference, and no LLM call involved in rendering the map, the source-mix panel, the forecast chart, or the enforcement worklist. This is what makes the dashboard fast and cheap to run at scale — CAAQMS itself only refreshes hourly, so there is no value in computing anything faster than that.

**Only the "Ask VayuDrishti" query bar (Agent 7) runs live, at the moment a person uses it.** Because a typed question is unpredictable, Agent 7 cannot be precomputed — it has to run an LLM call the instant the question comes in. Critically, this live call is *only* reasoning over already-precomputed numbers sitting in the database (it does not re-run Agent 1's attribution logic or Agent 2's forecast model from scratch) — see Agent 7's pseudocode in Section 4 for the exact loop. In the rare case where a person asks about something that genuinely hasn't been computed yet for that ward (e.g., no anomaly has tripped there), Agent 7 is architected to be able to trigger Agent 6 on demand for that one ward, rather than simply returning "no data" — but this is the exception, not the normal path.

**Practical implication for the build**: the dashboard frontend should be built against a REST API that only ever reads from the database (Section 7.1) — it should never call an ML model, an LLM, or a heavy computation directly. The only endpoint that triggers live agent execution is the one behind the query bar. This separation (dumb, fast frontend reads vs. one live reasoning endpoint) is what keeps the system affordable to run and simple to reason about when debugging.

---

## 4. Agent-by-Agent Design

Each agent below now carries a **Method Type** row — this is the honest classification of what's actually doing the work: a **trained ML model** (needs real training data, which we've checked exists or doesn't), a **rule-based/heuristic system** (domain-knowledge formulas, no training data needed), an **LLM-reasoning agent** (genuine language-model reasoning over evidence, not just formatting), or a **hybrid** of these.

**A note on what's a "tool" vs. a real "agent" here, since the word is used loosely below:** a true agent — the kind with a system prompt, a task, access to tools, and a loop that reasons about what to call next until the task is done — only describes **Agent 7** in this plan (see its pseudocode's reason → act → observe → repeat loop). **Agent 6** is a lighter version: it gathers evidence and reasons once, but doesn't loop back to decide what to fetch next. **Agents 1, 2, 3, 4, and 5 are not agents in that technical sense** — they're scheduled pipelines that run a fixed sequence of steps on a timer and write output to the database (Section 5.1); calling them "agents" is the common looser industry usage (autonomous backend components), not the ReAct-style reasoning loop. Individual functions like `get_attribution(ward)` or `get_forecast(ward)` are **tools** — single-purpose callables with no judgment of their own — and Agent 7 is the orchestrator that calls them in a loop, the same pattern used by Claude when it reasons through a multi-step task.

### Agent 1 — Geospatial Pollution Source Attribution Engine

| | |
|---|---|
| **Objective** | Attribute observed AQI at ward/zone level to source categories (vehicular, construction, industrial, biomass/waste burning, crop residue, dust) with a confidence score. |
| **Method type** | **Rule-based/heuristic system, not a trained classifier.** Honest correction from an earlier draft of this plan: training a classifier that outputs "45% vehicular, 30% construction" requires labeled ground-truth source-apportionment data, and no usable public dataset of that kind exists in India — only a handful of isolated academic studies (IIT Delhi, SAFAR-Pune). So this agent is built as domain-knowledge formulas applied directly to live data, not a model that learns from examples. |
| **Inputs** | CAAQMS pollutant speciation (PM2.5, PM10, NOx, SO2, CO) via **data.gov.in CPCB API**, cross-checked against **OpenAQ API v3**; wind speed/direction from **Open-Meteo**; **Sentinel-5P** NO2/aerosol column via Copernicus Data Space Ecosystem or Google Earth Engine; **NASA FIRMS** fire/thermal-anomaly data; road-network density from **OpenStreetMap Overpass API** as a traffic proxy; land-use category from **ISRO Bhuvan**; construction permit locations (manual — see Section 6 gap note). |
| **How it calculates (step by step)** | **1. Ratio fingerprinting** — each source has a known chemical signature: high NOx:CO ratio → vehicular; high SO2 → industrial; high PM10:PM2.5 ratio → dust/construction; high CO relative to PM2.5 co-located with a FIRMS hotspot → biomass/waste burning. These ratios are computed per station per hour directly from the CAAQMS feed. **2. Wind back-trajectory** — simple advection math (`distance = wind_speed × time`) draws a cone upwind of the station for the past few hours; the agent checks what's sitting in that cone (a FIRMS fire, an industrial stack, a construction site) as a candidate source. **3. Weighted scoring** — the ratio signatures and wind-cone hits are combined into a percentage breakdown per category using a transparent weighted formula (not a black-box model), so every number in the output can be traced back to which input drove it. **4. Confidence score** = a function of how many of the input signals were actually available that hour (satellite may be cloud-blocked, no fires may be nearby) — fewer available signals means a wider, more honest confidence interval, never a false-precision single number. |
| **Output** | Ward-level source-mix breakdown (% per category) + confidence interval, refreshed at CAAQMS reporting cadence (hourly). |
| **Tools** | Python/pandas (feed merging), PostGIS (spatial wind-cone query), plain weighted-scoring logic — deliberately no ML library here, to avoid overclaiming a trained model that the data can't support. |
| **Tie to evaluation** | Benchmarked against the few available CPCB/SAFAR/IIT source-apportionment studies where they exist; everywhere else, the confidence interval is reported honestly as low rather than the system pretending certainty. |

**Pseudocode:**
```
for each station, each hour:
  ratios = compute_ratios(NOx, CO, SO2, PM10, PM2.5)
  wind_cone = build_upwind_cone(station.lat, station.lon, wind_dir, wind_speed, hours_back=3)
  candidates = find_sources_in_cone(wind_cone, firms_hotspots, industrial_sites, construction_sites)
  scores = {}
  scores['vehicular']   = w1 * ratios.nox_co_score + w2 * road_density[ward]
  scores['industrial']  = w3 * ratios.so2_score    + w4 * (1 if 'industrial' in candidates else 0)
  scores['construction']= w5 * ratios.pm10_pm25_score + w6 * (1 if 'construction' in candidates else 0)
  scores['burning']     = w7 * ratios.co_pm25_score + w8 * (1 if 'fire' in candidates else 0)
  scores['dust']        = w9 * ratios.pm10_pm25_score
  normalize(scores)  # so all percentages sum to 100
  confidence = f(num_available_signals, satellite_cloud_cover_flag, wind_data_available)
  write_to_db(ward_id, hour, scores, confidence)
```

### Agent 2 — Hyperlocal Predictive AQI Forecasting Agent

| | |
|---|---|
| **Objective** | 24–72 hour AQI forecast at 1km grid resolution. |
| **Method type** | **Genuinely trained ML model.** This is the one agent where real training data actually exists in sufficient quantity — CPCB's CAAQMS network has multi-year hourly historical data via the API, with matching historical weather from Open-Meteo. |
| **Inputs** | Historical + live CAAQMS (data.gov.in + OpenAQ); **Open-Meteo Forecast + Historical Weather API** for wind, inversion, humidity, precipitation; Open-Meteo's own **Air Quality API** (CAMS-based) as a secondary baseline; seasonal emission calendars (stubble-burning windows from Punjab/Haryana state data + FIRMS fire counts, festival calendar, construction season) built in-house. |
| **How it calculates (step by step)** | **1. Grid interpolation** — station readings are point data; inverse-distance weighting spreads them onto a 1km grid (nearer stations weighted more heavily). **2. Physics layer (Gaussian plume)** — a standard atmospheric dispersion formula estimates downwind plume spread: `C = Q / (2π·σy·σz·u) × exp(-y²/2σy²) × exp(-z²/2σz²)`, where Q is emission rate, u is wind speed, σy/σz are horizontal/vertical spread depending on atmospheric stability class. This gives a physically-grounded baseline that doesn't need training data. **3. ML layer** — a ConvLSTM or Graph Neural Network is trained on sequences of past grid states plus met variables, learning spatio-temporal patterns the physics layer misses (e.g., traffic-hour spikes, festival effects). **4. Ensemble blend** — the physics estimate and ML estimate are combined via a weighted average, with weights tuned per city/season based on which historically performed better. **5. Uncertainty bands** are derived from the ensemble's internal disagreement — wider spread between the two models means wider uncertainty shown to the user. |
| **Output** | Grid-level forecast surface (heatmap) at 24h/48h/72h horizons, with per-grid confidence. |
| **Tools** | PyTorch (ConvLSTM/GNN training), pykrige/numpy (interpolation + plume math), xarray (gridded data handling). |
| **Tie to evaluation** | RMSE reported against a persistence baseline ("tomorrow = today"), per horizon — this is the strongest, most defensible evaluation metric in the whole platform because the data genuinely supports training a real model here. |

**Pseudocode:**
```
# Training (offline, run periodically e.g. weekly as new data accumulates)
X_train = build_sequences(historical_aqi_grid, historical_weather, lookback=72h)
model = ConvLSTM_or_GNN()
model.fit(X_train, y_train)  # y = next 24/48/72h grid values
save_model(model, city_id)

# Inference (run hourly per city)
for each city, each hour:
  grid_now = interpolate_stations_to_grid(latest_caaqms_readings, method='IDW')
  physics_forecast = gaussian_plume(grid_now, wind_forecast, emission_rate_estimate)
  ml_forecast = model.predict(recent_sequence)
  blended = weight_physics * physics_forecast + weight_ml * ml_forecast
  uncertainty = abs(physics_forecast - ml_forecast)  # simple disagreement-based band
  write_to_db(city_id, grid_cell_id, horizon, blended, uncertainty)

# Evaluation (run whenever ground truth for a past forecast becomes available)
rmse_persistence = rmse(actual, yesterday_value)
rmse_model = rmse(actual, blended_forecast)
log_metric(city_id, horizon, rmse_model, rmse_persistence)
```

### Agent 3 — Enforcement Intelligence & Prioritisation Agent

| | |
|---|---|
| **Objective** | Convert attribution + forecast into a ranked, actionable list of enforcement actions. |
| **Method type** | **Hybrid — weighted-scoring optimisation + genuine LLM reasoning.** The scoring is plain math; the write-up is real language-model reasoning, not templating, because it has to construct a coherent justification from a pile of heterogeneous evidence. |
| **Inputs** | Agent 1 output (source attribution + confidence), Agent 2 output (forecast trajectory), registered emission source database, historical compliance/violation records, inspector capacity/availability. |
| **How it calculates (step by step)** | **1. Impact score** = attributed source % × population exposed in that ward (from census) × a multiplier if the forecast trend is worsening. **2. Feasibility score** = inverse of inspector travel distance, adjusted by ease-of-action for that site type and a repeat-offender weighting from violation history. **3. Priority score** = weighted sum: `Priority = w1·Impact + w2·Confidence + w3·Feasibility − w4·TravelTime`, with weights exposed as adjustable parameters an official can tune. **4. Capacity-constrained assignment** — sites are matched to available inspectors as a bipartite assignment problem (solvable via linear programming), so the daily worklist never exceeds real inspector capacity. **5. LLM reasoning step** — for each top-ranked site, an LLM call reads the actual numbers (impact score, source mix, forecast trend, violation history) and constructs the human-readable justification and evidence packet — this is real reasoning because the model has to weigh which facts matter most for that specific case, not fill in a fixed template. |
| **Output** | Ranked daily/weekly enforcement worklist per zone, each item with a written justification + evidence packet (map snippet, source %, forecast trend). |
| **Tools** | Python weighted scoring, PuLP (linear programming for inspector assignment), LLM API call for the write-up. |
| **Tie to evaluation** | Quality rated by domain experts (municipal/pollution-control officers) on relevance, actionability, and evidence sufficiency. |

**Pseudocode:**
```
# Run once daily per city, after Agents 1 and 2 have refreshed
for each ward:
  impact = attribution[ward].pct_by_source * population[ward] * (1.2 if forecast_trend == 'worsening' else 1.0)
  feasibility = 1 / (1 + travel_time(inspector_base, ward)) * ease_of_action[site_type] * repeat_offender_weight[site]
  priority = w1*impact + w2*attribution[ward].confidence + w3*feasibility - w4*travel_time(inspector_base, ward)
  candidate_sites.append({ward, site, priority})

sorted_sites = sort_desc(candidate_sites, key='priority')
assignment = solve_bipartite_assignment(sorted_sites, available_inspectors, capacity_per_inspector)

for each assigned_site in assignment:
  evidence = {
    source_mix: attribution[assigned_site.ward],
    forecast_trend: forecast[assigned_site.ward],
    violation_history: get_violations(assigned_site.site_id)
  }
  justification = llm_call(
    prompt=f"Given this evidence: {evidence}, write a 3-sentence inspection justification citing the specific numbers.")
  write_to_db(assigned_site, priority, justification, evidence)
```

### Agent 4 — Multi-City Comparative Intelligence Dashboard

| | |
|---|---|
| **Objective** | Compare trends, interventions, and compliance across cities to surface transferable lessons. |
| **Method type** | **Hybrid — real statistical method, weak underlying data, partial LLM reasoning.** Being upfront: the statistics (difference-in-differences) are sound, but the method depends on intervention logs (what policy, which city, when) that don't exist as a standing public dataset anywhere — this would have to be manually compiled per pilot city. At hackathon stage, treat this as a small illustrative demo with 1–2 manually entered example interventions, not a live cross-city engine. |
| **Inputs** | Aggregated outputs of Agents 1–2 across onboarded cities, intervention logs (e.g., odd-even, construction bans, industrial shutdowns) with before/after AQI — manually compiled. |
| **How it calculates (step by step)** | **1. Clustering** — cities/wards are grouped by similarity of their source-mix vector (k-means or cosine similarity), so only comparable wards get compared. **2. Difference-in-differences** — for a given intervention: `Effect = (AQI change in intervention wards) − (AQI change in similar wards with no intervention, same period)`, isolating the policy's effect from a citywide trend (like weather) that would've happened anyway. **3. Significance check** — a t-test or bootstrap confidence interval on the effect size, so a random fluctuation doesn't get reported as "this worked." **4. LLM reasoning step (upgraded from pure summarisation)** — rather than just restating the DiD number, the LLM reasons about *whether* an intervention that worked in City A would actually transfer to City B, given City B's different source-mix and constraints — this is a genuine reasoning step, not narration. |
| **Output** | Cross-city leaderboard + "intervention playbook" recommendations, each with a transferability judgment, not just a raw effect size. |
| **Tools** | pandas/scipy (DiD + significance testing), scikit-learn (clustering), LLM call for the transferability reasoning. |
| **Tie to evaluation** | Contributes to the "reduction in signal-to-intervention response time" metric — but given the data gap, this should be framed in the deck as a *projected* methodology with a worked example, not a measured live result. |

**Pseudocode:**
```
# Run whenever a new intervention is manually logged, or weekly as a refresh
clusters = kmeans(source_mix_vectors_by_ward, k=n_clusters)

for each logged_intervention (city, ward, policy, start_date):
  treated_wards = wards_in(city, ward)
  control_wards = same_cluster_as(treated_wards) - treated_wards  # comparable wards, no intervention

  effect = (mean_aqi_change(treated_wards, before=start_date, after=start_date+30d)
            - mean_aqi_change(control_wards, before=start_date, after=start_date+30d))
  ci = bootstrap_confidence_interval(effect, treated_wards, control_wards, n_iter=1000)

  if ci_excludes_zero(ci):
    transferability_note = llm_call(
      prompt=f"Intervention {policy} produced effect {effect} (CI {ci}) in {city}. "
             f"Based on the comparable cities in this cluster, summarize whether this looks transferable and why.")
    write_to_db(policy, city, effect, ci, transferability_note)
  else:
    write_to_db(policy, city, effect, ci, note="not statistically significant, do not recommend")
```

### Agent 5 — Citizen Health Risk Advisory System

| | |
|---|---|
| **Objective** | Ward-level, population-specific health advisories pushed through the channels people actually use. |
| **Method type** | **Rule-based lookup + LLM for translation/localisation only.** Being explicit: this is deliberately *not* framed as deep "AI reasoning" — health guidance should be predictable and traceable to an official standard, not model-generated, so the categorisation step is a plain rule engine. The LLM's only job here is language localisation. |
| **Inputs** | Agent 2 forecast, vulnerability layer (hospitals, schools, elderly population density, outdoor worker concentration from Census of India data), language/locale mapping per city. |
| **How it calculates (step by step)** | **1. AQI-to-health-category mapping** — a direct lookup against CPCB's own published breakpoints (Good/Satisfactory/Moderate/Poor/Very Poor/Severe per pollutant), not invented by the system. **2. Escalation rule** — if a ward has high vulnerable-population density *and* the forecast crosses a severity threshold, the advisory tier escalates (e.g., adds "keep recess indoors" specifically for wards near schools). **3. Template selection + LLM localisation** — a rule engine picks the advisory template for that tier; the LLM's only task is translating and localising it into the regional language (Kannada for Bengaluru, Tamil for Chennai, Bengali for Kolkata) and adjusting register per channel (short for push notification, longer for IVR script, large-font for public display). |
| **Output** | Push notifications, IVR scripts, public display feed, all localised. |
| **Tools** | Simple rule engine/decision table (no ML), LLM API call for translation/localisation only. |
| **Tie to evaluation** | Advisory relevance and language coverage, assessed via user feedback and language QA. |

**Pseudocode:**
```
# Run every time Agent 2 produces a new forecast (hourly)
for each ward:
  category = cpcb_breakpoint_lookup(forecast[ward].aqi_value)  # official table, not invented
  tier = category
  if vulnerability[ward].school_density > threshold and category >= 'Poor':
    tier = escalate(tier, note="school-specific guidance")
  if vulnerability[ward].elderly_density > threshold and category >= 'Moderate':
    tier = escalate(tier, note="elderly-specific guidance")

  template = advisory_templates[tier]  # fixed, pre-approved templates, not LLM-generated content
  for channel in ['push', 'ivr', 'display']:
    for language in city_languages[ward.city]:
      localised = llm_call(
        prompt=f"Translate and adapt this advisory for {channel} in {language}: {template}",
        constraint="do not add new claims, translate and adjust tone/length only")
      write_to_db(ward, channel, language, localised)
```

### Agent 6 — Anomaly Investigation Agent *(new)*

| | |
|---|---|
| **Objective** | When a ward's AQI spikes unexpectedly, investigate *why* using LLM reasoning over the same weak, incomplete evidence a human analyst would have to work with — and in doing so, provide a stronger, more honest substitute for the "trained classifier" that Agent 1 can't actually be. |
| **Method type** | **Genuine LLM-reasoning agent.** This is the strongest case for real "AI brain" work in the whole platform: synthesising multiple incomplete, sometimes-conflicting signals into a plausible explanation is exactly the kind of reasoning task language models are suited for, and exactly the kind of task a rule-based system alone can't do gracefully. |
| **Inputs** | Real-time AQI spike detection from Agent 2's own historical baseline, wind direction (Open-Meteo), nearest FIRMS hotspot + distance/time, time-of-day pattern for that ward, nearby permit data, historical pattern for that specific ward (has this happened before at this time of year?). |
| **How it calculates (step by step)** | **1. Trigger** — a simple statistical rule flags when a ward's AQI deviates more than a set threshold (e.g., 2 standard deviations) from its own rolling baseline for that hour/season. **2. Evidence assembly** — the agent pulls every available contextual signal for that ward at that time: wind vector, nearest fire hotspot and its distance (checked against plume-travel-time math from Agent 2), whether a construction/industrial site is upwind, whether this ward has spiked at this same time in past weeks/years. **3. LLM reasoning** — the model is given this evidence bundle and reasons through it explicitly, e.g.: "Spike at 6am, wind from NW, FIRMS shows a fire 38km NW three hours ago, consistent with plume travel time — likely stubble-burning contribution, moderate confidence, similar pattern seen on 4 of the last 10 mornings this month." This is real reasoning over incomplete evidence, not template-filling. **4. Confidence framing** — the LLM is explicitly instructed to state what it's uncertain about and why, rather than presenting a single confident answer. |
| **Output** | A running anomaly feed on the dashboard: each flagged spike with a plain-language investigation note, cited evidence, and an honest confidence statement. |
| **Tools** | Statistical anomaly detection (rolling z-score, plain code), LLM API call for the investigation reasoning. |
| **Tie to evaluation** | Directly strengthens the "source attribution accuracy" evaluation criterion by being transparent about *why* an attribution is being made, rather than hiding uncertainty behind a single trained-model number the data can't actually support. |

**Pseudocode:**
```
# Triggered automatically whenever Agent 2 writes a new reading, checked every hour
for each ward:
  baseline = rolling_mean_and_stddev(ward_id, same_hour_of_day, past_60_days)
  z_score = (current_aqi[ward] - baseline.mean) / baseline.stddev

  if abs(z_score) > 2:  # threshold, tunable
    evidence = {
      wind: get_wind(ward, now),
      nearest_fire: nearest_firms_hotspot(ward, now, radius_km=100),
      plume_travel_time: distance(nearest_fire, ward) / wind_speed,
      upwind_sites: sites_in_wind_cone(ward, now),
      historical_pattern: past_spikes_at_this_hour(ward, past_365_days)
    }
    note = llm_call(
      prompt=f"A spike was detected: {evidence}. Explain the likely cause, "
             f"state your confidence, and explicitly say what you're uncertain about.")
    write_to_db(ward, timestamp, z_score, note, evidence)
    if severity(z_score) > review_threshold:
      queue_for_human_review(ward, note)
```

### Agent 7 — Natural-Language Query Agent *(new)*

| | |
|---|---|
| **Objective** | Let a city official ask plain-language questions across the whole platform ("why is ward 12 bad today?", "which wards need inspectors most this week?") and get a synthesised, cited answer — instead of clicking through five dashboard tabs. |
| **Method type** | **Genuine LLM-reasoning agent.** This is multi-source synthesis and natural-language interfacing, which is real reasoning work, and it also happens to be the single strongest live-demo moment on the platform. |
| **Inputs** | Live outputs of Agents 1–6 (attribution, forecast, enforcement worklist, city comparisons, advisories, anomaly notes), plus the officer's typed question. |
| **How it calculates (step by step)** | **1. Query parsing** — the LLM identifies which ward(s), time window, and which agent(s)' data the question actually needs (e.g., "why is ward 12 bad" needs Agent 1 + Agent 6's output for ward 12 today). **2. Data retrieval** — the relevant agent outputs are pulled from the shared context store (the same store the Coordinator in Section 5 maintains) rather than the LLM inventing an answer from general knowledge. **3. Synthesis reasoning** — the LLM combines the retrieved, real numbers into a coherent natural-language answer, explicitly citing which agent/data point supports each claim (e.g., "Ward 12's AQI is elevated mainly due to construction dust (Agent 1, 62% confidence) and is forecast to worsen tomorrow due to falling wind speed (Agent 2)"). **4. Guardrail** — if the retrieved data doesn't actually answer the question, the agent says so rather than fabricating a plausible-sounding answer. |
| **Output** | A conversational answer panel in the dashboard, always grounded in and citing the underlying agents' real outputs. |
| **Tools** | LLM API call with retrieval from the shared context store (Section 5) — architecturally this is a retrieval-augmented generation pattern scoped to the platform's own live data, not general web knowledge. |
| **Tie to evaluation** | Doesn't map to one specific brief metric directly, but strengthens the demo quality across all of them — it's the fastest way for an evaluator to see that the attribution, forecast, and enforcement numbers are real and connected, not five separate static screens. |

**Pseudocode:**
```
# Runs live, at the moment a person submits a question — this is the one true agentic loop in the platform
def handle_query(question, city, current_ward=None):
  context = []
  max_iterations = 5

  for i in range(max_iterations):
    # 1. Reason: decide what's needed next given the question and what's been gathered so far
    decision = llm_call(
      prompt=f"Question: {question}. City: {city}. Gathered so far: {context}. "
             f"What single piece of data do you need next, or do you have enough to answer? "
             f"Available tools: get_attribution(ward), get_forecast(ward), get_enforcement_list(city), "
             f"get_anomaly_notes(ward), get_city_comparison(city), trigger_anomaly_check(ward). "
             f"Respond with either a tool call or FINAL_ANSWER.")

    # 2. Act: call the tool the model asked for
    if decision.action == 'FINAL_ANSWER':
      break
    result = call_tool(decision.tool_name, decision.tool_args)  # reads from DB (Section 6.1), no retraining

    # 3. Observe: add the result to context for the next loop iteration
    context.append({tool: decision.tool_name, result: result})

    # 4. Guardrail: if the tool genuinely found nothing, let the model know explicitly
    if result is None:
      context.append({note: "no precomputed data found for this — consider trigger_anomaly_check if relevant"})

  # 5. Final synthesis, grounded only in what was actually retrieved
  answer = llm_call(
    prompt=f"Question: {question}. Evidence gathered: {context}. "
           f"Write a grounded answer citing which data point supports each claim. "
           f"If the evidence doesn't cover the question, say so explicitly rather than guessing.")
  return answer
```

### 4.8 Honest Summary — What's Actually "AI" Here

| Agent | Method type | Needs training data? |
|---|---|---|
| 1. Source Attribution | Rule-based/heuristic | No — by design, since labeled data doesn't exist |
| 2. Forecasting | **Trained ML (real)** | Yes — and yes, sufficient historical data exists |
| 3. Enforcement | Hybrid (scoring + LLM reasoning) | No training needed; LLM call only |
| 4. Multi-City Comparison | Hybrid (statistics + partial LLM reasoning) | No training; but real intervention-log data is thin — treat as illustrative |
| 5. Citizen Advisory | Rule-based + LLM translation only | No |
| 6. Anomaly Investigation | **Genuine LLM reasoning** | No training; this is where the "AI brain" work really lives |
| 7. Natural-Language Query | **Genuine LLM reasoning** | No training; retrieval-augmented reasoning over live platform data |

Only Agent 2 is a genuinely trained deep-learning model. Agents 6 and 7 are where real LLM reasoning does meaningful work beyond formatting or translation. The rest are honest, defensible engineering — rules, statistics, and optimisation — dressed as "agents" because they're autonomous and cooperating, not because they're all neural networks.

---

## 5. Multi-Agent Orchestration

- **Coordinator pattern**: a lightweight orchestrator (not a monolithic chain) routes data to each of the 7 agents, holds a shared spatial-temporal context store (ward ID, grid cell, timestamp as common keys), and manages confidence propagation — e.g., if Agent 1's attribution confidence is low for a ward, Agent 3 down-weights that ward in its enforcement ranking rather than treating it as certain.
- **Shared context store doubles as retrieval source**: this is the same store Agent 7 (Natural-Language Query) queries against — so a question typed into the dashboard is always answered from the platform's own live, real agent outputs, not from the LLM's general knowledge.
- **Anomaly-to-investigation handoff**: Agent 6's z-score check runs on the raw hourly AQI reading itself (Section 4's pseudocode), the same ingestion event that kicks off Agent 1 — when the threshold is crossed, the Coordinator passes the relevant ward's full context bundle (attribution, forecast, nearby fires/sites) to Agent 6 in one call rather than Agent 6 re-fetching raw data itself.
- **Human-in-the-loop checkpoint**: enforcement recommendations and citizen advisories above a severity threshold are queued for a human reviewer (municipal officer / comms lead) before dispatch — important both for accuracy and for public-facing trust.
- **Failure isolation**: each agent degrades independently — e.g., if satellite data is delayed (cloud cover), the attribution agent falls back to ground-sensor-only attribution with a wider confidence interval rather than blocking the whole pipeline.

### 5.1 Run Schedule — Exactly When Each Agent Executes

This is the concrete answer to "how often does each agent actually run":

| Agent | Trigger | Frequency | Runs where |
|---|---|---|---|
| 1. Source Attribution | Scheduled | Every hour, on each new CAAQMS reading | Background batch job |
| 2. Forecasting (inference) | Scheduled | Every hour | Background batch job |
| 2. Forecasting (model retraining) | Scheduled | Weekly (as more historical data accumulates) | Background batch job, offline |
| 3. Enforcement | Scheduled | Once daily (early morning, before the workday) | Background batch job, depends on 1 + 2 |
| 4. Multi-City Comparison | Event-triggered | Whenever a new intervention is manually logged, plus a weekly refresh | Background batch job |
| 5. Citizen Advisory | Scheduled | Every hour, immediately after Agent 2 refreshes | Background batch job, depends on 2 |
| 6. Anomaly Investigation | Event-triggered | Whenever a new hourly AQI reading crosses the z-score threshold for a ward — the same ingestion event that also kicks off Agent 1 | Triggered by the raw-data ingestion event, not on its own separate clock |
| 7. Natural-Language Query | On-demand | The instant a person submits a question | Live, in the request path — the only agent that isn't precomputed |

The practical rule: **everything except Agent 7 is a cron job that writes to the database; Agent 7 is the only endpoint that runs synchronously in response to a person's action.**

---

## 6. Data & Integration Layer — Verified Free APIs (checked July 2026)

| Data Need | Source & Endpoint | Cost / Access | Used By |
|---|---|---|---|
| Real-time ground AQI (CPCB's 900+ CAAQMS stations) | **data.gov.in CPCB Real-Time AQI API** — `api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69` | Free; register on data.gov.in, get API key instantly, works via DigiLocker SSO too | Agents 1, 2 |
| Harmonised/backup ground AQI, historical archive | **OpenAQ API v3** (`api.openaq.org`) — aggregates the same CPCB stations in a standard schema | Free, open, no cost tier | Agents 1, 2 (cross-validation) |
| Atmospheric NO2 / aerosol column (satellite) | **Sentinel-5P** via Copernicus Data Space Ecosystem (raw data, fully free/open) or **Google Earth Engine** (free for research/non-commercial use, much easier to query programmatically) | Free | Agent 1 |
| Fire / thermal anomaly detection (stubble burning, waste burning) | **NASA FIRMS API** (`firms.modaps.eosdis.nasa.gov/api`) — MODIS (1km) + VIIRS (375m), India data within ~3 hrs of overpass | Free; instant self-serve API key, no cost | Agent 1 (source attribution), Agent 2 (seasonal forecasting input) |
| Land cover / land use, urban sprawl | **ISRO Bhuvan Thematic API/WMS** (`bhuvan-app1.nrsc.gov.in`) — India-specific LULC, urban land use layers | Free after registration | Agent 1 |
| Road network (traffic density proxy) | **OpenStreetMap Overpass API** — road class, density, intersections | Free, no key required | Agents 1, 2 (proxy in absence of live traffic feed — see gap note below) |
| Meteorological forecast (wind, inversion, humidity, precipitation) | **Open-Meteo Forecast API** (`api.open-meteo.com/v1/forecast`) — no key, no card, free up to 10,000 calls/day for non-commercial use, blends ECMWF/NOAA/DWD/IMD-adjacent models, up to 1km resolution | Free | Agent 2 |
| Secondary/baseline AQI forecast | **Open-Meteo Air Quality API** (CAMS-based global air quality forecast) | Free | Agent 2 (benchmark comparison) |
| Population / vulnerability layer | **Census of India datasets via data.gov.in** | Free | Agent 5 |
| Construction permits, industrial stack registry, compliance records | No standing national free API exists for these (see gap note) | N/A | Agents 1, 3 |
| Cross-city intervention logs | Municipal/SPCB records — manual onboarding per city pilot | N/A | Agent 4 |

### Honest gap note — two things don't have a free working API today

1. **Live traffic/mobility feeds.** There is no free, India-wide, real-time traffic API — Google Maps' traffic layer and most commercial equivalents are paid. The plan substitutes **OpenStreetMap road-network density** (free) as a structural traffic proxy for the hackathon/pilot stage, with a clearly labelled option to add a paid feed (e.g., TomTom Traffic, which has a limited free-tier of ~2,500 requests/day) once budget allows.
2. **Construction permits & industrial stack registries.** These are held by individual municipal corporations and State Pollution Control Boards, and are largely not digitised or exposed as APIs anywhere in India today. This is a real, structural limitation, not a solvable API-discovery problem — the plan treats it as a **partnership/onboarding task per pilot city** (manual CSV exports from the municipal body), not something to fake with a placeholder API.

### 6.1 Database Schema — What Actually Gets Stored

This is the concrete set of tables the whole platform reads and writes. Everything the dashboard displays comes from these tables, not from live computation (see Section 3.4).

```sql
-- Reference/static tables
cities (city_id, name, state, timezone)
wards (ward_id, city_id, name, geometry, population, boundary_geojson)
stations (station_id, ward_id, name, lat, lon, source ['CPCB','OpenAQ'])
inspectors (inspector_id, city_id, name, base_lat, base_lon, daily_capacity)
emission_sites (site_id, ward_id, type ['industrial','construction'], lat, lon, permit_ref, registered_date)

-- Raw ingested data (from Section 6's APIs, refreshed on their own cadence)
raw_aqi_readings (reading_id, station_id, timestamp, pm25, pm10, no2, so2, co, source)
raw_weather (city_id, timestamp, wind_speed, wind_dir, humidity, precipitation, temp)
raw_fire_hotspots (hotspot_id, lat, lon, timestamp, frp, source ['FIRMS'])
raw_landuse (ward_id, category, pct_coverage, source ['Bhuvan'])

-- Agent 1 output
attribution_results (ward_id, timestamp, pct_vehicular, pct_construction, pct_industrial,
                      pct_burning, pct_dust, confidence_score, signals_available_json)

-- Agent 2 output
forecast_grid (city_id, grid_cell_id, forecast_made_at, horizon_hours, aqi_predicted,
               uncertainty_band, physics_component, ml_component)
forecast_accuracy_log (city_id, horizon_hours, date, rmse_model, rmse_persistence)

-- Agent 3 output
enforcement_worklist (worklist_id, ward_id, site_id, date, priority_score, impact_score,
                       feasibility_score, assigned_inspector_id, justification_text,
                       evidence_json, status ['pending','reviewed','actioned'])

-- Agent 4 output
interventions (intervention_id, city_id, ward_id, policy_name, start_date, logged_by)
intervention_effects (intervention_id, effect_size, confidence_interval_low,
                       confidence_interval_high, transferability_note, target_city_id)

-- Agent 5 output
advisories (advisory_id, ward_id, tier, channel ['push','ivr','display'], language,
            text, generated_at)

-- Agent 6 output
anomalies (anomaly_id, ward_id, timestamp, z_score, investigation_note, evidence_json,
           confidence_statement, human_reviewed boolean)

-- Agent 7 — no persistent output table needed; it reads from all tables above live.
-- Optionally log queries for QA:
query_log (query_id, user_id, question, city_id, final_answer, tools_called_json, timestamp)

-- Audit trail (Section 3.3's admin tab)
audit_log (log_id, user_id, action, target_table, target_id, timestamp)
```

This is a starting schema, not a final one — but it's enough to build against directly: every dashboard panel in Section 3.3 maps to a `SELECT` against exactly one or two of these tables, and every agent in Section 4 maps to an `INSERT`/`UPDATE` against exactly the tables it owns.

---

## 7. Technology Stack (indicative)

| Layer | Suggested Tech |
|---|---|
| Geospatial processing | PostGIS, GDAL, Google Earth Engine (free tier — Sentinel-5P/Sentinel-2 querying) |
| Data ingestion (all free APIs) | Scheduled pullers for data.gov.in CPCB, OpenAQ, NASA FIRMS, Open-Meteo, Bhuvan WMS, OSM Overpass — all no-cost, no-card endpoints suitable for a hackathon or pilot budget |
| Rule-based/heuristic logic (Agents 1, 5) | Plain Python weighted-scoring and decision-table logic — deliberately no ML library here, since the underlying data doesn't support a trained classifier |
| ML/forecasting (Agent 2 only) | PyTorch (ConvLSTM/GNN) — the one agent where real training data justifies a deep-learning model |
| Optimisation (Agent 3) | PuLP or similar linear-programming library for capacity-constrained inspector assignment |
| Statistics (Agent 4) | pandas/scipy (difference-in-differences, significance testing), scikit-learn (clustering) |
| LLM-reasoning agents (3, 4, 5-translation, 6, 7) | LLM API calls, with Agent 7 using a retrieval-augmented pattern against the shared context store rather than free-form generation |
| Orchestration | Multi-agent framework (e.g., LangGraph-style orchestrator) + message queue (Kafka/Redis streams) + shared context store (also serves as Agent 7's retrieval source) |
| Data storage | Time-series DB (TimescaleDB) for sensor data, object store for satellite imagery, PostGIS for vector layers |
| Delivery | Web dashboard (city ops, with embedded NL query bar), mobile push (citizen app), IVR gateway, public display API |

### 7.1 API Contract — What the Dashboard Actually Calls

This is the concrete REST contract between the frontend (Section 3.3) and the backend (Section 4 agents + Section 6.1 database). Every endpoint except the last one is a pure database read — no agent runs when these are called.

```
GET  /api/cities
     → list of onboarded cities

GET  /api/cities/{city_id}/wards
     → ward boundaries + current AQI for map rendering

GET  /api/wards/{ward_id}/attribution?date=today
     → reads attribution_results — powers the source-mix panel

GET  /api/wards/{ward_id}/forecast?horizon=24,48,72
     → reads forecast_grid — powers the forecast chart

GET  /api/cities/{city_id}/enforcement-worklist?date=today
     → reads enforcement_worklist — powers the worklist tab
POST /api/enforcement-worklist/{worklist_id}/mark-actioned
     → writes to enforcement_worklist.status + audit_log (this is a write, needs auth)

GET  /api/cities/{city_id}/comparisons
     → reads intervention_effects — powers the multi-city tab

GET  /api/wards/{ward_id}/anomalies?since=24h
     → reads anomalies — powers the anomaly feed

GET  /api/wards/{ward_id}/advisory?language=kn
     → reads advisories — powers the citizen-facing surface

POST /api/query
     body: { question, city_id, current_ward_id }
     → the ONLY endpoint that runs a live agent (Agent 7's loop, Section 4).
       Everything else above is a plain database read.
```

The important design rule this enforces: **the frontend never needs to know whether an agent "ran recently" — it just reads whatever is in the table.** Freshness is entirely the background scheduler's job (Section 5.1), not something the frontend has to manage or wait on, except for the one `/api/query` endpoint which is synchronous by nature.

### 7.2 UI/UX Design System

The brief is for a government-facing intelligence tool, so the design goal is **calm and trustworthy, not flashy** — an official should be able to read a ward's status in under two seconds. Simple, restrained animation is used only to guide attention (what changed, what's loading), never for decoration.

**Overall theme — "Clear Sky"**
A clean, airy theme built around the idea that the product's whole job is making air quality visible. Generous white space, soft neutral surfaces, and one confident accent color, with the AQI severity scale doing the rest of the color work (since that scale already carries real meaning — it shouldn't compete with a separate brand palette).

**Color palette**
- **Primary/brand accent**: a deep teal (`#0F6E56`-ish) — evokes clean air and trust without being a generic "eco green."
- **Neutral base**: warm off-white background (`#F1EFE8`-ish), charcoal-gray text (`#2C2C2A`-ish) — never pure white/pure black, easier on the eyes for a screen someone stares at all day.
- **AQI severity scale** (this is the one place color carries real, official meaning — use the standard CPCB bands, not a custom scale, so officials read it instantly): Good = green, Satisfactory = light green, Moderate = yellow, Poor = orange, Very Poor = red, Severe = deep maroon.
- **Status colors**: teal for "actioned/resolved," amber for "pending review," soft red for "needs attention" — kept separate from the AQI scale so the two meanings never visually collide.

**Typography**
- One clean, modern sans-serif throughout (e.g., Inter or similar) — no decorative or condensed fonts, this is a data-reading tool.
- Large, confident numerals for AQI values (they're the single most-scanned piece of information on the whole screen) — small, muted labels underneath.
- Sentence case everywhere, generous line height — avoids the cramped, all-caps "enterprise dashboard" look.

**Layout principles**
- **Card-based, not table-heavy.** Wards, worklist items, and anomaly notes are shown as soft-shadowed rounded cards, not dense spreadsheet rows — easier to scan, easier to make touch-friendly for tablet use in the field.
- **The map is the anchor**, always visible on the left/center; detail panels slide in on the right when a ward is selected, rather than navigating to a whole new page — keeps spatial context while drilling into detail.
- **One primary action per screen** — e.g., the worklist's main action is "mark actioned," not buried among five other buttons.
- **Citizen-facing surface is drastically simpler** than the officials' dashboard: one AQI number, one color, one line of advisory text, in large type — no charts, no tabs, no jargon. Designed to be understood at a glance by someone walking past a public display, not studied.

**Simple animations (restrained, purposeful only — nothing decorative)**
- **AQI number count-up**: when a ward's value loads, the number animates from 0 up to its actual value over ~600ms — draws the eye without being distracting, and doubles as a subtle loading indicator.
- **Map color transitions**: when the forecast horizon toggle changes (24h → 48h → 72h), ward colors cross-fade smoothly (~300ms) rather than snapping, so the eye can track which wards are getting better or worse.
- **Panel slide-in**: the ward detail panel slides in from the right (~250ms ease-out) rather than appearing instantly — reinforces "this is detail about the thing you just clicked," not a new page.
- **Anomaly pulse**: a flagged ward gets a slow, subtle pulse (opacity 1 → 0.7 → 1 over ~2s, looping) on the map — enough to draw attention without being alarming or distracting during a long viewing session.
- **Skeleton loading, not spinners**: while a panel's data loads, show a soft gray placeholder shape in the exact layout of the real content, then fade it into the real data — feels faster and less jarring than a spinner.
- **Query bar response**: while Agent 7's loop runs (Section 4), show three small dots animating in sequence (a simple "thinking" indicator) rather than a blank wait — sets honest expectation that this one action takes a moment, unlike everything else on the dashboard which is instant.
- **Reduced-motion respect**: every animation above is wrapped so it's disabled for users with reduced-motion preferences set — this is a public-sector tool and should be accessible by default.

**What to deliberately avoid**: gradients as decoration, drop shadows beyond a subtle card lift, more than one accent color competing with the AQI scale, dense data-grid tables as the primary view, and any animation whose only purpose is to look impressive rather than communicate a state change.

---

## 8. Phased Implementation Roadmap

| Phase | Focus | Key Milestone |
|---|---|---|
| **Phase 1 — Core Architecture & Data Ingestion (Weeks 1-2)** | Stand up the **database schema (Section 6.1)** and the ingestion spine. Connect real data sources (CAAQMS, Sentinel-5P, Open-Meteo, Bhuvan, etc.) and verify data is correctly stored in the tables. No frontend work yet. | DB schema live; ingestion spine actively pulling real data into tables |
| **Phase 2 — Backend Agents & Manual Testing (Weeks 3-6)** | Build and manually test each agent sequentially via script/terminal execution. Build Agent 1 (Attribution) and Agent 2 (Forecasting), verify their logic. Then build Agents 3 (Enforcement), 5 (Advisory), and 6 (Anomaly). Validate outputs directly in the database to ensure backend reasoning works flawlessly before introducing API/UI layers. | All core backend agents functioning and tested manually |
| **Phase 3 — API Layer & Integration (Weeks 7-8)** | Build the **API layer (Section 7.1)** on top of the tested database and agents. Connect Agent 7 (Natural-Language Query) to reason over the validated backend data via the API/context store. Test API endpoints manually (e.g., Postman/curl). | Fully tested API contract returning real, live data; Agent 7 capable of answering queries |
| **Phase 4 — Frontend & Dashboard Delivery (Weeks 9-10)** | Build the **City Ops Dashboard shell (Section 7.2)** and wire it to the live API. Since the backend is already fully tested, this phase focuses purely on UI rendering, responsiveness, and UX. | City Ops Dashboard and citizen-facing surface fully functional and demoable |
| **Phase 5 — Hardening & Cross-City (Weeks 11-12)** | Build Agent 4 (Comparative Dashboard). Conduct confidence calibration, human-in-the-loop review UI, language QA for advisories, and load testing. | Pilot-ready platform across multiple cities |

*(Timeline assumes a small dedicated team moving from hackathon prototype toward a pilot-ready build; compress proportionally for a hackathon-only MVP. For a tight hackathon timeline, the focus should heavily be on Phase 1 & 2 to ensure the core intelligence engine works, with a very basic UI layered on top at the end.)*

---

## 9. Evaluation Focus — How the Plan Addresses Each Criterion

| Brief's Evaluation Criterion | How VayuDrishti Addresses It | Honest strength |
|---|---|---|
| Source attribution accuracy vs. ground-truth inventories | Agent 1's rule-based breakdown validated against the few available CPCB/SAFAR/IIT source apportionment studies; Agent 6 adds transparent, cited reasoning for individual spikes | **Moderate** — honest confidence intervals rather than a trained-model number the data can't support |
| AQI forecast accuracy (RMSE vs. persistence baseline) | Agent 2 reports RMSE at 24/48/72h vs. naive persistence, per grid cell — a genuinely trained model on real historical data | **Strong** — this is the platform's most defensible metric |
| Enforcement recommendation quality (expert-rated) | Agent 3's evidence packets, with LLM-authored justification, are designed for direct expert review | **Strong** — real reasoning over real scoring, demoable end-to-end |
| Citizen advisory relevance & language coverage | Agent 5 explicitly scoped for multi-language (Kannada, Tamil, Bengali, etc.) from day one, using official CPCB breakpoints | **Strong** — low-risk, well-defined scope |
| Reduction in signal-to-intervention response time | Framed via Agent 4's DiD methodology plus Agent 7's NL query cutting an official's time-to-answer directly | **Weak-to-moderate** — genuine live measurement needs deployment data we won't have at hackathon stage; present as a worked methodology + example, not a claimed measured result |

---

## 10. Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Ground-truth source apportionment data is sparse for many cities | Start pilot with cities that have existing source apportionment studies (Delhi, Mumbai); use confidence intervals openly rather than overclaiming elsewhere |
| Satellite data latency/cloud cover gaps | Ground-sensor (CPCB/OpenAQ) fallback mode with widened confidence bands |
| **No free, India-wide, real-time traffic API exists** | Use OSM road-network density as a structural proxy for the pilot; budget for a paid feed (e.g., TomTom's limited free tier, then paid) only once the platform is funded past hackathon/pilot stage |
| **Construction permits & industrial stack registries aren't digitised/API-accessible anywhere in India today** | Treat as a per-city partnership/onboarding task (manual CSV from the municipal body/SPCB), not a data-discovery problem to keep searching for |
| Over-trusting automated enforcement recommendations | Mandatory human-in-the-loop review before any enforcement action is dispatched |
| Citizen advisory fatigue / trust erosion if forecasts are wrong | Always show confidence band to the user, not just a single number |
| Open-Meteo / OpenAQ free-tier rate limits under production load | Cache aggressively (hourly CAAQMS refresh doesn't need per-second polling); self-host Open-Meteo's open-source stack if scaling past non-commercial free tier |
| Overclaiming "AI" where it's really a rule-based lookup (a common hackathon pitfall) | This plan explicitly labels each agent's Method Type (Section 4) and Section 4.8 summarises it plainly — evaluators tend to reward honesty about scope over inflated claims that don't survive questioning |
| Agent 7 (NL Query) hallucinating an answer not actually supported by the platform's data | Hard-scope the agent to retrieval-augmented generation only against the shared context store, with an explicit instruction to say "I don't have that data" rather than fabricate a plausible-sounding number |
| Agent 6 (Anomaly Investigation) over-stating confidence in a plausible-but-wrong explanation | Require the LLM's output to explicitly list what it's uncertain about, and route any anomaly note above a severity threshold through the same human-review queue as enforcement actions |

---

## 11. Deliverables Mapping (for future phases)

This document covers the **implementation plan**. The brief's remaining expected deliverables, when you're ready to build them:

- **Working Prototype** → Phase 1-4 scope (single pilot city, Agents 1, 2, 3, 6 minimum — the highest demo-impact-per-effort set) is the realistic hackathon-timeline target; Agent 7 (NL Query) is the highest-value addition if any time remains.
- **Architecture Diagram** → Section 3.1's layered diagram, refined into a visual (already produced — the 7-agent version).
- **Presentation Deck** → Structured around Sections 1, 3, 4 (agent value, with the honest Method Type framing as a credibility strength, not a weakness), and 9 (evaluation fit).
- **Demo Video** → Should show the attribution → forecast → enforcement chain end-to-end for one ward, then close on Agent 7's natural-language query pulling the same result live — that combination is the strongest possible demo of the platform actually being integrated, not five separate screens.

---

*Next steps: happy to build the City Ops Dashboard mockup (with the NL query bar and anomaly feed), or start drafting the deck outline, whenever you're ready.*
