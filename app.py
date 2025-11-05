import pandas as pd
import numpy as np
import joblib
import streamlit as st
import plotly.graph_objects as go
from statsmodels.nonparametric.smoothers_lowess import lowess

# ✅ Load pre-trained pipeline
model = joblib.load("ev_range_pipeline.pkl")

# --- App Configuration ---
st.set_page_config(page_title="EV Range Predictor", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f9fafb; padding: 2rem; }
    .stButton button {
        background-color: #0072e8;
        color: white;
        border-radius: 10px;
        font-size: 16px;
        height: 3em;
        width: 100%;
    }
    .stButton button:hover { background-color: #005bb5; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Electric Vehicle Range Prediction Dashboard")
st.markdown("### Estimate your EV’s driving range and visualize how different features impact it!")

# --- Tabs ---
tab1, tab2 = st.tabs(["🚗 Single EV Prediction", "📂 Upload CSV for Bulk Prediction"])

# =====================
# 🚗 SINGLE ENTRY TAB
# =====================
with tab1:
    st.subheader("Enter EV Details")
    col1, col2 = st.columns(2)

    with col1:
        brand = st.selectbox("Brand", ["Tesla", "BMW", "Hyundai", "Kia", "Nissan"])
        model_name = st.text_input("Model", "Model 3")
        powertrain = st.selectbox("PowerTrain", ["RWD", "AWD", "FWD"])
        rapid_charge = st.selectbox("RapidCharge", ["Yes", "No"])
        plug_type = st.selectbox("PlugType", ["Type 2", "Type 1", "CHAdeMO"])
        body_style = st.selectbox("BodyStyle", ["Sedan", "SUV", "Hatchback"])
        segment = st.selectbox("Segment", ["A", "B", "C", "D", "E"])

    with col2:
        battery = st.number_input("Battery Capacity (kWh)", min_value=10.0, max_value=200.0, value=60.0)
        accel = st.number_input("Acceleration (0–100 km/h in sec)", min_value=2.0, max_value=20.0, value=5.6)
        top_speed = st.number_input("Top Speed (km/h)", min_value=60.0, max_value=400.0, value=180.0)
        efficiency = st.number_input("Efficiency (Wh/km)", min_value=80.0, max_value=300.0, value=150.0)
        fast_charge = st.number_input("FastCharge (km/h)", min_value=0.0, max_value=1000.0, value=300.0)
        seats = st.number_input("Seats", min_value=2, max_value=8, value=5)
        price = st.number_input("Price (€)", min_value=10000.0, max_value=200000.0, value=50000.0)

    # --- Prepare input ---
    sample = pd.DataFrame([{
        'Brand': brand,
        'Model': model_name,
        'PowerTrain': powertrain,
        'RapidCharge': rapid_charge,
        'PlugType': plug_type,
        'BodyStyle': body_style,
        'Segment': segment,
        'Battery_Capacity_kWh': battery,
        'AccelSec': accel,
        'TopSpeed_KmH': top_speed,
        'Efficiency_WhKm': efficiency,
        'FastCharge_KmH': fast_charge,
        'Seats': seats,
        'PriceEuro': price
    }])

    # Derived features
    sample["Range_per_kWh"] = sample["Battery_Capacity_kWh"] / (sample["Efficiency_WhKm"] / 1000)
    sample["Efficiency_ratio"] = sample["Battery_Capacity_kWh"] / sample["Efficiency_WhKm"]
    sample["Cost_per_km"] = sample["PriceEuro"] / 1000

    st.markdown("---")

    # Initialize session state
    if "predicted_range" not in st.session_state:
        st.session_state.predicted_range = None
        st.session_state.sample = None

    # --- Prediction Button ---
    if st.button("🚗 Predict EV Range"):
        try:
            predicted_range = model.predict(sample)[0]
            st.session_state.predicted_range = predicted_range
            st.session_state.sample = sample
            st.success(f"🔋 **Estimated EV Range:** {predicted_range:.2f} km")
        except Exception as e:
            st.error("⚠️ Prediction error.")
            st.code(str(e))

    # --- Visualization (shown after prediction) ---
    if st.session_state.predicted_range is not None:
        st.markdown("### 📈 Explore Feature Impact on Range")

        numeric_features = [
            "Battery_Capacity_kWh", "Efficiency_WhKm", "AccelSec",
            "TopSpeed_KmH", "FastCharge_KmH", "PriceEuro"
        ]
        selected_feature = st.selectbox("Choose a numeric feature to visualize:", numeric_features)

        sample = st.session_state.sample
        predicted_range = st.session_state.predicted_range

        # Create realistic value range
        feature_ranges = {
            "Battery_Capacity_kWh": np.linspace(30, 120, 30),
            "Efficiency_WhKm": np.linspace(100, 250, 30),
            "AccelSec": np.linspace(3, 15, 30),
            "TopSpeed_KmH": np.linspace(100, 300, 30),
            "FastCharge_KmH": np.linspace(50, 800, 30),
            "PriceEuro": np.linspace(20000, 150000, 30)
        }

        x_values = feature_ranges[selected_feature]
        temp_samples = pd.concat([sample] * len(x_values), ignore_index=True)
        temp_samples[selected_feature] = x_values
        y_pred = model.predict(temp_samples)

        # --- Scatter + Trendline ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_values, y=y_pred,
            mode="markers", name="Predictions",
            marker=dict(size=8, color="#00CC96")
        ))

        smoothed = lowess(y_pred, x_values, frac=0.25)
        slope = smoothed[-1, 1] - smoothed[0, 1]
        trend_color = 'lime' if slope > 0 else 'red'

        fig.add_trace(go.Scatter(
            x=smoothed[:, 0],
            y=smoothed[:, 1],
            mode='lines',
            line=dict(color=trend_color, width=3),
            name='Trendline'
        ))

        fig.add_trace(go.Scatter(
            x=[sample[selected_feature].iloc[0]],
            y=[predicted_range],
            mode='markers+text',
            text=["Your EV"],
            textposition="top center",
            marker=dict(color='yellow', size=12, symbol='star'),
            name='Your EV'
        ))

        fig.update_layout(
            title=f"Effect of {selected_feature} on Predicted EV Range",
            xaxis_title=selected_feature,
            yaxis_title="Predicted Range (km)",
            template="plotly_dark",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        trend_text = "increases" if slope > 0 else "decreases"
        st.info(f"💡 As **{selected_feature}** increases, the predicted range **{trend_text}**. "
                f"Green trendline = positive correlation, red = negative correlation.")

# =====================
# 📂 BULK UPLOAD TAB
# =====================
with tab2:
    st.subheader("Upload a CSV for Bulk Prediction")
    uploaded_file = st.file_uploader("📤 Upload CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df.head())

        if st.button("⚡ Predict All"):
            try:
                preds = model.predict(df)
                df["Predicted_Range_km"] = preds
                st.success("✅ Predictions Completed!")
                st.dataframe(df[["Brand", "Model", "Predicted_Range_km"]])

                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Results", csv, "predicted_ev_ranges.csv", "text/csv")
            except Exception as e:
                st.error("⚠️ Error during bulk prediction.")
                st.code(str(e))

st.markdown("---")
st.caption("Built with ❤️ by **Tirtha Jhaveri** | Powered by Gradient Boosting Regressor ⚡")
