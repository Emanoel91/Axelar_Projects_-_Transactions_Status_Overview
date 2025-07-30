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

# --- Load Data ----------------------------------------------------------------------------------------
chain_summary = load_chain_summary()
avg_block_time = load_avg_block_time()
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


