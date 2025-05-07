import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import logging
import os
import plotly.express as px
import pycountry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogAnalyzer:
    """Robust web log analyzer with GeoIP and conversion tracking."""

    REQUIRED_COLS = ['time', 'ip', 'method', 'resource', 'status']
    CONVERSION_PATTERNS = r'demo|promo|job|schedule'
    COUNTRY_MAP = {
        (0, 50): 'US',
        (50, 100): 'UK',
        (100, 150): 'IN',
        (150, 200): 'CA'
    }

    def __init__(self, df: pd.DataFrame):
        self._geoip_reader = None
        self.df = self._validate_and_process(df)

    @property
    def geoip_reader(self) -> Optional[Any]:
        if self._geoip_reader is None:
            self._init_geoip()
        return self._geoip_reader

    def _init_geoip(self) -> None:
        try:
            from geoip2 import database
            geoip_path = Path('data') / 'GeoLite2-Country.mmdb'
            full_path = geoip_path.resolve()
            if not full_path.exists():
                logger.warning(f"GeoIP database not found at {full_path}")
                return
            self._geoip_reader = database.Reader(str(full_path))
            logger.info(f"GeoIP reader initialized successfully from {full_path}")
        except ImportError:
            logger.error("GeoIP2 package not installed. Run: pip install geoip2")
        except Exception as e:
            logger.error(f"GeoIP initialization failed: {str(e)}")

    def _validate_and_process(self, df: pd.DataFrame) -> pd.DataFrame:
        if not set(self.REQUIRED_COLS).issubset(df.columns):
            df = self._standardize_columns(df)

        df_clean = df.copy()
        df_clean['datetime'] = pd.to_datetime(
            '1970-01-01 ' + df_clean['time'],
            errors='coerce'
        )
        df_clean = df_clean.dropna(subset=['datetime'])
        df_clean['hour'] = df_clean['datetime'].dt.hour
        df_clean['day_of_week'] = df_clean['datetime'].dt.day_name()
        df_clean['is_conversion'] = (
            df_clean['resource']
            .str.lower()
            .str.contains(self.CONVERSION_PATTERNS, regex=True, na=False)
        )

        # ✅ Add country resolution here
        logger.info("Resolving countries using GeoIP...")
        df_clean['country'] = df_clean['ip'].apply(self._resolve_country)
        logger.info("Country resolution complete.")

        return df_clean

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.rename(columns=dict(zip(df.columns[:5], self.REQUIRED_COLS)))

    def _resolve_country(self, ip: str) -> str:
        if not ip or not isinstance(ip, str):
            logger.debug(f"Invalid IP format: {ip}")
            return 'Unknown'

        reader = self.geoip_reader
        if reader:
            try:
                response = reader.country(ip)
                if response and response.country and response.country.iso_code:
                    return response.country.iso_code
            except Exception as e:
                logger.warning(f"GeoIP lookup failed for IP '{ip}': {e}")
        else:
            logger.warning("GeoIP reader not available.")

        return self._map_ip_to_country(ip)

    def _map_ip_to_country(self, ip: str) -> str:
        try:
            first_octet = int(ip.split('.')[0])
            for (low, high), country in self.COUNTRY_MAP.items():
                if low <= first_octet < high:
                    return country
        except (ValueError, IndexError, AttributeError):
            logger.debug(f"Failed to map IP '{ip}' to mock country.")
        return 'Unknown'

    def _convert_to_alpha3(self, code2: str) -> str:
        """Convert 2-letter to 3-letter ISO code."""
        try:
            return pycountry.countries.get(alpha_2=code2).alpha_3
        except:
            return 'UNK'

    def get_conversion_metrics(self) -> Tuple[float, pd.Series]:
        overall = self.df['is_conversion'].mean()
        by_type = self.df.groupby('method')['is_conversion'].mean()
        return overall, by_type

    def generate_geo_plot(self, top_n: int = 15):
        if 'country' not in self.df.columns:
            logger.error("Country column missing in DataFrame.")
            return None

        country_data = (
            self.df['country']
            .value_counts()
            .nlargest(top_n)
            .reset_index()
            .rename(columns={'index': 'country', 'country': 'count'})
        )

        country_data['iso_alpha'] = country_data['country'].apply(self._convert_to_alpha3)

        return px.choropleth(
            country_data,
            locations='iso_alpha',
            locationmode='ISO-3',
            color='count',
            hover_name='country',
            title=f'Top {top_n} Countries by Traffic'
        )
