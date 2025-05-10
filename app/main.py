import streamlit as st
import pandas as pd
import analyzer
import plotly.express as px
import numpy as np

# --- Streamlit UI ---
st.set_page_config(page_title="Web Log Analysis Dashboard", layout="wide")

st.title("🌍 Web Server Log Analysis")
st.markdown("Analyze web traffic and conversions to evaluate sales strategies.")

uploaded_file = st.file_uploader("Upload Web Log CSV File", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    analyzer_obj = analyzer.LogAnalyzer(df)  # <-- FIXED: Instantiate the class correctly

    st.success("Log file loaded and processed successfully.")

    # ---- Key Metrics ----
    st.header("🔍 Summary Metrics")
    col1, col2 = st.columns(2)
    with col1:
        overall_conv, by_method = analyzer_obj.get_conversion_metrics()
        st.metric("Overall Conversion Rate", f"{overall_conv * 100:.2f}%")
    with col2:
        st.write("**Conversion Rate by Method:**")
        st.dataframe(
            by_method.reset_index()
            .rename(columns={'method': 'Method', 'is_conversion': 'Conversion Rate (%)'})
            .assign(**{'Conversion Rate (%)': lambda df: df['Conversion Rate (%)'] * 100})
        )

    # ---- Country Choropleth Map ----
    st.header("🌐 Traffic by Country")
    fig_map = analyzer_obj.generate_geo_plot()
    if fig_map:
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.warning("Geo data not available for choropleth map.")

    # ---- Conversions by Hour ----
    st.header("📊 Conversion Activity Over the Day")
    conv_by_hour = analyzer_obj.df.groupby('hour')['is_conversion'].mean().reset_index()
    fig_hour = px.bar(
        conv_by_hour,
        x='hour',
        y='is_conversion',
        labels={'hour': 'Hour of Day', 'is_conversion': 'Conversion Rate'},
        title="Conversions by Hour",
        color='is_conversion',
        color_continuous_scale='Viridis',
    )
    st.plotly_chart(fig_hour, use_container_width=True)

    # ---- Conversion by Day of Week ----
    st.header("📅 Conversions by Day of Week")
    conv_by_day = analyzer_obj.df.groupby('day_of_week')['is_conversion'].mean().reindex(
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    ).reset_index()
    fig_day = px.bar(
        conv_by_day,
        x='day_of_week',
        y='is_conversion',
        title="Conversions by Day of Week",
        labels={'day_of_week': 'Day', 'is_conversion': 'Conversion Rate'},
        color='is_conversion',
        color_continuous_scale='Plasma',
    )
    st.plotly_chart(fig_day, use_container_width=True)

    # ---- Status Code Pie Chart ----
    st.header("📎 HTTP Status Codes Distribution")
    status_counts = analyzer_obj.df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    fig_status = px.pie(
        status_counts,
        names='status',
        values='count',
        title='Status Code Distribution',
        hole=0.4
    )
    st.plotly_chart(fig_status, use_container_width=True)

    # ---- Conversion Resource Breakdown ----
    st.header("🔗 Most Requested Conversion Resources")
    conv_resources = (
        analyzer_obj.df[analyzer_obj.df['is_conversion']]
        .groupby('resource')
        .size()
        .sort_values(ascending=False)
        .reset_index(name='count')
        .head(10)
    )
    fig_resources = px.bar(
        conv_resources,
        x='resource',
        y='count',
        title='Top Conversion Resources',
        color='count',
        labels={'resource': 'Resource', 'count': 'Hits'}
    )
    st.plotly_chart(fig_resources, use_container_width=True)

    # ---- Basic Descriptive Stats ----
    st.header("📈 Descriptive Statistics")
    st.write(analyzer_obj.df.describe(include='all'))

else:
    st.info("Please upload a valid CSV log file to start the analysis.")
