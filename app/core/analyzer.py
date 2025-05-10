import pandas as pd
import numpy as np
from pathlib import Path
import logging
import plotly.express as px
import pycountry
import streamlit as st
from geoip2.database import Reader

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
LOG_FILE = 'webserver_logs.csv'  # Assumes logs are in CSV format with columns: time, ip, method, resource, status
GEOIP_DB = 'data/GeoLite2-Country.mmdb'

# Helper functions
def load_data(filepath):
    df = pd.read_csv(filepath)
    df.columns = ['time', 'ip', 'method', 'resource', 'status']
    df['datetime'] = pd.to_datetime('1970-01-01 ' + df['time'], errors='coerce')
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.day_name()
    df['is_conversion'] = df['resource'].str.lower().str.contains(r'demo|promo|job|schedule|assistant|ai')
    return df

def resolve_country(ip, reader):
    try:
        response = reader.country(ip)
        return response.country.iso_code
    except:
        return 'Unknown'

def get_country(df):
    if not Path(GEOIP_DB).exists():
        st.warning("GeoLite2 database not found. Falling back to mock country mapping.")
        df['country'] = df['ip'].apply(lambda ip: 'BW')  # Simplified fallback
    else:
        with Reader(GEOIP_DB) as reader:
            df['country'] = df['ip'].apply(lambda ip: resolve_country(ip, reader))
    return df

def convert_to_alpha3(code2):
    try:
        return pycountry.countries.get(alpha_2=code2).alpha_3
    except:
        return 'UNK'

# Streamlit App
st.set_page_config(page_title="Web Log Analyzer", layout="wide")
st.title("📊 Web Server Log Analyzer")

uploaded_file = st.file_uploader("Upload web server log file (CSV)", type=['csv'])

if uploaded_file:
    df = load_data(uploaded_file)
    df = get_country(df)

    st.sidebar.subheader("Summary Statistics")
    st.sidebar.metric("Total Requests", len(df))
    st.sidebar.metric("Conversions", df['is_conversion'].sum())
    st.sidebar.metric("Unique Visitors", df['ip'].nunique())

    st.subheader("Requests by Country")
    country_data = df['country'].value_counts().reset_index()
    country_data.columns = ['country', 'count']
    country_data['iso_alpha'] = country_data['country'].apply(convert_to_alpha3)

    fig1 = px.choropleth(
        country_data,
        locations='iso_alpha',
        locationmode='ISO-3',
        color='count',
        hover_name='country',
        color_continuous_scale=px.colors.sequential.Plasma,
        title='Geographic Distribution of Requests'
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Conversion Activity Over Time")
    conversions_by_hour = df[df['is_conversion']].groupby('hour').size()
    fig2 = px.bar(x=conversions_by_hour.index, y=conversions_by_hour.values, labels={'x': 'Hour of Day', 'y': 'Conversions'}, title="Conversions by Hour")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Requests by Day of the Week")
    day_data = df['day_of_week'].value_counts().reset_index()
    day_data.columns = ['day', 'count']
    fig3 = px.bar(day_data, x='day', y='count', title="Requests by Day of Week")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Request Status Codes")
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    fig4 = px.pie(status_counts, names='status', values='count', title='Status Code Distribution')
    st.plotly_chart(fig4, use_container_width=True)

    st.subheader("Conversion Types")
    conversion_types = df[df['is_conversion']]['resource'].value_counts().nlargest(10)
    fig5 = px.bar(x=conversion_types.index, y=conversion_types.values, labels={'x': 'Resource', 'y': 'Frequency'}, title='Top Conversion Resources')
    st.plotly_chart(fig5, use_container_width=True)

else:
    st.info("Please upload a web server log file in CSV format.")
