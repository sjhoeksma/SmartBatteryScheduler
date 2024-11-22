import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta

def generate_historical_prices(days=30):
    """Generate historical price data for analysis"""
    end_date = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='h')
    
    # Base parameters for price generation
    base_price = 0.22
    yearly_factor = pd.Series(dates).dt.dayofyear / 365.0
    hourly_factor = pd.Series(dates).dt.hour / 24.0
    
    # Generate prices with seasonality and random variation
    yearly_seasonality = np.sin(2 * np.pi * yearly_factor) * 0.05
    daily_seasonality = np.sin(2 * np.pi * hourly_factor) * 0.1
    
    prices = base_price + yearly_seasonality + daily_seasonality
    prices += np.random.normal(0, 0.02, len(dates))
    
    return pd.Series(prices, index=dates)

def analyze_price_patterns(prices):
    """Analyze price patterns and return key statistics"""
    # Ensure prices is a pandas Series with datetime index
    if not isinstance(prices.index, pd.DatetimeIndex):
        prices.index = pd.to_datetime(prices.index)
    
    # Basic statistics
    daily_avg = prices.resample('D').mean()
    hourly_avg = prices.groupby(pd.Series(prices.index).dt.hour).mean()
    peak_hours = hourly_avg.nlargest(3).index.tolist()
    off_peak_hours = hourly_avg.nsmallest(3).index.tolist()
    
    # Weekly patterns
    weekly_avg = prices.groupby(pd.Series(prices.index).dt.dayofweek).mean()
    weekly_volatility = prices.groupby(pd.Series(prices.index).dt.dayofweek).std()
    
    # Price trend analysis
    rolling_mean = daily_avg.rolling(window=7).mean()
    trend_direction = "Increasing" if rolling_mean.iloc[-1] > rolling_mean.iloc[-7] else "Decreasing"
    
    # Volatility analysis
    daily_volatility = prices.resample('D').std()
    avg_daily_swing = prices.resample('D').agg(lambda x: x.max() - x.min())
    
    return {
        'daily_avg': daily_avg,
        'hourly_avg': hourly_avg,
        'peak_hours': peak_hours,
        'off_peak_hours': off_peak_hours,
        'weekly_avg': weekly_avg,
        'weekly_volatility': weekly_volatility,
        'price_volatility': daily_volatility,
        'avg_daily_swing': avg_daily_swing,
        'trend_direction': trend_direction,
        'rolling_mean': rolling_mean
    }

@st.cache_data(ttl=3600)  # Cache results for 1 hour
def analyze_historical_pv_production(dates, battery, weather_service, progress_bar=None):
    """Analyze historical PV production patterns with batch processing and caching"""
    import logging
    logger = logging.getLogger(__name__)
    
    if battery.max_watt_peak <= 0:
        logger.info("No PV capacity configured, skipping analysis")
        return None
    
    try:
        if battery.max_watt_peak <= 0:
            logger.info("No PV capacity configured, skipping analysis")
            return None

        production_data = []
        total_entries = len(dates)
        successful_entries = 0
        batch_size = 24  # Process 24 hours at a time
        
        # Process data in batches
        for i in range(0, total_entries, batch_size):
            batch_dates = dates[i:i + batch_size]
            batch_data = []
            
            # Update progress bar if provided
            if progress_bar is not None:
                progress = min(1.0, (i + batch_size) / total_entries)
                progress_bar.progress(progress, text=f"Processing PV data... {int(progress * 100)}%")
            
            # Process batch
            for date in batch_dates:
                try:
                    production = weather_service.get_pv_forecast(battery.max_watt_peak, date)
                    if production is not None:  # Validate production value
                        batch_data.append({
                            'datetime': date,
                            'production': float(production),  # Ensure numeric value
                            'hour': date.hour,
                            'day': date.day,
                            'month': date.month,
                            'dayofweek': date.weekday()
                        })
                        successful_entries += 1
                except Exception as e:
                    logger.warning(f"Error processing PV data for {date}: {str(e)}")
                    continue
            
            # Extend production data with batch results
            production_data.extend(batch_data)
            
            # Yield partial results for progressive updates
            if len(production_data) > 0:
                partial_df = pd.DataFrame(production_data)
                yield {
                    'complete': False,
                    'processed_entries': successful_entries,
                    'total_entries': total_entries,
                    'partial_data': partial_df
                }
        
        if not production_data:
            logger.warning("No valid PV production data collected")
            yield {'complete': True, 'data': None}
            return
            
        logger.info(f"Successfully processed {successful_entries}/{total_entries} PV entries")
        
        # Create final DataFrame
        df = pd.DataFrame(production_data)
        
    except Exception as e:
        logger.error(f"Error in PV production analysis: {str(e)}")
        yield {'complete': True, 'data': None}
        return
    
    try:
        # Calculate patterns with timeout protection
        with st.spinner("Calculating production patterns..."):
            # Calculate daily and hourly patterns
            daily_production = df.groupby(df['datetime'].dt.date)['production'].sum()
            hourly_production = df.groupby('hour')['production'].mean()
            monthly_production = df.groupby('month')['production'].mean()
            
            # Calculate peak production times
            hourly_means = df.groupby('hour')['production'].mean()
            peak_hours = hourly_means.sort_values(ascending=False).head(5).index.tolist()
            
            # Calculate efficiency metrics
            total_capacity = battery.max_watt_peak * len(dates) * 24  # Total theoretical capacity
            actual_production = df['production'].sum()
            efficiency_ratio = (actual_production / total_capacity) if total_capacity > 0 else 0
            
            # Return final results
            yield {
                'complete': True,
                'data': {
                    'daily_production': daily_production,
                    'hourly_production': hourly_production,
                    'monthly_production': monthly_production,
                    'peak_hours': peak_hours,
                    'total_production': actual_production,
                    'efficiency_ratio': efficiency_ratio,
                    'production_data': df
                }
            }
            
    except Exception as e:
        logger.error(f"Error calculating production patterns: {str(e)}")
        yield {'complete': True, 'data': None}
        return

def calculate_savings_opportunity(prices, battery):
    """Calculate potential savings based on historical prices"""
    if not isinstance(prices.index, pd.DatetimeIndex):
        prices.index = pd.to_datetime(prices.index)
    
    # Calculate daily potential savings
    daily_swings = prices.resample('D').agg(lambda x: x.max() - x.min())
    max_daily_charge = battery.charge_rate * 1  # Assuming 1 hour of charging
    potential_savings = daily_swings * max_daily_charge
    
    # Calculate weekly savings pattern
    weekly_savings = potential_savings.groupby(potential_savings.index.dayofweek).mean()
    
    # Calculate optimal charging windows
    price_percentiles = prices.quantile([0.25, 0.75])
    optimal_charge_mask = prices <= price_percentiles[0.25]
    optimal_discharge_mask = prices >= price_percentiles[0.75]
    
    return {
        'daily_savings': potential_savings.mean(),
        'weekly_pattern': weekly_savings,
        'optimal_charge_times': optimal_charge_mask,
        'optimal_discharge_times': optimal_discharge_mask,
        'price_thresholds': price_percentiles
    }
