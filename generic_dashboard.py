import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(layout="wide")

# --- State Management ---
if "analysis_run" not in st.session_state:
    st.session_state.analysis_run = False
if "results_df" not in st.session_state:
    st.session_state.results_df = None
if "table_data" not in st.session_state:
    st.session_state.table_data = None
if "num_vars" not in st.session_state:
    st.session_state.num_vars = [
        {"name": "Mean (F1)", "value": 50.0},
        {"name": "Std Dev (F1)", "value": 10.0},
        {"name": "Mean (F2)", "value": 100.0},
        {"name": "Std Dev (F2)", "value": 20.0},
        {"name": "Binomial n (F3)", "value": 10},
        {"name": "Binomial p (F3)", "value": 0.5},
        {"name": "Uniform Low (F4)", "value": 0.0},
        {"name": "Uniform High (F4)", "value": 1.0},
        {"name": "Poisson λ (F5)", "value": 3.0},
        {"name": "Sample Size", "value": 100},
    ]

# --- Tabs Layout ---
tabs = st.tabs(["Input", "Results"])

# =============================================================================
# Tab 1: INPUT
# =============================================================================
with tabs[0]:
    st.title("📊 Sensitivity Analysis Dashboard")
    st.markdown(
        "A professional dashboard for running sensitivity analyses using simulated data. "
        "Adjust parameters below, enter or upload tabular data, and run the simulation."
    )
    
    # Create three columns for layout
    col_num, col_other, col_table = st.columns(3)

    # ---------------------
    # Column 1: Numerical Inputs (Dynamic)
    # ---------------------
    with col_num:
        st.subheader("Numerical Inputs (Dynamic)")

        # Buttons to add/remove variables
        add_remove_row = st.columns([1, 1])
        with add_remove_row[0]:
            if st.button("➕ Add Variable"):
                st.session_state.num_vars.append(
                    {"name": f"Var {len(st.session_state.num_vars) + 1}", "value": 0.0}
                )
        with add_remove_row[1]:
            if st.button("➖ Remove Variable") and len(st.session_state.num_vars) > 1:
                st.session_state.num_vars.pop()

        # Render each numerical input
        for i, var in enumerate(st.session_state.num_vars):
            var_name = st.text_input(f"Name {i+1}", value=var["name"], key=f"num_name_{i}")
            var_value = st.number_input(f"Value {i+1}", value=var["value"], key=f"num_value_{i}")
            st.session_state.num_vars[i]["name"] = var_name
            st.session_state.num_vars[i]["value"] = var_value

    # ---------------------
    # Column 2: Other Settings (Toggles and Dropdowns)
    # ---------------------
    with col_other:
        st.subheader("Other Settings")

        st.markdown("##### Toggles")
        toggle1 = st.checkbox("Add Gaussian Noise")
        toggle2 = st.checkbox("Apply Log Transformation")
        toggle3 = st.checkbox("Shuffle Data")
        toggle4 = st.checkbox("Add Outliers")
        toggle5 = st.checkbox("Drop Nulls")

        st.markdown("##### Dropdowns")
        dropdown1 = st.selectbox("Distribution for F6", ["Normal", "Uniform", "Exponential"])
        dropdown2 = st.selectbox("Category for F7", ["A", "B", "C"])
        dropdown3 = st.selectbox("Scaling Method", ["None", "MinMax", "Standard"])
        dropdown4 = st.selectbox("Correlation Strength", ["Low", "Medium", "High"])
        dropdown5 = st.selectbox("Dataset Label", ["Scenario 1", "Scenario 2", "Scenario 3"])

    # ---------------------
    # Column 3: Tabular Data Entry
    # ---------------------
    with col_table:
        st.subheader("Tabular Data Entry")

        tabular_option = st.radio("Choose table input method:", ["Manual Entry", "Upload CSV"])
        if tabular_option == "Manual Entry":
            table_data = st.data_editor(
                pd.DataFrame(
                    {
                        "Parameter": [f"Param {i+1}" for i in range(5)],
                        "Value": [0.0] * 5
                    }
                ),
                num_rows="dynamic"
            )
            st.session_state.table_data = table_data

        else:
            uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
            if uploaded_file:
                table_data = pd.read_csv(uploaded_file)
                st.write(table_data)
                st.session_state.table_data = table_data
            else:
                table_data = None
                st.session_state.table_data = None

    # ---------------------
    # Run Button (below columns)
    # ---------------------
    run = st.button("Run Sensitivity Analysis 🚀")

    if run:
        np.random.seed(42)  # for reproducibility

        # Helper to retrieve a stored variable by name
        def get_var(name, default=0.0):
            for v in st.session_state.num_vars:
                if v["name"] == name:
                    return v["value"]
            return default

        # Extract defaulted or user-provided values
        mean_f1 = get_var("Mean (F1)", 50.0)
        std_f1  = get_var("Std Dev (F1)", 10.0)
        mean_f2 = get_var("Mean (F2)", 100.0)
        std_f2  = get_var("Std Dev (F2)", 20.0)
        binom_n = int(get_var("Binomial n (F3)", 10))
        binom_p = get_var("Binomial p (F3)", 0.5)
        unif_low = get_var("Uniform Low (F4)", 0.0)
        unif_high = get_var("Uniform High (F4)", 1.0)
        pois_lambda = get_var("Poisson λ (F5)", 3.0)
        N = int(get_var("Sample Size", 100))

        # Generate features
        feature1 = np.random.normal(mean_f1, std_f1, N)
        feature2 = np.random.normal(mean_f2, std_f2, N)
        feature3 = np.random.binomial(binom_n, binom_p, N)
        feature4 = np.random.uniform(unif_low, unif_high, N)
        feature5 = np.random.poisson(pois_lambda, N)

        # Feature 6
        if dropdown1 == "Normal":
            feature6 = np.random.normal(0, 1, N)
        elif dropdown1 == "Uniform":
            feature6 = np.random.uniform(0, 1, N)
        else:
            feature6 = np.random.exponential(1, N)

        # Feature 7: Category
        feature7 = np.random.choice([dropdown2, "Other"], N)

        # Feature 8: Correlated with feature1
        corr_strength = {"Low": 0.2, "Medium": 0.6, "High": 0.9}[dropdown4]
        feature8 = feature1 * corr_strength + np.random.normal(0, 1, N) * (1 - corr_strength)

        # Feature 9: Random integers
        feature9 = np.random.randint(0, 100, N)

        # Feature 10: Label
        feature10 = [dropdown5] * N

        # Combine into DataFrame
        df = pd.DataFrame({
            "Feature1": feature1,
            "Feature2": feature2,
            "Feature3": feature3,
            "Feature4": feature4,
            "Feature5": feature5,
            "Feature6": feature6,
            "Feature7": feature7,
            "Feature8": feature8,
            "Feature9": feature9,
            "Label": feature10
        })

        # Apply Toggles
        if toggle1:
            df += np.random.normal(0, 0.05, df.shape)
        if toggle2:
            for c in ["Feature1", "Feature2"]:
                df[c] = np.log1p(np.abs(df[c]))
        if toggle3:
            df = df.sample(frac=1).reset_index(drop=True)
        if toggle4:
            outlier_indices = np.random.choice(df.index, size=int(0.01*N), replace=False)
            df.loc[outlier_indices, "Feature1"] += np.random.normal(100, 20, size=len(outlier_indices))
        if toggle5:
            df = df.dropna()

        # Apply Scaling
        if dropdown3 == "MinMax":
            for c in df.select_dtypes(include=[np.number]).columns:
                df[c] = (df[c] - df[c].min()) / (df[c].max() - df[c].min())
        elif dropdown3 == "Standard":
            for c in df.select_dtypes(include=[np.number]).columns:
                df[c] = (df[c] - df[c].mean()) / df[c].std()

        # Save final DataFrame in session_state for "Results" tab
        st.session_state.analysis_run = True
        st.session_state.results_df = df

        st.success("Analysis complete! View results in the 'Results' tab.")

# =============================================================================
# Tab 2: RESULTS
# =============================================================================
with tabs[1]:
    st.title("Analysis Results")
    if st.session_state.analysis_run and st.session_state.results_df is not None:
        df = st.session_state.results_df

        st.subheader("Generated Dataset Preview")
        st.dataframe(df.head(10))
        st.success(f"Generated dataset with {df.shape[0]} rows and {df.shape[1]} columns.")

        st.subheader("Summary Statistics")
        st.write(df.describe())

        if st.session_state.table_data is not None:
            st.subheader("Your Table Data")
            st.write(st.session_state.table_data)

        st.info("You can download the full dataset as a CSV file below.")
        st.download_button("Download CSV", df.to_csv(index=False), "sensitivity_data.csv")
    else:
        st.info("No analysis results to display yet. Run an analysis from the 'Input' tab.")

# --- Footer ---
st.markdown("---")
st.markdown(
    "<div style='text-align: right; color: gray; font-size: 0.9em;'>"
    "Oliver Wyman Mock Sensitivity Analysis Dashboard &copy; 2025"
    "</div>", 
    unsafe_allow_html=True
)