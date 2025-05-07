import streamlit as st
import pandas as pd
import logging
from pathlib import Path
from core.analyzer import LogAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(
    page_title="Log Analytics",
    page_icon="📊",
    layout="wide"
)

def validate_file(uploaded_file) -> pd.DataFrame:
    """Validate and parse uploaded log file."""
    try:
        if uploaded_file.name.endswith('.csv'):
            logger.info("Parsing CSV file")
            return pd.read_csv(uploaded_file)
        else:  # Raw log format
            logger.info("Parsing raw log file")
            return pd.read_csv(
                uploaded_file,
                sep=' ',
                header=None,
                names=['time', 'ip', 'method', 'resource', 'status']
            )
    except Exception as e:
        logger.error(f"File parsing failed: {str(e)}")
        st.error(f"File parsing failed: {str(e)}")
        st.stop()

def display_metrics(analyzer: LogAnalyzer) -> None:
    """Render key metrics dashboard."""
    logger.info("Displaying metrics")
    col1, col2, col3 = st.columns(3)
    
    # Total requests
    total = len(analyzer.df)
    col1.metric("Total Requests", f"{total:,}")
    
    # Conversion rate
    conv_rate, _ = analyzer.get_conversion_metrics()
    col2.metric("Conversion Rate", f"{conv_rate:.1%}")
    
    # Peak hour
    peak_hour = analyzer.df['hour'].value_counts().idxmax()
    col3.metric("Peak Hour", f"{peak_hour}:00 - {peak_hour+1}:00")

def display_geo_analysis(analyzer: LogAnalyzer) -> None:
    """Render geographical analysis section."""
    logger.info("Displaying geo analysis")
    st.header("Geographical Distribution")

    try:
        geo_fig = analyzer.generate_geo_plot()

        if geo_fig:
            st.plotly_chart(geo_fig, use_container_width=True)
        else:
            logger.warning("No geographical data available")
            st.warning("No geographical data available")
            st.dataframe(
                analyzer.df['country'].value_counts(),
                column_config={"value": "Count"}
            )
    except Exception as e:
        logger.error(f"Error in geographical analysis: {str(e)}")
        st.error(f"Analysis failed: {str(e)}")


def display_temporal_analysis(analyzer: LogAnalyzer) -> None:
    """Render time-based patterns."""
    logger.info("Displaying temporal analysis")
    st.header("Temporal Patterns")
    
    tab1, tab2 = st.tabs(["Hourly", "Daily"])
    
    with tab1:
        st.bar_chart(analyzer.df['hour'].value_counts().sort_index())
    
    with tab2:
        st.bar_chart(
            analyzer.df['day_of_week'].value_counts().reindex([
                'Monday', 'Tuesday', 'Wednesday',
                'Thursday', 'Friday', 'Saturday', 'Sunday'
            ])
        )

def display_conversions(analyzer: LogAnalyzer) -> None:
    """Render conversion analysis."""
    logger.info("Displaying conversion analysis")
    st.header("Conversion Analysis")
    _, by_type = analyzer.get_conversion_metrics()
    
    st.subheader("By Request Type")
    st.bar_chart(by_type)
    
    st.subheader("Detailed Records")
    st.dataframe(
        analyzer.df[analyzer.df['is_conversion']],
        hide_index=True,
        use_container_width=True
    )

def main():
    """Main application entry point."""
    logger.info("Starting application")
    st.title("Web Server Log Analytics Dashboard")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload server logs",
        type=['csv', 'log'],
        accept_multiple_files=False
    )
    
    if not uploaded_file:
        logger.info("Waiting for file upload")
        st.info("Please upload a log file to begin analysis")
        return
    
    # Process file
    with st.spinner("Analyzing logs..."):
        try:
            df = validate_file(uploaded_file)
            analyzer = LogAnalyzer(df)
            
            # Validate analyzer initialization
            if not hasattr(analyzer, 'geoip_reader'):
                logger.error("Analyzer initialization failed - missing geoip_reader")
                st.error("Analyzer initialization failed - check logs")
                return
            
            # Dashboard sections
            display_metrics(analyzer)
            display_geo_analysis(analyzer)
            display_temporal_analysis(analyzer)
            display_conversions(analyzer)
            
        except Exception as e:
            logger.exception("Analysis failed")
            st.error(f"Analysis failed: {str(e)}")

if __name__ == "__main__":
    main()