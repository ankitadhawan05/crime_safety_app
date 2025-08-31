# free_api_utils.py - with probabilistic crime model 
import requests
import pandas as pd
import folium
import streamlit as st
import numpy as np
from streamlit_folium import st_folium 
from data_preprocess import load_crime_data, add_time_of_day
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Tuple, Dict, Optional
import math

# ================= FREE OSRM CONFIGURATION =================
OSRM_HOST = "router.project-osrm.org"  # Free public OSRM server

# ================= RESEARCH-BASED VULNERABILITY FACTORS =================
def get_research_based_vulnerability_factors():
    """
    Returns more realistic vulnerability factors for different travel modes.
    Adjusted to provide more reasonable risk assessments.
    """
    return {
        "driving": {
            "base_vulnerability": 1.0,
            "night_multiplier": 1.1,  
            "rationale": "Enclosed space, ability to lock doors and escape quickly"
        },
        "cycling": {
            "base_vulnerability": 1.3,  
            "night_multiplier": 1.15,   
            "rationale": "Exposed but mobile, moderate escape speed (~15 km/h)"
        },
        "walking": {
            "base_vulnerability": 1.5,  
            "night_multiplier": 1.2,    
            "rationale": "Fully exposed, lowest escape speed (~5 km/h), easiest target"
        }
    }

# ================= FIXED CRIME DATA LOADING  =================
@st.cache_data
def load_crime_data_for_areas():
    """
    Load ALL crime data for area selection (no time filtering)
    This ensures all areas are always available regardless of time selection
    """
    try:
        df = load_crime_data()
        
        if 'Time of Day' not in df.columns:
            df = add_time_of_day(df)
        
        def classify_enhanced_crime_severity(row):
            crime_desc = str(row.get('Crm Cd Desc', '')).upper()
            
            # High severity crimes (Red level)
            high_severity = ['ROBBERY', 'ASSAULT WITH DEADLY WEAPON, AGGRAVATED ASSAULT', 'BURGLARY', 
                           'RAPE, FORCIBLE', 'CRIMINAL HOMICIDE', 'MURDER', 'EXTORTION',
                           'KIDNAPPING', 'ARSON', 'DISCHARGE FIREARMS/SHOTS FIRED', 'CRIMINAL THREATS', 
                           'BATTERY WITH SEXUAL CONTACT', 'SEXUAL PENETRATION W/FOREIGN OBJECT',
                           'CRM AGNST CHLD (13 OR UNDER) (14-15 & SUSP 10 YRS OLDER)']
            
            if any(crime in crime_desc for crime in high_severity):
                return 0  # High risk (Red)
            
            # Medium severity crimes (Yellow level) 
            medium_severity = ['THEFT, PERSON', 'VANDALISM', 'FRAUD', 'SHOPLIFTING', 'VEHICLE - STOLEN',
                             'VEHICLE - ATTEMPT STOLEN', 'TRESPASSING', 'PICKPOCKET', 'BURGLARY FROM VEHICLE',
                             'DISCHARGE FIREARMS/SHOTS FIRED', 'SHOTS FIRED AT INHABITED DWELLING']
            
            if any(crime in crime_desc for crime in medium_severity):
                return 1  # Medium risk (Yellow)
            
            return 2  # Low risk (Green)
        
        df['Cluster'] = df.apply(classify_enhanced_crime_severity, axis=1)
        
        return df
    except Exception as e:
        st.error(f"Error loading crime data: {e}")
        return None

@st.cache_data
def get_area_coordinates(crime_df):
    """
    Get fixed coordinates for all areas (doesn't change with time filtering)
    """
    area_coords = {}
    
    if crime_df is not None and not crime_df.empty:
        area_groups = crime_df.groupby('AREA NAME')[['LAT', 'LON']].agg({
            'LAT': 'mean',
            'LON': 'mean'
        }).reset_index()
        
        for _, row in area_groups.iterrows():
            area_coords[row['AREA NAME']] = {
                'lat': row['LAT'],
                'lon': row['LON']
            }
    
    return area_coords

def get_research_based_crime_weights():
    """
    Returns crime severity weights based on criminological research.
    """
    
    crime_severity_weights = {
        'high': {
            'weight': 8.5,
            'crimes': [
                'ROBBERY', 'ASSAULT WITH DEADLY WEAPON, AGGRAVATED ASSAULT', 'BURGLARY',
                'RAPE, FORCIBLE', 'CRIMINAL HOMICIDE', 'MURDER', 'EXTORTION',
                'KIDNAPPING', 'ARSON', 'DISCHARGE FIREARMS/SHOTS FIRED',
                'CRIMINAL THREATS', 'BATTERY WITH SEXUAL CONTACT',
                'SEXUAL PENETRATION W/FOREIGN OBJECT', 'CRM AGNST CHLD (13 OR UNDER)'
            ]
        },
        'medium': {
            'weight': 2.8,
            'crimes': [
                'THEFT, PERSON', 'VANDALISM', 'FRAUD', 'SHOPLIFTING',
                'VEHICLE - STOLEN', 'VEHICLE - ATTEMPT STOLEN', 'TRESPASSING',
                'PICKPOCKET', 'BURGLARY FROM VEHICLE', 'SHOTS FIRED AT INHABITED DWELLING'
            ]
        },
        'low': {
            'weight': 1.0,
            'crimes': 'ALL_OTHER_CRIMES'
        }
    }
    
    return crime_severity_weights

def get_evidence_based_vulnerability_factors():
    """
    Returns travel mode vulnerability factors from victimization research.
    """
    
    return {
        "walking": {"vulnerability": 2.1},
        "cycling": {"vulnerability": 1.6},
        "driving": {"vulnerability": 1.0}
    }

def routes_are_similar(route1, route2, threshold=0.7):
    """Check if two routes are too similar"""
    if not route1 or not route2:
        return False
    
    if abs(len(route1) - len(route2)) > len(route1) * 0.3:
        return False
    
    # Sample points for comparison
    sample_size = min(10, min(len(route1), len(route2)))
    indices = np.linspace(0, min(len(route1), len(route2)) - 1, sample_size, dtype=int)
    
    similar_points = 0
    for i in indices:
        if i < len(route1) and i < len(route2):
            lon1, lat1 = route1[i]
            lon2, lat2 = route2[i]
            # Check if points are within ~200 meters
            if abs(lon1 - lon2) < 0.002 and abs(lat1 - lat2) < 0.002:
                similar_points += 1
    
    return (similar_points / sample_size) > threshold

def get_safety_level_from_probability(crime_probability_percentage, travel_mode):
    """Determine safety level based on crime probability percentage"""
    # Mode-specific thresholds for realistic probability ranges
    thresholds = {
        "driving": {"low": 2.0, "medium": 8.0},     # 0-2%, 2-8%, 8%+
        "cycling": {"low": 3.0, "medium": 12.0},    # 0-3%, 3-12%, 12%+  
        "walking": {"low": 4.0, "medium": 15.0}     # 0-4%, 4-15%, 15%+
    }
    
    mode_thresholds = thresholds.get(travel_mode, thresholds["driving"])
    
    if crime_probability_percentage < mode_thresholds["low"]:
        return "low"
    elif crime_probability_percentage < mode_thresholds["medium"]:
        return "medium"
    else:
        return "high"

# ================= TIME-OF-DAY ANALYSIS (SILENT) =================
def calculate_time_risk_weights(crime_df):
    """
    Calculate time-based risk weights from actual crime distribution.
    These are used ONLY for "Any Time" mode to provide risk estimates.
    """
    if crime_df is None or crime_df.empty or 'Time of Day' not in crime_df.columns:
        return {
            "Morning": 1.0,
            "Afternoon": 1.0,
            "Evening": 1.0, 
            "Night": 1.0
        }
    
    # Count crimes and calculate rates per hour
    time_periods = {
        "Morning": 6,    # 6am-12pm
        "Afternoon": 4,  # 12pm-4pm
        "Evening": 2,    # 4pm-6pm
        "Night": 12      # 6pm-6am
    }
    
    crime_counts = crime_df['Time of Day'].value_counts()
    
    # Calculate crime rate per hour for each period
    crime_rates = {}
    for period, hours in time_periods.items():
        count = crime_counts.get(period, 0)
        rate_per_hour = count / hours if hours > 0 else 0
        crime_rates[period] = rate_per_hour
    
    # Normalize to get relative weights (baseline = average rate)
    avg_rate = sum(crime_rates.values()) / len(crime_rates)
    
    weights = {}
    for period, rate in crime_rates.items():
        if avg_rate > 0:
            weights[period] = min(2.0, max(0.5, rate / avg_rate))
        else:
            weights[period] = 1.0
    
    return weights

# ================= PROBABILISTIC CRIME ESTIMATOR =================

class BaselinePoissonCrimeEstimator:
    """
    Original Poisson process model for crime probability estimation
  
    """
    
    def __init__(self, crime_df: pd.DataFrame, historical_years: float = 3.0):
        """
        Initialize with historical crime data
        
        Args:
            crime_df: Historical crime dataset
            historical_years: Years of historical data for rate calculation
        """
        self.crime_df = crime_df
        self.historical_years = historical_years
        self._calculate_base_crime_rates()
        self._estimate_coverage_area()
        self.time_risk_weights = self._calculate_time_risk_weights()
    
    def _calculate_time_risk_weights(self):
        """Calculate time-based risk weights from actual crime distribution"""
        if self.crime_df is None or self.crime_df.empty or 'Time of Day' not in self.crime_df.columns:
            return {"Morning": 1.0, "Afternoon": 1.0, "Evening": 1.0, "Night": 1.0}
        
        time_periods = {
            "Morning": 6,    # 6am-12pm
            "Afternoon": 4,  # 12pm-4pm
            "Evening": 2,    # 4pm-6pm
            "Night": 12      # 6pm-6am
        }
        
        crime_counts = self.crime_df['Time of Day'].value_counts()
        
        crime_rates = {}
        for period, hours in time_periods.items():
            count = crime_counts.get(period, 0)
            rate_per_hour = count / hours if hours > 0 else 0
            crime_rates[period] = rate_per_hour
        
        avg_rate = sum(crime_rates.values()) / len(crime_rates)
        
        weights = {}
        for period, rate in crime_rates.items():
            if avg_rate > 0:
                weights[period] = min(2.0, max(0.5, rate / avg_rate))
            else:
                weights[period] = 1.0
        
        return weights
    
    def _calculate_base_crime_rates(self):
        """Calculate base crime rates from historical data (crimes per km² per year)"""
        if self.crime_df is None or self.crime_df.empty:
            self.base_crime_rates = {'high': 0, 'medium': 0, 'low': 0, 'total': 0}
            return
        
        lat_range = self.crime_df['LAT'].max() - self.crime_df['LAT'].min()
        lon_range = self.crime_df['LON'].max() - self.crime_df['LON'].min()
        
        # Approximate coverage area (degrees to km conversion for LA area ~34°N)
        coverage_area_km2 = (lat_range * 111) * (lon_range * 111 * math.cos(math.radians(34.05)))
        
        severity_counts = self.crime_df['Cluster'].value_counts()
        
        self.base_crime_rates = {
            'high': severity_counts.get(0, 0) / (self.historical_years * coverage_area_km2),
            'medium': severity_counts.get(1, 0) / (self.historical_years * coverage_area_km2),
            'low': severity_counts.get(2, 0) / (self.historical_years * coverage_area_km2),
            'total': len(self.crime_df) / (self.historical_years * coverage_area_km2),
            'coverage_area_km2': coverage_area_km2
        }
    
    def _estimate_coverage_area(self):
        """Estimate the geographical coverage area of the dataset"""
        self.coverage_area_km2 = self.base_crime_rates.get('coverage_area_km2', 1000)
    
    def calculate_route_crime_probability(self, crimes_near_route: dict, 
                                        route_distance_km: float,
                                        route_time_minutes: float,
                                        travel_mode: str,
                                        time_of_day: str = "Any Time",
                                        is_filtered: bool = False) -> dict:
        """
        Calculate probability of crime occurrence using Poisson process model
        
        BASELINE VERSION - No calibration applied
        """
        
        # Mode vulnerability factors backed by research
        vulnerability_factors = {"walking": 2.1, "cycling": 1.6, "driving": 1.0}
        vulnerability = vulnerability_factors.get(travel_mode, 1.0)
        
        # Mode-specific exposure parameters
        proximity_radii = {'walking': 0.25, 'cycling': 0.20, 'driving': 0.15}
        buffer_radius_km = proximity_radii.get(travel_mode, 0.20)
        route_exposure_area_km2 = route_distance_km * (2 * buffer_radius_km)
        
        # Get crime counts
        high_crimes = crimes_near_route.get('high', 0)
        medium_crimes = crimes_near_route.get('medium', 0)
        low_crimes = crimes_near_route.get('low', 0)
        total_crimes = high_crimes + medium_crimes + low_crimes
        
        # Severity weights
        severity_weights = {'high': 8.5, 'medium': 2.8, 'low': 1.0}
        
        if total_crimes > 0:
            # Use observed crimes near route
            weighted_score = (
                high_crimes * severity_weights['high'] +
                medium_crimes * severity_weights['medium'] +
                low_crimes * severity_weights['low']
            )
            
            crime_density_per_km = weighted_score / route_distance_km
            
            # BASELINE: Uses full year for time fraction
            minutes_per_year = 365 * 24 * 60
            trip_time_fraction = route_time_minutes / minutes_per_year
            
            lambda_base = crime_density_per_km * route_exposure_area_km2 * trip_time_fraction
            
        else:
            # Use base rates when no crimes found
            weighted_base_rate = (
                self.base_crime_rates['high'] * severity_weights['high'] +
                self.base_crime_rates['medium'] * severity_weights['medium'] + 
                self.base_crime_rates['low'] * severity_weights['low']
            )
            
            minutes_per_year = 365 * 24 * 60
            trip_time_fraction = route_time_minutes / minutes_per_year
            
            lambda_base = weighted_base_rate * route_exposure_area_km2 * trip_time_fraction
        
        # Apply time weight for "Any Time" mode
        if time_of_day == "Any Time" and not is_filtered:
            time_periods = ["Morning", "Afternoon", "Evening", "Night"]
            hours = [6, 4, 2, 12]
            total_hours = 24
            
            weighted_sum = sum(
                self.time_risk_weights[period] * hour / total_hours 
                for period, hour in zip(time_periods, hours)
            )
            time_weight = weighted_sum
        else:
            time_weight = 1.0
        
        # Apply adjustments (NO CALIBRATION in baseline)
        lambda_adjusted = lambda_base * vulnerability * time_weight
        
        # Calculate Poisson probabilities
        try:
            prob_zero_crimes = math.exp(-lambda_adjusted)
            prob_at_least_one = 1 - prob_zero_crimes
            prob_exactly_one = lambda_adjusted * math.exp(-lambda_adjusted) if lambda_adjusted > 0 else 0
        except (OverflowError, ValueError):
            if lambda_adjusted > 20:
                prob_zero_crimes = 0.0
                prob_at_least_one = 1.0
                prob_exactly_one = 0.0
            else:
                prob_zero_crimes = 1.0
                prob_at_least_one = 0.0
                prob_exactly_one = 0.0
        
        crime_probability_percentage = prob_at_least_one * 100
        crime_probability_percentage = min(crime_probability_percentage, 50.0)  # Cap at 50%
        
        # Calculate confidence bounds
        if lambda_adjusted > 0:
            lambda_std = math.sqrt(lambda_adjusted)
            lambda_lower = max(0, lambda_adjusted - 1.96 * lambda_std)
            lambda_upper = lambda_adjusted + 1.96 * lambda_std
            
            prob_lower = max(0, (1 - math.exp(-lambda_upper)) * 100)
            prob_upper = min(50, (1 - math.exp(-lambda_lower)) * 100)
        else:
            prob_lower = prob_upper = 0
        
        return {
            'crime_probability_percentage': crime_probability_percentage,
            'probability_no_crime': prob_zero_crimes * 100,
            'probability_exactly_one_crime': prob_exactly_one * 100,
            'expected_crimes_per_trip': lambda_adjusted,
            'probability_lower_95ci': prob_lower,
            'probability_upper_95ci': prob_upper,
            'lambda_base': lambda_base,
            'lambda_adjusted': lambda_adjusted,
            'vulnerability_factor': vulnerability,
            'time_weight': time_weight,
            'route_exposure_area_km2': route_exposure_area_km2,
            'crime_exposure_percentage': crime_probability_percentage,
            'normalized_risk': min(prob_at_least_one, 1.0),
            'model_version': 'baseline'
        }

# ================= ENHANCED ROUTE OPTIMIZER =================

class RouteOptimizer:
    """
    Route optimizer with probabilistic crime model
    """
    
    def __init__(self, crime_df: pd.DataFrame, time_of_travel: str = "Any Time"):
        """
        Initialize with crime data and time filter
        """
        self.full_crime_df = crime_df
        self.time_of_travel = time_of_travel
        self.crime_df = crime_df
        self.prob_estimator = BaselinePoissonCrimeEstimator(crime_df)
        
        # Determine if filtering is active
        self.is_time_filtered = time_of_travel != "Any Time"
        
        self._preprocess_crime_data()
        self._create_time_filtered_index()
    
    def _preprocess_crime_data(self):
        """Preprocess crime data for efficient spatial queries"""
        if self.crime_df is None or self.crime_df.empty:
            self.crime_grid = {}
            return
            
        self.crime_grid = defaultdict(list)
        grid_size = 0.01  # ~1km grid cells
        
        for idx, crime in self.crime_df.iterrows():
            if pd.notna(crime.get('LAT')) and pd.notna(crime.get('LON')):
                grid_x = int(crime['LON'] / grid_size)
                grid_y = int(crime['LAT'] / grid_size)
                
                crime_data = {
                    'lat': crime['LAT'],
                    'lon': crime['LON'],
                    'severity': crime.get('Cluster', 1),
                    'time_of_day': crime.get('Time of Day', 'Unknown'),
                    'crime_id': idx
                }
                
                # Add to immediate and adjacent cells
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        self.crime_grid[(grid_x + dx, grid_y + dy)].append(crime_data)
    
    def _create_time_filtered_index(self):
        """Create a separate index for time-filtered crimes"""
        self.time_filtered_grid = defaultdict(list)
        
        if self.full_crime_df is None or self.full_crime_df.empty:
            return
        
        time_mapping = {
            "Morning (6-12)": "Morning",
            "Afternoon (12-16)": "Afternoon",
            "Evening (16-18)": "Evening",
            "Night (18-6)": "Night",
            "Any Time": None
        }
        
        target_time = time_mapping.get(self.time_of_travel)
        grid_size = 0.01
        
        for idx, crime in self.full_crime_df.iterrows():
            if target_time and crime.get('Time of Day') != target_time:
                continue
                
            if pd.notna(crime.get('LAT')) and pd.notna(crime.get('LON')):
                grid_x = int(crime['LON'] / grid_size)
                grid_y = int(crime['LAT'] / grid_size)
                
                crime_data = {
                    'lat': crime['LAT'],
                    'lon': crime['LON'],
                    'severity': crime.get('Cluster', 1),
                    'time_of_day': crime.get('Time of Day', 'Unknown'),
                    'crime_id': idx
                }
                
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        self.time_filtered_grid[(grid_x + dx, grid_y + dy)].append(crime_data)
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula (km)"""
        R = 6371
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _calculate_comprehensive_risk(self, route_coords: List,
                                     travel_mode: str,
                                     start_time: str) -> Dict:
        """
        Probabilistic crime risk calculation with proper time handling
        """
        
        MODE_PARAMS = {
            "driving": {
                "speed_kmh": 50,
                "proximity_radius": 0.15,
            },
            "cycling": {
                "speed_kmh": 15,
                "proximity_radius": 0.2,
            },
            "walking": {
                "speed_kmh": 5,
                "proximity_radius": 0.25,
            }
        }
        
        params = MODE_PARAMS.get(travel_mode, MODE_PARAMS["driving"])
        
        total_distance_km = 0
        total_time_minutes = 0
        crimes_encountered = {
            'high': set(),
            'medium': set(),
            'low': set()
        }
        
        # Collect crimes along route
        for i in range(len(route_coords) - 1):
            lon1, lat1 = route_coords[i]
            lon2, lat2 = route_coords[i + 1]
            
            segment_distance_km = self._haversine_distance(lat1, lon1, lat2, lon2)
            segment_time_minutes = (segment_distance_km / params["speed_kmh"]) * 60
            
            total_distance_km += segment_distance_km
            total_time_minutes += segment_time_minutes
            
            nearby_crimes = self._get_crimes_near_point(lat1, lon1, params["proximity_radius"])
            
            for crime in nearby_crimes:
                crime_id = crime.get('crime_id')
                severity = crime.get('severity', 1)
                
                if severity == 0:
                    crimes_encountered['high'].add(crime_id)
                elif severity == 1:
                    crimes_encountered['medium'].add(crime_id)
                else:
                    crimes_encountered['low'].add(crime_id)
        
        high_count = len(crimes_encountered['high'])
        medium_count = len(crimes_encountered['medium'])
        low_count = len(crimes_encountered['low'])
        
        # Prepare data for probabilistic calculation
        crimes_near_route = {
            'high': high_count,
            'medium': medium_count,
            'low': low_count
        }
        
        # Use probabilistic estimator with proper time handling
        prob_data = self.prob_estimator.calculate_route_crime_probability(
            crimes_near_route, 
            total_distance_km, 
            total_time_minutes, 
            travel_mode,
            self.time_of_travel,
            is_filtered=self.is_time_filtered
        )
        
        # Calculate crime ratios for analysis
        total_crimes = high_count + medium_count + low_count
        if total_crimes > 0:
            high_ratio = high_count / total_crimes
            medium_ratio = medium_count / total_crimes
            low_ratio = low_count / total_crimes
        else:
            high_ratio = medium_ratio = low_ratio = 0
        
        return {
            # Core probabilistic metrics
            'crime_probability_percentage': prob_data['crime_probability_percentage'],
            'crime_exposure_percentage': prob_data['crime_exposure_percentage'],
            'normalized_risk': prob_data['normalized_risk'],
            
            # Route metrics
            'total_time_minutes': total_time_minutes,
            'total_distance_km': total_distance_km,
            
            # Crime counts
            'high_crimes': high_count,
            'medium_crimes': medium_count,
            'low_crimes': low_count,
            'total_crimes': total_crimes,
            
            # Analysis data
            'high_ratio': high_ratio,
            'medium_ratio': medium_ratio,
            'low_ratio': low_ratio,
            
            # Probabilistic model details
            'probabilistic_data': prob_data,
            
            # Confidence intervals
            'probability_lower_95ci': prob_data['probability_lower_95ci'],
            'probability_upper_95ci': prob_data['probability_upper_95ci'],
            
            # Additional metrics
            'total_risk_score': prob_data['lambda_adjusted'] * 100,
            'weighted_crime_score': (high_count * 8.5 + medium_count * 2.8 + low_count * 1.0),
            'crime_density': (high_count * 8.5 + medium_count * 2.8 + low_count * 1.0) / max(total_distance_km, 0.1),
            'time_weight_applied': prob_data['time_weight']
        }
    
    def _get_crimes_near_point(self, lat: float, lon: float, radius_km: float) -> List:
        """Get crimes within radius of a point"""
        grid_size = 0.01
        grid_x = int(lon / grid_size)
        grid_y = int(lat / grid_size)
        
        # Use time-filtered grid if time is specified
        if self.time_of_travel != "Any Time":
            nearby_crimes = self.time_filtered_grid.get((grid_x, grid_y), [])
        else:
            nearby_crimes = self.crime_grid.get((grid_x, grid_y), [])
        
        # Filter by actual distance
        crimes_in_radius = []
        for crime in nearby_crimes:
            distance_km = self._haversine_distance(lat, lon, crime['lat'], crime['lon'])
            if distance_km <= radius_km:
                crimes_in_radius.append(crime)
        
        return crimes_in_radius
    
    def calculate_objective_function(self, route_coords: List[Tuple[float, float]], 
                                    start_coords: Tuple[float, float],
                                    end_coords: Tuple[float, float],
                                    travel_mode: str = "driving",
                                    start_time: str = "09:00",
                                    alpha: float = 0.3,
                                    beta: float = 0.7) -> Dict:
        """
        Calculate f(route) = α·D(route) + β·R(route, mode, t)
        Using probabilistic risk calculation
        """
        # Ensure weights sum to 1
        weight_sum = alpha + beta
        if abs(weight_sum - 1.0) > 0.001:
            alpha = alpha / weight_sum
            beta = beta / weight_sum
        
        # Calculate normalized distance component
        D_route = self._calculate_normalized_distance(route_coords, start_coords, end_coords)
        
        # Calculate probabilistic risk component
        R_route_data = self._calculate_comprehensive_risk(route_coords, travel_mode, start_time)
        R_route = R_route_data['normalized_risk']  # Uses probabilistic model
        
        # Objective function (minimization)
        objective_score = alpha * D_route + beta * R_route
        
        return {
            'objective_score': objective_score,
            'distance_component': alpha * D_route,
            'risk_component': beta * R_route,
            'normalized_distance': D_route,
            'normalized_risk': R_route,
            'route_distance_km': R_route_data['total_distance_km'],
            'route_time_minutes': R_route_data['total_time_minutes'],
            'crime_exposure_percentage': R_route_data['crime_exposure_percentage'],
            'crime_probability_percentage': R_route_data['crime_probability_percentage'],
            'high_crimes': R_route_data['high_crimes'],
            'medium_crimes': R_route_data['medium_crimes'],
            'low_crimes': R_route_data['low_crimes'],
            'total_crimes': R_route_data['total_crimes'],
            'probability_confidence_interval': f"{R_route_data['probability_lower_95ci']:.1f}%-{R_route_data['probability_upper_95ci']:.1f}%",
            'alpha': alpha,
            'beta': beta
        }
    
    def _calculate_normalized_distance(self, route_coords: List, 
                                      start_coords: Tuple, 
                                      end_coords: Tuple) -> float:
        """Calculate normalized distance score (0 = direct path, 1 = 2x direct)"""
        route_distance = 0
        for i in range(len(route_coords) - 1):
            lon1, lat1 = route_coords[i]
            lon2, lat2 = route_coords[i + 1]
            segment_dist = self._haversine_distance(lat1, lon1, lat2, lon2)
            route_distance += segment_dist
        
        start_lat, start_lon = start_coords
        end_lat, end_lon = end_coords
        direct_distance = self._haversine_distance(start_lat, start_lon, end_lat, end_lon)
        
        if direct_distance == 0:
            return 0
        
        distance_ratio = route_distance / direct_distance
        normalized = min((distance_ratio - 1.0), 1.0)
        normalized = max(0, normalized)
        
        return normalized

# ================= ROUTE GENERATION AND VARIANTS =================
def get_free_osrm_routes(start_coords, end_coords, travel_mode="driving"):
    """Get real road routes from free OSRM public server"""
    
    profile_mapping = {
        "driving": "driving",
        "walking": "foot", 
        "cycling": "bike"
    }
    
    profile = profile_mapping.get(travel_mode, "driving")
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    url = f"http://{OSRM_HOST}/route/v1/{profile}/{start_lon},{start_lat};{end_lon},{end_lat}"
    
    params = {
        "geometries": "geojson",
        "alternatives": "3",
        "steps": "false",
        "overview": "full"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("code") == "Ok" and data.get("routes"):
                routes = {}
                route_info = []
                
                for idx, route in enumerate(data["routes"][:3]):
                    coordinates = route["geometry"]["coordinates"]
                    distance = route.get("distance", 0)
                    duration = route.get("duration", 0)
                    
                    route_data = {
                        "coordinates": coordinates,
                        "distance": f"{distance/1000:.1f} km",
                        "duration": f"{duration//60:.0f} min",
                        "distance_meters": distance,
                        "duration_seconds": duration
                    }
                    route_info.append(route_data)
                
                sorted_routes = sorted(route_info, key=lambda x: x["duration_seconds"])
                
                # Store routes with generic names
                for idx, route_data in enumerate(sorted_routes):
                    routes[f"route_{idx}"] = route_data["coordinates"]
                
                return routes, route_info
        
        return None, None
        
    except Exception:
        return None, None

def generate_simulated_routes(start_coords, end_coords, travel_mode="driving"):
    """Generate simulated routes when OSRM is unavailable"""
    
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    routes = {}
    
    mode_params = {
        "driving": {"waypoints": 15, "curve_factor": 0.001},
        "walking": {"waypoints": 25, "curve_factor": 0.0015},
        "cycling": {"waypoints": 20, "curve_factor": 0.0012}
    }
    
    params = mode_params.get(travel_mode, mode_params["driving"])
    waypoints = params["waypoints"]
    
    # Generate 3 different route patterns
    for route_idx in range(3):
        route = []
        for i in range(waypoints + 1):
            progress = i / waypoints
            lat = start_lat + (end_lat - start_lat) * progress
            lon = start_lon + (end_lon - start_lon) * progress
            
            if route_idx > 0 and 0.2 <= progress <= 0.8:
                curve_factor = params["curve_factor"] * (route_idx + 1)
                lat += curve_factor * math.sin(progress * math.pi * (2 + route_idx))
                lon += curve_factor * math.cos(progress * math.pi * (1.5 + route_idx))
            
            route.append([lon, lat])
        
        routes[f"route_{route_idx}"] = route
    
    return routes

def generate_distinct_route_variants(base_route, num_variants=2, variance_factor=0.015):
    """Generate more distinct route variants that actually take different paths"""
    if not base_route or len(base_route) < 3:
        return []
    
    variants = []
    route_len = len(base_route)
    
    # Extract start and end points
    start_point = base_route[0]
    end_point = base_route[-1]
    
    for variant_idx in range(num_variants):
        variant = []
        
        for i, (lon, lat) in enumerate(base_route):
            if i == 0 or i == len(base_route) - 1:
                # Keep start and end points exactly the same
                variant.append([lon, lat])
            else:
                # Create different perturbation patterns for each variant
                progress = i / route_len
                
                # Increase variance factor for middle portions of the route
                middle_boost = 1.0 + (2.0 * (0.5 - abs(progress - 0.5)))
                
                if variant_idx == 0:
                    # Northern detour variant - creates an arc above the direct path
                    lat_offset = variance_factor * middle_boost * math.sin(progress * math.pi) * 2.5
                    lon_offset = variance_factor * middle_boost * math.cos(progress * math.pi * 2) * 0.8
                elif variant_idx == 1:
                    # Southern detour variant - creates an arc below the direct path
                    lat_offset = -variance_factor * middle_boost * math.sin(progress * math.pi) * 2.5
                    lon_offset = -variance_factor * middle_boost * math.sin(progress * math.pi * 3) * 0.8
                else:
                    # Eastern/Western zigzag variant
                    segment_num = int(progress * 5)  # Divide route into 5 segments
                    if segment_num % 2 == 0:
                        lon_offset = variance_factor * middle_boost * 2.0
                        lat_offset = variance_factor * math.sin(i * 0.3) * 0.5
                    else:
                        lon_offset = -variance_factor * middle_boost * 2.0
                        lat_offset = -variance_factor * math.sin(i * 0.3) * 0.5
                
                variant.append([lon + lon_offset, lat + lat_offset])
        
        # Smooth the variant to make it look more like a real route
        smoothed_variant = smooth_route(variant)
        variants.append(smoothed_variant)
    
    return variants

def smooth_route(route, smoothing_factor=0.3):
    """Apply smoothing to make routes look more natural"""
    if len(route) < 3:
        return route
    
    smoothed = [route[0]]  # Keep start point
    
    for i in range(1, len(route) - 1):
        prev_lon, prev_lat = route[i - 1]
        curr_lon, curr_lat = route[i]
        next_lon, next_lat = route[i + 1]
        
        # Weighted average for smoothing
        smooth_lon = (prev_lon * smoothing_factor + 
                     curr_lon * (1 - 2 * smoothing_factor) + 
                     next_lon * smoothing_factor)
        smooth_lat = (prev_lat * smoothing_factor + 
                     curr_lat * (1 - 2 * smoothing_factor) + 
                     next_lat * smoothing_factor)
        
        smoothed.append([smooth_lon, smooth_lat])
    
    smoothed.append(route[-1])  # Keep end point
    return smoothed

# ================= ROUTE OPTIMIZATION WITH VARIANTS =================
def optimize_and_select_routes(routes_dict, crime_df, start_coords, end_coords,
                               travel_mode="driving", time_of_travel="Any Time",
                               safety_priority="balanced", generate_variants=True):
    """
    Enhanced version that ensures diverse route options for balanced mode
    Now uses probabilistic model with time-of-day weighting
    """
    # Create optimizer
    optimizer = RouteOptimizer(crime_df, time_of_travel)
    
    # Set weights based on safety priority
    priority_weights = {
        "maximum_safety": (0.2, 0.8),  # 20% distance, 80% safety
        "balanced": (0.5, 0.5),         # 50% distance, 50% safety
        "speed_priority": (0.7, 0.3)    # 70% distance, 30% safety
    }
    
    alpha, beta = priority_weights.get(safety_priority, (0.5, 0.5))
    
    # For balanced mode, create different route options with different tradeoffs
    if safety_priority == "balanced" and generate_variants:
        base_routes = list(routes_dict.values())
        
        if not base_routes:
            return None
        
        # Use the first route as base
        primary_route = base_routes[0]
        
        # Generate distinct alternative routes with larger variance
        distinct_variants = generate_distinct_route_variants(
            primary_route, 
            num_variants=2, 
            variance_factor=0.025  # Increased for more distinction
        )
        
        # Prepare diverse route candidates
        route_candidates = []
        
        # Add base route
        route_candidates.append(("base", primary_route))
        
        # Add variants if available
        if distinct_variants:
            route_candidates.append(("variant_north", distinct_variants[0]))
            if len(distinct_variants) > 1:
                route_candidates.append(("variant_south", distinct_variants[1]))
        
        # Add OSRM alternatives if available
        if len(base_routes) > 1:
            route_candidates.append(("osrm_alt", base_routes[1]))
        
        # Score all candidates with DIFFERENT weight combinations to ensure diversity
        scored_routes = []
        
        # Score with safety priority (safer route)
        safety_alpha, safety_beta = 0.3, 0.7  # 30% distance, 70% safety
        
        # Score with speed priority (faster route)
        speed_alpha, speed_beta = 0.7, 0.3   # 70% distance, 30% safety
        
        # Score each route with both weight sets
        safety_best = None
        speed_best = None
        safety_best_score = float('inf')
        speed_best_score = float('inf')
        
        for route_name, route_coords in route_candidates:
            # Score with safety priority
            safety_score = optimizer.calculate_objective_function(
                route_coords, start_coords, end_coords,
                travel_mode, "09:00", safety_alpha, safety_beta
            )
            
            # Score with speed priority
            speed_score = optimizer.calculate_objective_function(
                route_coords, start_coords, end_coords,
                travel_mode, "09:00", speed_alpha, speed_beta
            )
            
            # Track best safety route
            if safety_score['objective_score'] < safety_best_score:
                safety_best_score = safety_score['objective_score']
                safety_best = (route_name, route_coords, safety_score)
            
            # Track best speed route
            if speed_score['objective_score'] < speed_best_score:
                speed_best_score = speed_score['objective_score']
                # Use the safety-weighted score for metadata to show actual risk
                actual_risk_score = optimizer.calculate_objective_function(
                    route_coords, start_coords, end_coords,
                    travel_mode, "09:00", 0.5, 0.5  # Balanced weights for display
                )
                speed_best = (route_name, route_coords, actual_risk_score)
        
        # Build result with diverse routes
        result_routes = {}
        
        # Primary route is the safer option
        if safety_best:
            _, safe_coords, safe_score = safety_best
            result_routes["primary_route"] = {
                'coordinates': safe_coords,
                'safety_level': get_safety_level_from_probability(safe_score['crime_probability_percentage'], travel_mode),
                'metadata': safe_score
            }
        
        # Alternative route is the faster option (if different from primary)
        if speed_best and safety_best:
            _, speed_coords, speed_score = speed_best
            _, safe_coords, _ = safety_best
            
            # Check if routes are actually different
            if not routes_are_similar(speed_coords, safe_coords):
                result_routes["alternative_route"] = {
                    'coordinates': speed_coords,
                    'safety_level': get_safety_level_from_probability(speed_score['crime_probability_percentage'], travel_mode),
                    'metadata': speed_score
                }
            else:
                # If they're too similar, force a variant route
                if distinct_variants:
                    variant_coords = distinct_variants[1] if len(distinct_variants) > 1 else distinct_variants[0]
                    variant_score = optimizer.calculate_objective_function(
                        variant_coords, start_coords, end_coords,
                        travel_mode, "09:00", 0.5, 0.5
                    )
                    result_routes["alternative_route"] = {
                        'coordinates': variant_coords,
                        'safety_level': get_safety_level_from_probability(variant_score['crime_probability_percentage'], travel_mode),
                        'metadata': variant_score
                    }
        
        return result_routes
    
    else:
        # For single route modes (maximum_safety or speed_priority)
        all_candidates = {}
        
        for route_name, route_coords in routes_dict.items():
            if not route_coords:
                continue
            all_candidates[route_name] = route_coords
        
        # Score all candidates with specified priority weights
        route_scores = {}
        for candidate_name, candidate_coords in all_candidates.items():
            score_data = optimizer.calculate_objective_function(
                candidate_coords, start_coords, end_coords,
                travel_mode, "09:00", alpha, beta
            )
            route_scores[candidate_name] = {
                'coordinates': candidate_coords,
                'score_data': score_data
            }
        
        if not route_scores:
            return None
        
        # Select best route based on objective score
        best_route_name = min(route_scores.keys(), 
                             key=lambda x: route_scores[x]['score_data']['objective_score'])
        best_route = route_scores[best_route_name]
        best_score_data = best_route['score_data']
        
        return {
            'single_route': {
                'coordinates': best_route['coordinates'],
                'safety_level': get_safety_level_from_probability(best_score_data['crime_probability_percentage'], travel_mode),
                'metadata': best_score_data
            }
        }

# ================= SAFETY MESSAGE GENERATION =================
def generate_safety_message(safety_level, time_of_travel, travel_mode):
    """Generate appropriate safety message based on route risk level"""
    
    if safety_level == "low":
        message = "✅ Excellent! Safe route found with low crime probability."
        message_type = "success"
    elif safety_level == "medium":
        message =  "⚠️ Route has moderate crime probability. Exercise normal caution."
        message_type = "warning"
    else:  # high
        message = "🚨 Higher crime probability detected along the route. Extra caution advised."
        message_type = "error"
    
    # Add time-specific context
    if "Night" in time_of_travel:
        if safety_level == "high":
            message += " Consider traveling during daylight hours if possible."
        elif safety_level == "medium":
            message += " Be extra vigilant during night travel."
    
    # Add mode-specific context
    if travel_mode == "walking" and safety_level != "low":
        message += " Consider alternative transportation if available."
    
    return message, message_type

# ================= ENHANCED MAP CREATION WITH MULTIPLE ROUTES =================
def create_enhanced_map(routes_data, crime_df, start_coords, end_coords, travel_mode, 
                       time_of_travel, safety_priority):
    """Create map with properly colored routes based on actual crime probability levels"""
    
    center_lat = (start_coords[0] + end_coords[0]) / 2
    center_lon = (start_coords[1] + end_coords[1]) / 2
    
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=12,
        prefer_canvas=True
    )
    
    folium.TileLayer(
        tiles='OpenStreetMap',
        name='Street Map',
        overlay=False,
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://carto.com/attributions">CARTO</a>',
        name='Satellite-like',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Filter crimes for display based on time
    display_crime_df = crime_df.copy()
    
    if time_of_travel != "Any Time":
        time_mapping = {
            "Morning (6-12)": "Morning",
            "Afternoon (12-16)": "Afternoon",
            "Evening (16-18)": "Evening",
            "Night (18-6)": "Night"
        }
        target_time = time_mapping.get(time_of_travel)
        if target_time:
            display_crime_df = display_crime_df[display_crime_df['Time of Day'] == target_time]
    
    # Add crime visualization
    if not display_crime_df.empty:
        crime_layer = folium.FeatureGroup(name=f"Crime Risk Zones ({time_of_travel})", show=True)
        
        max_crime_points = 400
        if len(display_crime_df) > max_crime_points:
            crime_sample = display_crime_df.sample(n=max_crime_points, random_state=42)
        else:
            crime_sample = display_crime_df
        
        crime_colors = {0: '#FF0000', 1: '#FFA500', 2: '#00FF00'}
        crime_names = {0: 'High Crime Risk', 1: 'Medium Crime Risk', 2: 'Low Crime Risk'}
        
        for _, row in crime_sample.iterrows():
            cluster = row.get('Cluster', 1)
            color = crime_colors.get(cluster, '#FFA500')
            
            folium.CircleMarker(
                location=(row['LAT'], row['LON']),
                radius=3,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=1,
                popup=f"<b>{crime_names.get(cluster)}</b><br>Area: {row.get('AREA NAME', 'Unknown')}"
            ).add_to(crime_layer)
        
        crime_layer.add_to(m)
    
    # Route colors based on ACTUAL crime probability levels  
    def get_route_color(crime_probability_percentage, travel_mode):
        """Get route color based on actual crime probability percentage"""
        thresholds = {
            "driving": {"low": 2.0, "medium": 8.0},
            "cycling": {"low": 3.0, "medium": 12.0},  
            "walking": {"low": 4.0, "medium": 15.0}
        }
        
        mode_thresholds = thresholds.get(travel_mode, thresholds["driving"])
        
        if crime_probability_percentage < mode_thresholds["low"]:
            return "#00AA00"  # Green - Low probability
        elif crime_probability_percentage < mode_thresholds["medium"]:
            return "#FF8C00"  # Orange - Medium probability
        else:
            return "#DC143C"  # Red - High probability
    
    # Add routes to map
    if routes_data:
        route_names_display = {
            "single_route": "Optimized Route",
            "primary_route": "Primary Route (Recommended)",
            "alternative_route": "Alternative Route (Faster)"
        }
        
        # Check if it's single or multiple routes
        if 'single_route' in routes_data:
            # Single route mode
            route_info = routes_data['single_route']
            route_coords = route_info['coordinates']
            metadata = route_info['metadata']
            crime_probability = metadata.get('crime_probability_percentage', 0)
            
            # Get color based on actual probability
            route_color = get_route_color(crime_probability, travel_mode)
            route_points = [[lat, lon] for lon, lat in route_coords]
            
            # Create popup text with probabilistic information
            popup_text = f"<b>Optimized Route</b><br>"
            popup_text += f"Distance: {metadata.get('route_distance_km', 0):.1f} km<br>"
            popup_text += f"Time: {metadata.get('route_time_minutes', 0):.0f} min<br>"
            popup_text += f"Crime Probability: {crime_probability:.1f}%<br>"
            popup_text += f"Confidence: {metadata.get('probability_confidence_interval', 'N/A')}<br>"
            popup_text += f"Safety Level: {route_info['safety_level'].title()}"
            
            folium.PolyLine(
                route_points,
                color=route_color,
                weight=6,
                opacity=0.9,
                popup=popup_text
            ).add_to(m)
            
        else:
            # Multiple routes mode - Draw ALL routes
            route_count = 0
            for route_key, route_info in routes_data.items():
                route_coords = route_info['coordinates']
                metadata = route_info['metadata']
                crime_probability = metadata.get('crime_probability_percentage', 0)
                
                # Get color based on actual probability
                route_color = get_route_color(crime_probability, travel_mode)
                route_points = [[lat, lon] for lon, lat in route_coords]
                
                # Different styling for primary vs alternative
                if route_key == "primary_route":
                    weight = 7
                    opacity = 0.9
                    dash_array = None
                else:
                    weight = 5
                    opacity = 0.7
                    dash_array = '10, 5'  # Dashed line for alternative
                
                # Create popup text with probabilistic information
                route_name = route_names_display.get(route_key, f"Route {route_count + 1}")
                popup_text = f"<b>{route_name}</b><br>"
                popup_text += f"Distance: {metadata.get('route_distance_km', 0):.1f} km<br>"
                popup_text += f"Time: {metadata.get('route_time_minutes', 0):.0f} min<br>"
                popup_text += f"Crime Probability: {crime_probability:.1f}%<br>"
                popup_text += f"Confidence: {metadata.get('probability_confidence_interval', 'N/A')}<br>"
                popup_text += f"Safety Level: {route_info['safety_level'].title()}"
                
                # Add route to map
                route_line = folium.PolyLine(
                    route_points,
                    color=route_color,
                    weight=weight,
                    opacity=opacity,
                    popup=popup_text,
                    dash_array=dash_array
                )
                route_line.add_to(m)
                
                # Add route markers for distinction
                if len(route_points) > 10:
                    # Add a small marker at the midpoint
                    mid_idx = len(route_points) // 2
                    mid_point = route_points[mid_idx]
                    
                    icon_html = f"""
                    <div style="
                        background-color: {route_color};
                        color: white;
                        border-radius: 50%;
                        width: 20px;
                        height: 20px;
                        text-align: center;
                        font-weight: bold;
                        font-size: 12px;
                        line-height: 20px;
                        border: 2px solid white;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    ">{route_count + 1}</div>
                    """
                    
                    folium.Marker(
                        location=mid_point,
                        icon=folium.DivIcon(html=icon_html),
                        popup=popup_text
                    ).add_to(m)
                
                route_count += 1
    
    # Add start/end markers
    mode_icons = {
        "driving": "car",
        "walking": "walking",
        "cycling": "bicycle"
    }
    
    icon_name = mode_icons.get(travel_mode, "location-arrow")
    
    folium.Marker(
        location=start_coords,
        popup=f"<b>🏁 Start</b><br>Travel Mode: {travel_mode.title()}",
        icon=folium.Icon(color='green', icon=icon_name, prefix='fa'),
        zindex=1000
    ).add_to(m)
    
    folium.Marker(
        location=end_coords,
        popup=f"<b>🎯 Destination</b><br>Mode: {travel_mode.title()}",
        icon=folium.Icon(color='red', icon='flag', prefix='fa'),
        zindex=1000
    ).add_to(m)
    
    # Enhanced legend with probabilistic information
    prob_thresholds = {
        "driving": {"low": 2, "medium": 8},
        "cycling": {"low": 3, "medium": 12},
        "walking": {"low": 4, "medium": 15}
    }
    
    mode_thresh = prob_thresholds.get(travel_mode, prob_thresholds["driving"])
    
    legend_html = f'''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 320px; height: auto; 
                background: white; border: 2px solid #ccc; z-index:9999; 
                font-size: 13px; padding: 12px; border-radius: 8px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
    <p style="margin: 0 0 10px 0; font-weight: bold; color: #333;">🗺️ Smart Route - {travel_mode.title()}</p>
    <p style="margin: 2px 0; font-size: 11px;"><b>Time:</b> {time_of_travel}</p>
    <p style="margin: 2px 0; font-size: 11px;"><b>Priority:</b> {safety_priority.replace('_', ' ').title()}</p>
    <hr style="margin: 8px 0; border: 1px solid #eee;">
    <p style="margin: 0 0 6px 0; font-weight: bold; color: #333;">🚨 Crime Risk Zones:</p>
    <p style="margin: 2px 0;"><span style="color:#FF0000; font-size: 14px;">●</span> High Crime Risk</p>
    <p style="margin: 2px 0;"><span style="color:#FFA500; font-size: 14px;">●</span> Medium Crime Risk</p>
    <p style="margin: 2px 0;"><span style="color:#00FF00; font-size: 14px;">●</span> Low Crime Risk</p>
    <hr style="margin: 8px 0; border: 1px solid #eee;">
    <p style="margin: 0 0 6px 0; font-weight: bold; color: #333;">🛣️ Route Crime Probability:</p>
    <p style="margin: 2px 0;"><span style="color:#00AA00; font-weight: bold;">━━</span> Low Risk (&lt;{mode_thresh["low"]}% chance)</p>
    <p style="margin: 2px 0;"><span style="color:#FF8C00; font-weight: bold;">━━</span> Medium Risk ({mode_thresh["low"]}-{mode_thresh["medium"]}% chance)</p>
    <p style="margin: 2px 0;"><span style="color:#DC143C; font-weight: bold;">━━</span> High Risk (&gt;{mode_thresh["medium"]}% chance)</p>'''
    
    # Add route type explanation if multiple routes
    if 'primary_route' in routes_data:
        legend_html += '''
    <hr style="margin: 8px 0; border: 1px solid #eee;">
    <p style="margin: 0 0 6px 0; font-weight: bold; color: #333;">📍 Route Types:</p>
    <p style="margin: 2px 0;"><span style="font-weight: bold;">━━━</span> Primary (Solid)</p>
    <p style="margin: 2px 0;"><span style="font-weight: bold;">┅┅┅</span> Alternative (Dashed)</p>'''
    
    legend_html += '</div>'
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    folium.LayerControl(position='topleft').add_to(m)
    
    return m

# ================= MAIN COMPUTATION FUNCTION =================
def compute_and_display_safe_route(start_area, end_area, travel_mode="driving", 
                                  force_safe_route=False, api_keys=None, 
                                  safety_priority="balanced", time_of_travel="Any Time"):
    """Enhanced route computation with probabilistic crime model"""
    
    try:
        # Load FULL crime data (no time filtering for areas)
        full_crime_df = load_crime_data_for_areas()
        if full_crime_df is None:
            st.error("Could not load crime data")
            return False
        
        # Get FIXED area coordinates
        area_coords = get_area_coordinates(full_crime_df)
        
        if start_area not in area_coords or end_area not in area_coords:
            st.error(f"Area coordinates not found for {start_area} or {end_area}")
            return False
        
        # Use fixed coordinates
        start_coords_dict = area_coords[start_area]
        end_coords_dict = area_coords[end_area]
        start_lat, start_lon = start_coords_dict['lat'], start_coords_dict['lon']
        end_lat, end_lon = end_coords_dict['lat'], end_coords_dict['lon']
        
        # Get base routes from OSRM
        routes, route_info = get_free_osrm_routes((start_lat, start_lon), (end_lat, end_lon), travel_mode)
        
        # Fallback to simulated routes if OSRM fails
        if routes is None:
            routes = generate_simulated_routes((start_lat, start_lon), (end_lat, end_lon), travel_mode)
            route_info = None
        
        # Optimize and select routes based on safety_priority
        optimized_routes = optimize_and_select_routes(
            routes, full_crime_df, 
            (start_lat, start_lon), (end_lat, end_lon),
            travel_mode, time_of_travel, safety_priority
        )
        
        if optimized_routes is None:
            st.error("Could not generate optimized route")
            return False
        
        # Generate and display safety message based on routes using probabilistic model
        if safety_priority == "balanced" and len(optimized_routes) > 1:
            # For balanced mode with multiple routes
            safety_levels = []
            probabilities = []
            for route_key, route_info in optimized_routes.items():
                safety_levels.append(route_info['safety_level'])
                probabilities.append(route_info['metadata']['crime_probability_percentage'])
            
            # Message based on the range of options available
            if "low" in safety_levels and "high" in safety_levels:
                message = "ℹ️ Multiple route options available. Green route has lowest crime probability, red route is faster but riskier."
                message_type = "info"
            elif "low" in safety_levels:
                message = "✅ Safe routes available with low crime probabilities. Choose based on your preferences."
                message_type = "success"
            elif "high" in safety_levels:
                message = "⚠️ Routes have elevated crime probabilities. Consider the safer option if possible."
                message_type = "warning"
            else:
                message = "ℹ️ Route options analyzed. Review the crime probabilities below."
                message_type = "info"
        else:
            # For single route modes
            route_info = optimized_routes.get('single_route', list(optimized_routes.values())[0])
            safety_level = route_info['safety_level']
            crime_probability = route_info['metadata']['crime_probability_percentage']
            
            if safety_level == "low":
                message = f"✅ Excellent! Safe route found with {crime_probability:.1f}% crime probability."
                message_type = "success"
            elif safety_level == "medium":
                message = f"⚠️ Route has {crime_probability:.1f}% crime probability. Exercise normal caution."
                message_type = "warning"
            else:
                message = f"🚨 Route has {crime_probability:.1f}% crime probability. Extra caution advised."
                message_type = "error"
            
            # Add context for safety priority
            if safety_priority == "maximum_safety" and safety_level != "low":
                message += " This is the safest available route given current conditions."
            elif safety_priority == "speed_priority":
                message += " This is the fastest route to your destination."
        
        # Display safety message
        if message_type == "success":
            st.success(message)
        elif message_type == "warning":
            st.warning(message)
        elif message_type == "error":
            st.error(message)
        else:
            st.info(message)
        
        # Create and display map
        map_obj = create_enhanced_map(
            optimized_routes, full_crime_df, 
            (start_lat, start_lon), (end_lat, end_lon), 
            travel_mode, time_of_travel, safety_priority
        )
        
        st_folium(map_obj, width=900, height=600, returned_objects=[])
        
        # Display travel time and distance with probabilistic information
        st.markdown("### ⏱️ Travel Time & Crime Probability")
        
        if safety_priority == "balanced" and len(optimized_routes) > 1:
            # Show comparison for multiple routes
            cols = st.columns(len(optimized_routes))
            
            for idx, (route_key, route_info) in enumerate(optimized_routes.items()):
                metadata = route_info['metadata']
                with cols[idx]:
                    if idx == 0:
                        route_name = "Primary Route"
                    else:
                        route_name = "Alternative Route"
                    
                    st.metric(
                        label=route_name,
                        value=f"{metadata['route_time_minutes']:.0f} min",
                        delta=f"{metadata['route_distance_km']:.1f} km"
                    )
                    st.write(f"Crime Probability: {metadata['crime_probability_percentage']:.1f}%")
                    st.caption(f"Confidence: {metadata.get('probability_confidence_interval', 'N/A')}")
        else:
            # Single route display
            route_info = optimized_routes.get('single_route', list(optimized_routes.values())[0])
            metadata = route_info['metadata']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Distance",
                    value=f"{metadata['route_distance_km']:.1f} km"
                )
            
            with col2:
                st.metric(
                    label="Travel Time",
                    value=f"{metadata['route_time_minutes']:.0f} min"
                )
            
            with col3:
                st.metric(
                    label="Crime Probability",
                    value=f"{metadata['crime_probability_percentage']:.1f}%"
                )
                st.caption(f"95% CI: {metadata.get('probability_confidence_interval', 'N/A')}")
        
        # Route Safety Information with Probabilistic Analysis
        st.markdown("### 🛡️ Route Safety Analysis")
        
        # Generate specific safety message based on routes
        if safety_priority == "balanced" and len(optimized_routes) > 1:
            # Message for multiple routes with probabilistic interpretation
            primary_route = list(optimized_routes.values())[0]
            crime_probability = primary_route['metadata']['crime_probability_percentage']
            confidence_interval = primary_route['metadata'].get('probability_confidence_interval', 'N/A')
            
            st.info(f"📊 **Route Comparison Available**: The primary route has {crime_probability:.1f}% crime probability "
                   f"(95% confidence: {confidence_interval}). "
                   f"Alternative routes are shown for comparison. Choose based on your risk tolerance.")
            
            # Show comparison table with probabilistic data
            comparison_data = []
            for idx, (route_key, route_info) in enumerate(optimized_routes.items()):
                metadata = route_info['metadata']
                safety_level = route_info['safety_level']
                
                route_name = "Primary" if idx == 0 else "Alternative"
                emoji = "🟢" if safety_level == "low" else "🟡" if safety_level == "medium" else "🔴"
                
                comparison_data.append({
                    'Route': f"{emoji} {route_name}",
                    'Distance': f"{metadata['route_distance_km']:.1f} km",
                    'Time': f"{metadata['route_time_minutes']:.0f} min",
                    'Crime Probability': f"{metadata['crime_probability_percentage']:.1f}%",
                    'Confidence Interval': metadata.get('probability_confidence_interval', 'N/A'),
                    'Safety Level': safety_level.title()
                })
            
            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True)
            
        else:
            # Single route message with probabilistic interpretation
            route_info = optimized_routes.get('single_route', list(optimized_routes.values())[0])
            crime_probability = route_info['metadata']['crime_probability_percentage']
            confidence_interval = route_info['metadata'].get('probability_confidence_interval', 'N/A')
            journey_time = route_info['metadata']['route_time_minutes']
            
            # Interpret crime probability in user-friendly terms
            if crime_probability < 1:
                emoji = "✅"
                risk_interpretation = "extremely low"
                freq_interpretation = f"Less than 1 incident expected per 100 similar trips"
            elif crime_probability < 3:
                emoji = "✅"
                risk_interpretation = "very low"
                freq_interpretation = f"About {crime_probability:.1f} incidents expected per 100 similar trips"
            elif crime_probability < 8:
                emoji = "⚠️"
                risk_interpretation = "low to moderate"
                freq_interpretation = f"About {crime_probability:.1f} incidents expected per 100 similar trips"
            elif crime_probability < 15:
                emoji = "⚠️"
                risk_interpretation = "moderate"
                freq_interpretation = f"About {int(crime_probability)} incidents expected per 100 similar trips"
            else:
                emoji = "🚨"
                risk_interpretation = "elevated"
                freq_interpretation = f"About {int(crime_probability)} incidents expected per 100 similar trips"
            
            safety_info = f"{emoji} **Crime Probability Analysis**: This route has a **{crime_probability:.1f}% probability** "
            safety_info += f"of crime encounter during your {journey_time:.0f}-minute journey ({risk_interpretation} risk)."
            
            # Add confidence interval information
            if confidence_interval != 'N/A':
                safety_info += f" **Statistical confidence**: {confidence_interval} (95% confidence interval)."
            
            # Add frequency interpretation
            safety_info += f" **Practical meaning**: {freq_interpretation}."
            
            if "✅" in safety_info:
                st.success(safety_info)
            elif "⚠️" in safety_info:
                st.warning(safety_info)
            else:
                st.error(safety_info)
        
        # Probabilistic Model Information
        st.markdown("### 📊 Understanding Crime Probabilities")
        
        with st.expander("🔍 How Crime Probabilities Are Calculated"):
            st.write("**Probabilistic Crime Model**: Our system uses advanced statistical methods to convert historical crime data into meaningful probabilities.")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**What the probability means:**")
                st.write("• Based on historical crime patterns in the area")
                st.write("• Accounts for your travel mode vulnerability")  
                st.write("• Includes journey time and route-specific factors")
                st.write("• Shows likelihood of encountering any crime incident")
                
            with col2:
                st.write("**Confidence intervals:**")
                st.write("• 95% confidence bounds around probability estimate")
                st.write("• Accounts for uncertainty in historical data")
                st.write("• Wider intervals = less certain estimates")
                st.write("• Based on 3+ years of crime data")
        
        # Route Safety Guide with Probabilistic Thresholds
        st.markdown("### 📈 Probabilistic Safety Guide")
        
        # Get mode-specific thresholds
        prob_thresholds = {
            "driving": {"low": 2.0, "medium": 8.0},
            "cycling": {"low": 3.0, "medium": 12.0},
            "walking": {"low": 4.0, "medium": 15.0}
        }
        
        mode_thresh = prob_thresholds.get(travel_mode, prob_thresholds["driving"])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success(f"**🟢 Low Risk Routes**\nCrime probability <{mode_thresh['low']:.0f}%\n(Very safe for {travel_mode})")
        with col2:
            st.warning(f"**🟡 Moderate Risk Routes**\nCrime probability {mode_thresh['low']:.0f}-{mode_thresh['medium']:.0f}%\n(Exercise normal caution)")
        with col3:
            st.error(f"**🔴 Higher Risk Routes**\nCrime probability >{mode_thresh['medium']:.0f}%\n(Extra precautions advised)")
        
        # Safety tips
        st.markdown(f"### 🛡️ Safety Tips for {travel_mode.title()} Travel")
        
        if "Night" in time_of_travel:
            st.warning(f"🌙 **Night Travel**: Be extra vigilant during night hours.")
        elif "Evening" in time_of_travel:
            st.info(f"🌆 **Evening Travel**: Be extra vigilant during evening hours.")
        elif "Morning" in time_of_travel:
            st.success(f"☀️ **Morning Travel**: Generally safest time period for travel.")
        
        mode_tips = {
            "driving": [
                "🚗 Keep vehicle doors locked at all times",
                "⛽ Plan fuel stops in well-lit, busy areas",
                "📱 Use hands-free navigation to stay focused",
                "🚨 If you feel unsafe, drive to the nearest police station"
            ],
            "walking": [
                "👥 Walk with companions when possible",
                "🔦 Carry a flashlight for evening walks",
                "📱 Share your route and ETA with someone you trust",
                "👀 Stay alert and avoid distractions like headphones"
            ],
            "cycling": [
                "🚴‍♂️ Wear bright, reflective clothing for visibility",
                "🛡️ Always wear a properly fitted helmet",
                "🚲 Use designated bike lanes when available",
                "💡 Use front and rear lights during low visibility conditions"
            ]
        }
        
        tips = mode_tips.get(travel_mode, mode_tips["driving"])
        for tip in tips:
            st.write(f"- {tip}")
        
        return True
        
    except Exception as e:
        st.error(f"Error generating routes: {str(e)}")
        return False

# ================= HELPER FUNCTIONS =================
@st.cache_data
def get_peak_crime_time_from_data(crime_df):
    """Get peak crime time from overall crime data"""
    try:
        if 'Time of Day' not in crime_df.columns:
            return "Unknown"
        
        if len(crime_df) > 1000:
            sample_df = crime_df.sample(n=1000, random_state=42)
        else:
            sample_df = crime_df
        
        time_counts = sample_df['Time of Day'].value_counts()
        if not time_counts.empty:
            return time_counts.index[0]
        
        return "Unknown"
    except Exception:
        return "Unknown"

def get_system_info():
    """Get information about the enhanced routing system"""
    return {
        "status": "Active",
        "version": "4.0 - Probabilistic Model with Time-of-Day Analysis"
    }
