import streamlit as st
import pypsa
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Cyprus Grid Dashboard", layout="wide")
st.title("⚡ Cyprus Electricity Market Dashboard")
st.markdown("Interactive dispatch model using PyPSA and HiGHS.")

# --- 2. CACHED MODEL EXECUTION ---
# @st.cache_resource ensures the model only builds and solves ONCE when the app starts.
# Moving the Streamlit slider will only redraw the map, not rerun the whole optimization.
@st.cache_resource
def solve_cyprus_model():
    n = pypsa.Network()
    
    # Buses (with real coordinates)
    buses = pd.DataFrame({
        "Vasilikos": (33.336, 34.717),
        "Dhekelia":  (33.700, 34.985),
        "Moni":      (33.183, 34.713),
        "Nicosia":   (33.365, 35.185),
        "Limassol":  (33.045, 34.707),
    }, index=["x", "y"]).T

    for name, row in buses.iterrows():
        n.add("Bus", name, x=row.x, y=row.y, v_nom=132, carrier="AC")

    # Lines
    lines = [
        ("Vasilikos-Moni",  "Vasilikos", "Moni",      400),
        ("Moni-Limassol",   "Moni",      "Limassol",  400),
        ("Vasilikos-Nicosia","Vasilikos","Nicosia",   500),
        ("Nicosia-Dhekelia","Nicosia",   "Dhekelia",  300),
        ("Dhekelia-Vasilikos","Dhekelia","Vasilikos", 300),
    ]
    for name, b0, b1, s_nom in lines:
        n.add("Line", name, bus0=b0, bus1=b1, s_nom=s_nom, x=0.1, r=0.01, carrier="AC")

    # Carriers & Generators
    n.add("Carrier", "oil", co2_emissions=0.65)
    n.add("Carrier", "diesel", co2_emissions=0.70)
    n.add("Carrier", "solar", co2_emissions=0.0)

    generators = [
        ("Vasilikos_HFO",   "Vasilikos", "oil",    700, 110, 0.40),
        ("Dhekelia_HFO",    "Dhekelia",  "oil",    300, 120, 0.38),
        ("Moni_Diesel",     "Moni",      "diesel", 150, 180, 0.35),
        ("Limassol_Solar",  "Limassol",  "solar",  200,   0, 1.00),
        ("Nicosia_Solar",   "Nicosia",   "solar",  150,   0, 1.00),
    ]
    for name, bus, carrier, p_nom, mc, eff in generators:
        n.add("Generator", name, bus=bus, carrier=carrier, p_nom=p_nom, marginal_cost=mc, efficiency=eff)

    # Loads
    loads = [
        ("Nicosia_Load",  "Nicosia",  450),
        ("Limassol_Load", "Limassol", 350),
        ("Dhekelia_Load", "Dhekelia", 120),
    ]
    for name, bus, p_set in loads:
        n.add("Load", name, bus=bus, p_set=p_set)

    # Time Series Setup (24 hours)
    snapshots = pd.date_range("2024-06-21 00:00", periods=24, freq="h")
    n.set_snapshots(snapshots)
    n.snapshot_weightings.loc[:, :] = 1.0

    hours = np.arange(24)
    demand_shape = 0.55 + 0.20 * np.exp(-((hours - 9)**2)/8) + 0.45 * np.exp(-((hours - 20)**2)/6)
    demand_shape = pd.Series(demand_shape / demand_shape.max(), index=snapshots)

    for load in n.loads.index:
        n.loads_t.p_set[load] = n.loads.at[load, "p_set"] * demand_shape
    n.loads["p_set"] = 0.0 

    solar_shape = np.clip(np.sin((hours - 6) / 12 * np.pi), 0, None)
    solar_shape = pd.Series(solar_shape, index=snapshots)
    for g in n.generators.index[n.generators.carrier == "solar"]:
        n.generators_t.p_max_pu[g] = solar_shape

    # Optimize and detach solver
    n.optimize(solver_name="highs", include_objective_constant=False)
    n.model.solver_model = None 
    return n

# Initialize the model
with st.spinner("Solving PyPSA optimization model..."):
    n = solve_cyprus_model()

# --- 3. UI CONTROLS ---
# Use Streamlit's native slider instead of Plotly's built-in animation timeline
st.markdown("### View Network Dispatch")
selected_hour = st.slider("Select Hour of the Day", min_value=0, max_value=23, value=14, step=1, format="%d:00")

# --- 4. MAP VISUALIZATION ---
def create_mapbox(n, hour_idx):
    snap = n.snapshots[hour_idx]
    prices = n.buses_t.marginal_price
    line_loading = (n.lines_t.p0.abs() / n.lines.s_nom * 100)
    gen_by_bus_t = n.generators_t.p.T.groupby(n.generators.bus).sum().T
    bus_xy = n.buses[["x", "y"]]

    def load_colour(pct):
        if pct < 50: return "#2ecc71" # Green
        if pct < 80: return "#f1c40f" # Amber
        return "#e74c3c"              # Red

    fig = go.Figure()

    # 1. Draw Lines
    mid_lons, mid_lats, labels = [], [], []
    for ln, row in n.lines.iterrows():
        lon0, lat0 = bus_xy.loc[row.bus0]
        lon1, lat1 = bus_xy.loc[row.bus1]
        pct = line_loading.at[snap, ln]
        
        # Line trace
        fig.add_trace(go.Scattermapbox(
            lon=[lon0, lon1], lat=[lat0, lat1],
            mode="lines",
            line=dict(width=4, color=load_colour(pct)),
            hoverinfo="text",
            text=f"Line: {ln}<br>Loading: {pct:.0f}%",
            showlegend=False
        ))
        
        # Save midpoints for text labels
        mid_lons.append((lon0 + lon1) / 2)
        mid_lats.append((lat0 + lat1) / 2)
        labels.append(f"{pct:.0f}%")

    # 2. Draw Line Loading Text
    fig.add_trace(go.Scattermapbox(
        lon=mid_lons, lat=mid_lats,
        mode="text", text=labels,
        textfont=dict(size=12, color="black"),
        hoverinfo="skip", showlegend=False
    ))

    # 3. Draw Buses
    sizes = 12 + gen_by_bus_t.reindex(columns=bus_xy.index).loc[snap].fillna(0) / 20
    colour = prices.loc[snap, bus_xy.index]
    hover = [f"<b>{b}</b><br>Price: €{prices.at[snap,b]:.0f}/MWh<br>Generation: {gen_by_bus_t.reindex(columns=bus_xy.index).at[snap,b]:.0f} MW" for b in bus_xy.index]

    fig.add_trace(go.Scattermapbox(
        lon=bus_xy.x, lat=bus_xy.y,
        mode="markers+text",
        marker=dict(
            size=sizes, color=colour, colorscale="YlOrRd",
            cmin=float(prices.values.min()), cmax=float(prices.values.max()),
            colorbar=dict(title="LMP (€/MWh)")
        ),
        text=bus_xy.index, textposition="top center",
        hoverinfo="text", hovertext=hover, showlegend=False
    ))

    # Configure the real map
    fig.update_layout(
        mapbox=dict(
            style="carto-positron", # Clean, free, open-source basemap
            center=dict(lat=34.9, lon=33.3), # Centered on Cyprus
            zoom=7.5
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600
    )
    return fig

# Render the map
fig = create_mapbox(n, selected_hour)
st.plotly_chart(fig, use_container_width=True)

# --- 5. DATA METRICS ---
col1, col2, col3 = st.columns(3)
total_demand = n.loads_t.p_set.sum(axis=1).iloc[selected_hour]
solar_gens = n.generators.index[n.generators.carrier == "solar"]
total_solar = n.generators_t.p[solar_gens].sum(axis=1).iloc[selected_hour]

col1.metric("Total System Demand", f"{total_demand:,.0f} MW")
col2.metric("Solar Output", f"{total_solar:,.0f} MW")
col3.metric("Daily System Cost", f"€{n.objective:,.0f}")