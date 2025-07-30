import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config: Tab Title & Icon -------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Axelar Projects & Transactions Status Overview",
    page_icon="https://img.cryptorank.io/coins/axelar1663924228506.png",
    layout="wide"
)

# --- Title with Logo ---------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 15px;">
        <img src="https://axelarscan.io/logos/chains/axelarnet.svg" alt="Axelar Logo" style="width:60px; height:60px;">
        <h1 style="margin: 0;">Axelar Projects & Transactions Status Overview</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --- builder Info --------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="margin-top: 20px; margin-bottom: 20px; font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg" alt="Eman Raz" style="width:25px; height:25px; border-radius: 50%;">
            <span>Rebuilt by: <a href="https://x.com/0xeman_raz" target="_blank">Eman Raz</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Snowflake Connection --------------------------------------------------------------------------------------------------
conn = snowflake.connector.connect(
    user=st.secrets["snowflake"]["user"],
    password=st.secrets["snowflake"]["password"],
    account=st.secrets["snowflake"]["account"],
    warehouse="SNOWFLAKE_LEARNING_WH",
    database="AXELAR",
    schema="PUBLIC"
)

# --- Query Functions ---------------------------------------------------------------------------------------
# --- Row 1,2 -------------------------
@st.cache_data
def load_chain_summary():
    query = """
        SELECT
            COUNT(DISTINCT tx_id) AS "Number of Transactions",
            COUNT(DISTINCT block_timestamp::date) AS "Activity days",
            COUNT(DISTINCT tx_from) AS "Number of Users",
            ROUND((COUNT(DISTINCT tx_id) / COUNT(DISTINCT block_timestamp::date)) / 24) AS TPH,
            ROUND((COUNT(DISTINCT tx_id) / COUNT(DISTINCT block_timestamp::date)) / 24 / 60) AS TPM,
            ROUND((COUNT(DISTINCT tx_id) / COUNT(DISTINCT block_timestamp::date)) / 24 / 60 / 60) AS TPS,
            ROUND(SUM(fee / 1e6), 2) AS "Total Fee"
        FROM axelar.core.fact_transactions
        WHERE TX_SUCCEEDED = TRUE
    """
    return pd.read_sql(query, conn)

@st.cache_data
def load_avg_block_time():
    query = """
        WITH ordered_blocks AS (
            SELECT 
                block_id,
                block_timestamp,
                LAG(block_timestamp) OVER (ORDER BY block_id) AS prev_timestamp
            FROM axelar.core.fact_blocks
        ),
        block_diffs AS (
            SELECT 
                block_id,
                DATEDIFF('second', prev_timestamp, block_timestamp) AS block_time_seconds
            FROM ordered_blocks
            WHERE prev_timestamp IS NOT NULL
        )
        SELECT 
            ROUND(AVG(block_time_seconds), 2) AS "Average Block Time"
        FROM block_diffs
    """
    return pd.read_sql(query, conn)

# --- Row 3 -----------------------------------
@st.cache_data
def load_tx_success_fail():
    query = """
        SELECT
            DATE_TRUNC(week, block_timestamp)::date AS "Date",
            COUNT(IFF(TX_SUCCEEDED = TRUE, 1, NULL)) AS "Successful Transactions",
            COUNT(IFF(TX_SUCCEEDED = FALSE, 1, NULL)) AS "Failed Transactions",
            COUNT(DISTINCT tx_id) AS TXs
        FROM axelar.core.fact_transactions
        GROUP BY 1
        ORDER BY 1
    """
    return pd.read_sql(query, conn)

@st.cache_data
def load_new_user_metrics():
    query = """
        WITH lst_all AS (
            SELECT 
                tx_from,
                MIN(block_timestamp)::date AS min_date
            FROM axelar.core.fact_transactions
            GROUP BY 1
        )
        SELECT 
            DATE_TRUNC(week, min_date) AS "Date",
            COUNT(DISTINCT tx_from) AS "New Users",
            SUM(COUNT(DISTINCT tx_from)) OVER (ORDER BY DATE_TRUNC(week, min_date)) AS "Cumulative New Users"
        FROM lst_all
        GROUP BY 1
        ORDER BY 1
    """
    return pd.read_sql(query, conn)

# --- Load Data ----------------------------------------------------------------------------------------
chain_summary = load_chain_summary()
avg_block_time = load_avg_block_time()
tx_status = load_tx_success_fail()
new_users = load_new_user_metrics()
# ------------------------------------------------------------------------------------------------------
# --- Row1: Chain Summary KPIs (Txns, Wallets, Fee) ------------------
st.markdown(
    """
    <div style="background-color:#a2f09f; padding:1px; border-radius:10px;">
        <h2 style="color:#000000; text-align:center;">📋Overview</h2>
    </div>
    """,
    unsafe_allow_html=True
)

if not chain_summary.empty:
    stats = chain_summary.iloc[0]
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Number of Transactions", value=f"{stats['Number of Transactions']:,} Txns")

    with col2:
        st.metric(label="Number of Users", value=f"{stats['Number of Users']:,} Wallets")

    with col3:
        st.metric(label="Total Fee", value=f"{stats['Total Fee']:,} AXL")

# --- Row2: Performance KPIs (TPM, TPS, Avg Block Time) ---------------
if not chain_summary.empty and not avg_block_time.empty:
    stats = chain_summary.iloc[0]
    avg_block_sec = avg_block_time["Average Block Time"].iloc[0]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Transaction per Minute (TPM)", value=f"{stats['TPM']} Txns")

    with col2:
        st.metric(label="Transaction per Second (TPS)", value=f"{stats['TPS']} Txns")

    with col3:
        st.metric(label="Average Block Time", value=f"{avg_block_sec} sec")

# --- Row3: Two Charts Side by Side (Transactions + New Users) ---------------------------------------------------------
col1, col2 = st.columns(2)

# Chart 1: Comparing Successful vs. Unsuccessful Transactions
with col1:
    if not tx_status.empty:
        fig1 = go.Figure()

        fig1.add_trace(go.Bar(
            x=tx_status["Date"],
            y=tx_status["Successful Transactions"],
            name="Successful Transactions",
            marker_color="#0099ff",
            yaxis="y"
        ))

        fig1.add_trace(go.Scatter(
            x=tx_status["Date"],
            y=tx_status["Failed Transactions"],
            name="Failed Transactions",
            mode="lines+markers",
            line=dict(color="#fc0060", width=2),
            yaxis="y"
        ))

        fig1.update_layout(
            title="Comparing Successful vs. Unsuccessful Transactions",
            xaxis=dict(title="Date"),
            yaxis=dict(title="Number of Transactions"),
            height=500,
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
            barmode="group"
        )

        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.warning("No data available for transaction success/failure.")

# Chart 2: New User Metrics: Count and Growth
with col2:
    if not new_users.empty:
        fig2 = go.Figure()

        fig2.add_trace(go.Bar(
            x=new_users["Date"],
            y=new_users["New Users"],
            name="New Users",
            marker_color="#0099ff",
            yaxis="y"
        ))

        fig2.add_trace(go.Scatter(
            x=new_users["Date"],
            y=new_users["Cumulative New Users"],
            name="Cumulative New Users",
            mode="lines+markers",
            line=dict(color="#ffeb5a", width=2),
            yaxis="y"
        ))

        fig2.update_layout(
            title="New User Metrics: Count and Growth",
            xaxis=dict(title="Date"),
            yaxis=dict(title="Number of Users"),
            height=500,
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
            barmode="group"
        )

        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No data available for new user metrics.")


# --- Reference and Rebuild Info -------------------------------------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="margin-top: 20px; margin-bottom: 20px; font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <img src="https://cdn-icons-png.flaticon.com/512/3178/3178287.png" alt="Reference" style="width:20px; height:20px;">
            <span>Dashboard Reference: <a href="https://flipsidecrypto.xyz/Saleh/axelar-projects-transactions-status-overview-PIbPtD" target="_blank">https://flipsidecrypto.xyz/Saleh/axelar-projects-transactions-status-overview-PIbPtD</a></span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://pbs.twimg.com/profile_images/1856738793325268992/OouKI10c_400x400.jpg" alt="Flipside" style="width:25px; height:25px; border-radius: 50%;">
            <span>Data Powered by: <a href="https://flipsidecrypto.xyz/home/" target="_blank">Flipside</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Links with Logos ---------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="Axelar" style="width:20px; height:20px;">
            <a href="https://www.axelar.network/" target="_blank">https://www.axelar.network/</a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://cdn-icons-png.flaticon.com/512/5968/5968958.png" alt="X" style="width:20px; height:20px;">
            <a href="https://x.com/axelar" target="_blank">https://x.com/axelar</a>
        </div>
        
    </div>
    """,
    unsafe_allow_html=True
)


