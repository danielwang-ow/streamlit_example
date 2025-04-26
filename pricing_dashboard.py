import streamlit as st
from streamlit_modal import Modal
import pandas as pd
import numpy as np
import plotly.express as px
import json
import io

# --------- MOCK DATA DEFINITIONS ---------
# Card products and MCCs for selection
CARD_PRODUCTS = ["Platinum", "Gold", "Silver", "Business", "Student"]

with open("config/MCC_list.json", "r") as f:
    MCC_LIST = json.load(f)

mcc_options = [m["key"] for m in MCC_LIST]
key_to_label = {m["key"]: m["label"] for m in MCC_LIST}

# Mock country charge table
DEFAULT_COUNTRY_RULES = pd.DataFrame({
    "Country": ["USA", "Canada", "UK", "Germany", "France"],
    "Charge (bps)": [150, 140, 130, 120, 125]
})

# --------------------------
# Initialize Session State
# --------------------------
if "has_run_simulation" not in st.session_state:
    st.session_state["has_run_simulation"] = False

# We'll store the user-selected products, time period, and scenario
if "selected_card_products" not in st.session_state:
    st.session_state["selected_card_products"] = []
if "time_period" not in st.session_state:
    st.session_state["time_period"] = (6, 18)
if "scenario_name" not in st.session_state:
    st.session_state["scenario_name"] = "Scenario A"

# --------- STREAMLIT APP ---------
st.set_page_config(page_title="Pricing Simulation Dashboard", layout="wide")
st.title("💳 Pricing Simulation Dashboard")

# --------- STYLE APP ---------
st.markdown(
    """
    <style>
    span[title] {
        max-width: 1000px !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: initial !important;
        display: inline !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# === SIDEBAR ===

# 1. Select program
program = st.sidebar.selectbox(
    "Select Program",
    options=["Emerging Markets", "PLACEHOLDER 1", "PLACEHOLDER 2"]
)

# 2. Select program definition
program_definition = st.sidebar.selectbox(
    f"Select definition for {program}",
    options=["Unrestricted", "Restricted"]
)

# 3. Button to confirm program selection
select_program_definition = st.sidebar.button("Confirm program selection")

# On button click, store the selections in session state and refresh relevant settings
if select_program_definition:
    st.session_state["selected_program_definition"] = {
        "program": program,
        "definition": program_definition
    }

    # Optionally load specialized settings for Emerging Markets
    if program == "Emerging Markets":
        with open("config/MCC_list.json", "r") as f:
            MCC_LIST = json.load(f)
        mcc_options = [m["key"] for m in MCC_LIST]
        key_to_label = {m["key"]: m["label"] for m in MCC_LIST}
        DEFAULT_COUNTRY_RULES = pd.DataFrame({
            "Country": ["Vietnam", "Cambodia", "Laos"],
            "Charge (bps)": [150, 140, 130]
        })

# 4. Display stored selections if available
if "selected_program_definition" in st.session_state:
    st.sidebar.write(
        f"**Displaying settings for** "
        f"{st.session_state['selected_program_definition']['definition']} "
        f"{st.session_state['selected_program_definition']['program']}"
    )

# 5. Add a horizontal bar
st.sidebar.markdown("---")

# 6. Scenario naming input
scenario_name = st.sidebar.text_input("Scenario Name", st.session_state["scenario_name"])

# Forecast time period
time_period = st.sidebar.slider(
    "Forecast Time Period (Months)", 
    min_value=1, max_value=36, value=st.session_state["time_period"]
)

# 7. Button to run simulation - sets the session state
if st.sidebar.button("Run Simulation"):
    st.session_state["has_run_simulation"] = True
    st.session_state["scenario_name"] = scenario_name
    st.session_state["time_period"] = time_period
    
    # If no products are selected in the Config tab, we can store an empty or partial selection here
    # but you'll see we do that logic in the config tab below if we want immediate selection.

    st.sidebar.write(f"Running simulation for: {st.session_state['scenario_name']}")

# === TOP-LEVEL TABS ===
top_tabs = st.tabs(["Configurations", "Results", "Report Generation"])

# ----------------------------------------------------------------------------
# 1) CONFIGURATIONS TAB (NESTED SUB-TABS)
# ----------------------------------------------------------------------------
with top_tabs[0]:
    # Sub-tabs inside Configurations
    sub_tabs = st.tabs(["Pricing / Network", "Events Driven"])

    # ---TAB 1: PRICING / NETWORK---
    with sub_tabs[0]:
        st.header("Pricing / Network Parameters")
        col1, col2 = st.columns([2, 3])

        with st.expander("Affected Products - click to expand", expanded=False):
            # Card product multi-select
            # We'll read/write to st.session_state["selected_card_products"]
            st.session_state["selected_card_products"] = st.multiselect(
                "Select Card Product(s)", 
                options=CARD_PRODUCTS, 
                default=st.session_state["selected_card_products"] or [CARD_PRODUCTS[0]],
            )
        
        with st.expander("Pricing by MCC - click to expand", expanded=False):
            # Initialize session state if not present
            if "show_upload" not in st.session_state:
                st.session_state["show_upload"] = False

            # Button toggles the boolean
            if st.button("Upload MCC Rules"):
                st.session_state["show_upload"] = True

            # Conditionally show the upload "popup"
            if st.session_state["show_upload"]:
                st.subheader("Upload MCC Rules CSV (Optional)")
                uploaded_mcc_file = st.file_uploader(
                    "Upload CSV file with MCC rules",
                    type=["csv"],
                    help="If a file is uploaded, it overrides the local JSON data."
                )

                # Button to hide
                if st.button("Close Uploader"):
                    st.session_state["show_upload"] = False
            else:
                uploaded_mcc_file = None
                
            # 1) Initialize "master" and "temp" in session_state if not present
            if "mcc_rules_full" not in st.session_state:
                st.session_state["mcc_rules_full"] = pd.DataFrame([
                    {
                        "MCC": m["key"],
                        "Merchant Name": m["name"],
                        "PCT (%)": m["pct"],
                        "PTF ($)": m["ptf"],
                        "Cap ($)": m["cap_value"]
                    }
                    for m in MCC_LIST
                ])

            if "mcc_rules_temp" not in st.session_state:
                # Start temp data as a copy of the full data
                st.session_state["mcc_rules_temp"] = st.session_state["mcc_rules_full"].copy()

            # 2) Handle CSV Upload
            if uploaded_mcc_file is not None:
                try:
                    uploaded_df = pd.read_csv(uploaded_mcc_file)
                    st.session_state["mcc_rules_full"] = uploaded_df
                    # Reset the temp data to match the newly uploaded data
                    st.session_state["mcc_rules_temp"] = uploaded_df.copy()
                    st.success("CSV uploaded successfully.")
                except Exception as e:
                    st.error(f"Error reading uploaded CSV: {e}")
                    st.warning("Falling back to default MCC_LIST from JSON.")
                    st.session_state["mcc_rules_full"] = pd.DataFrame([
                        {
                            "MCC": m["key"],
                            "Merchant Name": m["name"],
                            "PCT (%)": m["pct"],
                            "PTF ($)": m["ptf"],
                            "Cap ($)": m["cap_value"]
                        }
                        for m in MCC_LIST
                    ])
                    st.session_state["mcc_rules_temp"] = st.session_state["mcc_rules_full"].copy()

            # 3) Filter the "temp" DataFrame
            mcc_filter_text = st.text_input("Filter on MCC or Merchant Name", "")

            # Copy the temp data for local filtering/display
            temp_df_for_display = st.session_state["mcc_rules_temp"].copy()

            if mcc_filter_text:
                temp_df_for_display = temp_df_for_display[
                    temp_df_for_display["MCC"].astype(str).str.contains(mcc_filter_text, case=False, na=False)
                    | temp_df_for_display["Merchant Name"].astype(str).str.contains(mcc_filter_text, case=False, na=False)
                ]

            st.markdown("#### MCC Rules (Filtered View)")

            # 4) Let user edit the filtered subset
            edited_filtered_df = st.data_editor(
                temp_df_for_display,
                column_config={
                    "MCC": st.column_config.Column(disabled=True),
                    "Merchant Name": st.column_config.Column(disabled=True),
                    "PCT (%)": st.column_config.Column(disabled=False),
                    "PTF ($)": st.column_config.Column(disabled=False),
                    "Cap ($)": st.column_config.Column(disabled=False),
                },
                num_rows="dynamic",
                use_container_width=True,
                key="temp_editor"
            )

            # 5) Save the user's changes to the "temp" data
            for idx in edited_filtered_df.index:
                st.session_state["mcc_rules_temp"].loc[idx] = edited_filtered_df.loc[idx]

            # 6) Provide a button to commit temp edits into the master data
            if st.button("Save Edits"):
                # Merge all current temp changes into the master data
                for idx in st.session_state["mcc_rules_temp"].index:
                    st.session_state["mcc_rules_full"].loc[idx] = st.session_state["mcc_rules_temp"].loc[idx]
                st.success("Edits have been saved to master data!")

        
        with st.expander("Countries - click to expand", expanded=False):
            # Country rules table
            st.markdown("#### Country Rules")
            country_rules = st.data_editor(
                DEFAULT_COUNTRY_RULES,
                num_rows="dynamic",
                use_container_width=True,
                key="country_rules_editor"
            )
            st.caption("Tip: Filter or edit country charges directly in the table.")

    # # ---TAB 2: CARD QUALIFICATION---
    # with sub_tabs[1]:
    #     st.header("Card Qualification")
    #     st.info("This section will be developed in the future.")

    # ---TAB 3: EVENTS DRIVEN---
    with sub_tabs[1]:
        st.header("Events Driven")
        st.info("This section will be developed in the future.")


# ----------------------------------------------------------------------------
# 2) RESULTS TAB WITH SUB-TABS (Net Sales, All In Revenue, All In Net Effective Rate)
# ----------------------------------------------------------------------------
with top_tabs[1]:
    # Create sub-tabs inside the Results tab
    results_sub_tabs = st.tabs(["Net Sales", "All In Revenue", "All In Net Effective Rate"])

    # =======================
    #     2.1) NET SALES
    # =======================
    with results_sub_tabs[0]:
        st.header("Net Sales")

        # Retrieve from session state
        has_run_simulation = st.session_state["has_run_simulation"]
        card_products = st.session_state["selected_card_products"]
        forecast_range = st.session_state["time_period"]

        if has_run_simulation and card_products:
            # Months from forecast_range[0] to forecast_range[1]
            months = np.arange(forecast_range[0], forecast_range[1] + 1)

            # Convert user-selected card_products to a list
            selected_products = list(card_products)
            num_products = len(selected_products)

            # Build a DataFrame for Net Sales ($MM)
            product_rows = selected_products + ["", "Card Present", "Card Not Present", "Grand Total"]

            np.random.seed(42)
            product_data = {"Product": product_rows}
            for m in months:
                col_name = f"M{m}"
                # Random for the 'actual' products
                product_vals = list(np.random.uniform(5, 15, size=num_products))
                # aggregator rows: blank + Card Present + Not Present + Grand Total
                aggregator_vals = [0, 0, 0, 0]
                product_data[col_name] = product_vals + aggregator_vals

            df_net_sales = pd.DataFrame(product_data)
            month_cols = [f"M{m}" for m in months]

            # Sum across months for "Total"
            df_net_sales["Total"] = df_net_sales[month_cols].sum(axis=1)

            # Identify the indexes of aggregator rows
            blank_row_idx = num_products
            card_present_idx = num_products + 1
            card_not_present_idx = num_products + 2
            grand_total_idx = num_products + 3

            # Calculate aggregator row values
            for col in month_cols:
                sum_of_products = df_net_sales.loc[0:num_products - 1, col].sum()
                df_net_sales.at[card_present_idx, col] = sum_of_products * 0.60
                df_net_sales.at[card_not_present_idx, col] = sum_of_products * 0.40
                df_net_sales.at[grand_total_idx, col] = (
                    df_net_sales.at[card_present_idx, col] + df_net_sales.at[card_not_present_idx, col]
                )

            # Recalc aggregator totals
            for idx in [card_present_idx, card_not_present_idx, grand_total_idx]:
                df_net_sales.at[idx, "Total"] = df_net_sales.loc[idx, month_cols].sum()

            # Hide numeric values in blank row
            df_net_sales.loc[blank_row_idx, month_cols + ["Total"]] = np.nan

            # Style function to highlight the blank row
            def highlight_empty_row(row):
                return [
                    "background-color: lightgrey" if row["Product"] == "" else ""
                    for _ in row
                ]

            # TABLE 1: Net Sales ($ MM)
            st.subheader("Table 1: Net Sales ($ MM)")
            styled_df_net_sales = (
                df_net_sales.style
                .apply(highlight_empty_row, axis=1)
                .format(na_rep="")
            )
            st.dataframe(styled_df_net_sales, use_container_width=True)

            # --------------------
            # "View Chart" button
            # --------------------
            if "table1_modal_open" not in st.session_state:
                st.session_state.table1_modal_open = False

            modal_table1 = Modal(
                key="modal_table1",
                title="Net Sales - Table 1 Chart",
                max_width="700px"
            )

            # Button to open
            if st.button("View Chart: Table 1"):
                st.session_state.table1_modal_open = True

            # If open, build one chart with ALL lines from Table 1
            if st.session_state.table1_modal_open:
                with modal_table1.container():
                    long_df = df_net_sales[df_net_sales["Product"] != ""].reset_index(drop=True)
                    melted = long_df.melt(
                        id_vars="Product",
                        value_vars=month_cols,
                        var_name="Month",
                        value_name="Value"
                    )
                    melted["Month"] = melted["Month"].str.replace("M", "").astype(int)

                    fig_table1 = px.line(
                        melted,
                        x="Month", y="Value", color="Product",
                        markers=True,
                        title="All Lines – Net Sales ($ MM)",
                    )
                    st.plotly_chart(fig_table1, use_container_width=True)

                    # Close button
                    if st.button("Close Chart: Table 1"):
                        st.session_state.table1_modal_open = False

                modal_table1.open()

            # =================
            # TABLE 2: Net Sales (% of Total)
            # =================
            st.subheader("Table 2: Net Sales (% of Total)")

            # Construct a second DataFrame for percentages
            df_net_sales_pct = df_net_sales.copy()

            # For each column, divide by the Grand Total row except the blank row
            for col in month_cols + ["Total"]:
                denominator = df_net_sales_pct.at[grand_total_idx, col]
                if denominator != 0:
                    df_net_sales_pct[col] = (df_net_sales_pct[col] / denominator) * 100
                else:
                    df_net_sales_pct[col] = np.nan

            # Keep the blank row's numeric cells as NaN
            df_net_sales_pct.loc[blank_row_idx, month_cols + ["Total"]] = np.nan

            styled_df_net_sales_pct = (
                df_net_sales_pct.style
                .apply(highlight_empty_row, axis=1)
                .format(na_rep="")
            )
            st.dataframe(styled_df_net_sales_pct, use_container_width=True)

            # --------------------
            # "View Chart" button for Table 2
            # --------------------
            if "table2_modal_open" not in st.session_state:
                st.session_state.table2_modal_open = False

            modal_table2 = Modal(
                key="modal_table2",
                title="Net Sales - Table 2 Chart",
                max_width="700px"
            )

            if st.button("View Chart: Table 2"):
                st.session_state.table2_modal_open = True

            if st.session_state.table2_modal_open:
                with modal_table2.container():
                    long_pct_df = df_net_sales_pct[df_net_sales_pct["Product"] != ""].reset_index(drop=True)
                    melted_pct = long_pct_df.melt(
                        id_vars="Product",
                        value_vars=month_cols,
                        var_name="Month",
                        value_name="PctValue"
                    )
                    melted_pct["Month"] = melted_pct["Month"].str.replace("M", "").astype(int)

                    fig_table2 = px.line(
                        melted_pct,
                        x="Month", y="PctValue", color="Product",
                        markers=True,
                        title='All Lines – Net Sales (% of Total)'
                    )
                    fig_table2.update_yaxes(ticksuffix="%")
                    st.plotly_chart(fig_table2, use_container_width=True)

                    if st.button("Close Chart: Table 2"):
                        st.session_state.table2_modal_open = False

                modal_table2.open()

        else:
            st.info("Please click 'Run Simulation' to generate Net Sales results (and make sure at least one product is selected).")
        
        
        if has_run_simulation and card_products:
            # Prepare the two DataFrames for export (remove styling)
            export_table1 = df_net_sales.copy()
            export_table2 = df_net_sales_pct.copy()

            # Optional: Format numbers for Excel (e.g., round to 2 decimals)
            export_table1 = export_table1.round(2)
            export_table2 = export_table2.round(2)

            # Create an in-memory buffer
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                export_table1.to_excel(writer, index=False, sheet_name='Net Sales ($MM)')
                export_table2.to_excel(writer, index=False, sheet_name='Net Sales (% of Total)')
            output.seek(0)

            # Download button
            st.download_button(
                label="⬇️ Download Net Sales Tables (Excel)",
                data=output,
                file_name=f"Net_Sales_Tables_{st.session_state['scenario_name'].replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        
    # =======================
    #  2.2) ALL IN REVENUE
    # =======================
    with results_sub_tabs[1]:
        st.header('"All In" Revenue')
        st.info('Content for "All In" Revenue will go here.')

    # =======================
    # 2.3) ALL IN NET EFFECTIVE RATE
    # =======================
    with results_sub_tabs[2]:
        st.header('"All In" Net Effective Rate')
        st.info('Content for "All In" Net Effective Rate will go here.')
       

        
# ----------------------------------------------------------------------------
# 3) REPORT GENERATION TAB
# ----------------------------------------------------------------------------
with top_tabs[2]:
    st.header("Report Generation")
    st.info("Here you can implement your PDF/Excel report generation logic, or any output feature.")