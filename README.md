# Cyprus Electricity System Model

A one-day learning project: a [PyPSA](https://pypsa.org)-based model of the Cypriot
electricity system, ending in an interactive geographic dashboard of network and
market indicators.

Cyprus is a small, currently isolated island grid, historically dominated by heavy
fuel oil and diesel generation with rapidly growing solar PV, operated by TSOC with
EAC as the incumbent utility.

> **Status:** learning prototype. Uses a **synthetic but plausible** dataset, not
> validated operational data. See [Assumptions](#assumptions) before drawing
> conclusions.

## What it does

For a representative 24-hour day, the model runs an hourly economic dispatch
(linear optimal power flow) over a simplified 5-bus network and visualises:

- **Network indicators:** line loadings, generator dispatch, generation mix, loads
- **Market indicators:** marginal/locational prices, a single system price, total
  system cost, CO2 emissions

The output is an interactive map with an hour slider — open
`cyprus_dashboard.html` in any browser, no Python required.

## Quick start

```bash
pip install -r requirements.txt
```

Then open **`notebooks/CY_Electricity_Model.ipynb`** in Jupyter (or Google Colab)
and run the cells from top to bottom. Everything lives in this single notebook,
organised into labelled phases (see below). A free solver is required for the
optimisation; this project uses [HiGHS](https://highs.dev) via `highspy`.

## How the notebook is organised

The notebook runs top to bottom in phases:

| Phase | What it does |
|-------|--------------|
| Setup | Installs/imports libraries (PyPSA, pandas, numpy, plotly) |
| 1. Build network | Defines buses, lines, generators, loads; solves one snapshot |
| Congestion demo | Deliberately throttles a line to show locational prices split *(the first attempt is intentionally infeasible — that error is an expected teaching moment, not a bug)* |
| 2. Time-series | Adds a 24-hour demand curve and solar profile; solves the full day |
| 3. Indicators | Extracts tidy dataframes: generation mix, dispatch, prices, line loading, emissions, cost |
| 4. Dashboard | Builds the interactive map with an hour slider; saves `cyprus_dashboard.html` |
| Cleanup | Tags carriers to clear consistency warnings before sharing |

> **Note:** the dashboard cell saves `cyprus_dashboard.html` into the notebook's
> working directory (i.e. `notebooks/` if you run it from there). Move it to the
> repo root if you want it to match the layout below.

## Model at a glance

| Component | Choice | Notes |
|-----------|--------|-------|
| Buses     | ~5, at real plant/city locations | Vasilikos, Dhekelia, Moni, Nicosia, Limassol |
| Lines     | Simple ring/star | Synthetic ratings; transport-style limits |
| Generators| HFO, diesel, solar PV | Synthetic capacities, costs, efficiencies |
| Timeframe | One representative summer day (24 h) | One-line change to extend to a full year |
| Pricing   | Locational prices computed; single load-weighted system price reported | See note below |

### A note on pricing

PyPSA computes a **locational marginal price (LMP)** at each bus — the true marginal
cost of serving one more MW there. These diverge only when a transmission line
congests. Cyprus is a single bidding zone and does **not** use locational pricing in
its real market, so the headline figure here is a **load-weighted single system
price**; the per-bus LMPs are retained as a congestion diagnostic, not as prices
customers would actually pay.

## Assumptions

- All generator capacities, costs, efficiencies, line ratings, and demand are
  **synthetic** values chosen to be realistic, not measured data.
- The grid is modelled as **isolated** (no EuroAsia Interconnector).
- Lines use a simplified transport-style limit rather than full AC power flow.
- A single representative day stands in for seasonal/annual variation.

## Where real data would go (future work)

- **Demand & generation actuals:** ENTSO-E Transparency Platform (free API token)
- **Solar resource:** PVGIS (EU) or renewables.ninja — hourly Cyprus PV profiles
- **Plant fleet:** TSOC annual reports / Global Energy Monitor
- **Fuel & CO2 prices:** EU ETS price + fuel cost assumptions

Other natural extensions: battery storage (to shift midday solar into the evening
peak), the EuroAsia Interconnector as a cross-border link, and a full-year run.

## Repository contents

```
cyprus-power-model/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── notebooks/
│   └── CY_Electricity_Model.ipynb   # the whole project — run top to bottom
├── cyprus_dashboard.html            # saved interactive map (open in a browser)
└── data/
    └── README.md                    # notes on where real data would go
```

## Licence

Released under the MIT Licence — see `LICENSE`.
