import json
import os
from datetime import datetime, time, timezone
from typing import List, Dict, Any
import streamlit as st
from utils.battery_profiles import BatteryProfile


class ObjectStore:

    def __init__(self):
        self.schedule_file = '.DB/schedules.json'
        self.profile_file = '.DB/battery_profiles.json'

        # Initialize session state for schedules
        if 'persist_schedules' not in st.session_state:
            try:
                st.session_state.persist_schedules = self._load_schedules()
            except Exception as e:
                print(f"Error initializing schedules: {str(e)}")
                st.session_state.persist_schedules = []

        # Initialize session state for profiles
        if 'profiles' not in st.session_state:
            st.session_state.profiles = {}
            try:
                loaded_profiles = self._load_profiles()
                for name, profile_data in loaded_profiles.items():
                    # Convert monthly_distribution keys to integers
                    if 'monthly_distribution' in profile_data:
                        profile_data['monthly_distribution'] = {
                            int(k): v
                            for k, v in
                            profile_data['monthly_distribution'].items()
                        }
                    profile = BatteryProfile(**profile_data)
                    st.session_state.profiles[name] = profile
            except Exception as e:
                print(f"Error loading profiles: {str(e)}")

            if not st.session_state.profiles:
                # Create default profile if none exists
                monthly_distribution = {
                    int(k): v
                    for k, v in {
                        1: 1.2,
                        2: 1.15,
                        3: 1.0,
                        4: 0.9,
                        5: 0.5,
                        6: 0.4,
                        7: 0.4,
                        8: 0.5,
                        9: 0.7,
                        10: 0.9,
                        11: 1.0,
                        12: 1.15
                    }.items()
                }
                default_profile = BatteryProfile(
                    name="Home Battery",
                    capacity=20.0,
                    empty_soc=0.1,
                    min_soc=0.2,
                    max_soc=0.9,
                    charge_rate=12,
                    daily_consumption=15.0,
                    usage_pattern="Flat",
                    yearly_consumption=3475.0,
                    monthly_distribution=monthly_distribution,
                    surcharge_rate=0.025,
                    max_daily_cycles=1.5,
                    max_charge_events=2,
                    max_discharge_events=1)
                self.save_profile(default_profile)

    def _load_schedules(self) -> List[Dict[str, Any]]:
        """Load schedules from file with proper timezone handling"""
        if os.path.exists(self.schedule_file):
            try:
                with open(self.schedule_file, 'r') as f:
                    schedules = json.load(f)
                    # Convert string dates back to datetime with UTC timezone
                    for s in schedules:
                        try:
                            if isinstance(s.get('start_time'), str):
                                dt = datetime.fromisoformat(
                                    s['start_time'].replace('Z', '+00:00'))
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=timezone.utc)
                                s['start_time'] = dt
                        except (ValueError, TypeError) as e:
                            print(f"Error parsing schedule date: {str(e)}")
                            continue

                    # Filter out expired and invalid schedules
                    current_date = datetime.now(timezone.utc).date()
                    valid_schedules = []
                    for s in schedules:
                        if (isinstance(s.get('start_time'), datetime)
                                and s['start_time'].date() >= current_date
                                and isinstance(s.get('power'), (int, float))
                                and isinstance(s.get('duration'), (int, float))
                                and isinstance(s.get('operation'), str)):
                            valid_schedules.append(s)
                    return valid_schedules
            except Exception as e:
                print(f"Error loading schedules: {str(e)}")
                return []
        return []

    def _save_schedules(self) -> bool:
        """Save schedules to file with proper timezone handling"""
        try:
            schedules = st.session_state.persist_schedules
            serializable_schedules = []

            for s in schedules:
                if isinstance(s.get('start_time'), (datetime, time)):
                    s_copy = s.copy()
                    if isinstance(s_copy['start_time'], datetime):
                        # Ensure timezone information is preserved
                        if s_copy['start_time'].tzinfo is None:
                            s_copy['start_time'] = s_copy[
                                'start_time'].replace(tzinfo=timezone.utc)
                        s_copy['start_time'] = s_copy['start_time'].isoformat()
                    serializable_schedules.append(s_copy)

            os.makedirs(os.path.dirname(self.schedule_file), exist_ok=True)
            with open(self.schedule_file, 'w') as f:
                json.dump(serializable_schedules, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving schedules: {str(e)}")
            return False

    def _load_profiles(self) -> Dict[str, Any]:
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading profiles: {str(e)}")
                return {}
        return {}

    def save_profile(self, profile: BatteryProfile) -> None:
        if 'profiles' not in st.session_state:
            st.session_state.profiles = {}
        st.session_state.profiles[profile.name] = profile
        self._save_profiles_to_file()

    def remove_profile(self, profile_name: str) -> None:
        if 'profiles' in st.session_state and profile_name in st.session_state.profiles:
            del st.session_state.profiles[profile_name]
            self._save_profiles_to_file()

    def get_profile(self, name: str) -> BatteryProfile:
        return st.session_state.profiles.get(name)

    def list_profiles(self) -> List[str]:
        return list(st.session_state.profiles.keys()
                    ) if 'profiles' in st.session_state else []

    def _save_profiles_to_file(self) -> None:
        try:
            profiles_data = {}
            for name, profile in st.session_state.profiles.items():
                # Ensure monthly_distribution has integer keys
                monthly_distribution = {
                    int(k): v
                    for k, v in profile.monthly_distribution.items()
                }
                profiles_data[name] = {
                    'name': profile.name,
                    'capacity': profile.capacity,
                    'empty_soc': profile.empty_soc,
                    'min_soc': profile.min_soc,
                    'max_soc': profile.max_soc,
                    'charge_rate': profile.charge_rate,
                    'daily_consumption': profile.daily_consumption,
                    'usage_pattern': profile.usage_pattern,
                    'yearly_consumption': profile.yearly_consumption,
                    'monthly_distribution': monthly_distribution,
                    'surcharge_rate': profile.surcharge_rate,
                    'max_daily_cycles': profile.max_daily_cycles,
                    'max_charge_events': profile.max_charge_events,
                    'max_discharge_events': profile.max_discharge_events
                }

            os.makedirs(os.path.dirname(self.profile_file), exist_ok=True)
            with open(self.profile_file, 'w') as f:
                json.dump(profiles_data, f, indent=2)
        except Exception as e:
            print(f"Error saving profiles: {str(e)}")

    def save_schedule(self, schedule: Dict[str, Any]) -> None:
        """Save a new schedule with proper timezone handling and validation"""
        try:
            # Validate schedule data
            if not all(
                    k in schedule
                    for k in ['operation', 'power', 'start_time', 'duration']):
                raise ValueError(
                    "Invalid schedule format: missing required fields")

            # Validate data types
            if not isinstance(schedule.get('power'), (int, float)):
                raise ValueError("Power must be a number")
            if not isinstance(schedule.get('duration'), (int, float)):
                raise ValueError("Duration must be a number")
            if not isinstance(schedule.get('operation'), str):
                raise ValueError("Operation must be a string")

            # Handle time conversion
            if isinstance(schedule['start_time'], time):
                today = datetime.now(timezone.utc).date()
                schedule['start_time'] = datetime.combine(
                    today, schedule['start_time'])

            # Ensure datetime has timezone information
            if isinstance(schedule['start_time'], datetime):
                if schedule['start_time'].tzinfo is None:
                    schedule['start_time'] = schedule['start_time'].replace(
                        tzinfo=timezone.utc)
            else:
                raise ValueError("Invalid start_time format")

            # Initialize persist_schedules if not exists
            if 'persist_schedules' not in st.session_state:
                st.session_state.persist_schedules = []

            # Ensure numeric values are of correct type
            schedule['power'] = float(schedule['power'])
            schedule['duration'] = int(schedule['duration'])

            # Add status if not present
            if 'status' not in schedule:
                schedule['status'] = 'scheduled'

            # Add schedule and save
            st.session_state.persist_schedules.append(schedule)
            if not self._save_schedules():
                raise ValueError("Failed to save schedule to file")

        except Exception as e:
            print(f"Error saving schedule: {str(e)}")
            raise

    def remove_schedule(self, index: int) -> bool:
        """Remove a schedule by index with enhanced error handling and validation"""
        try:
            # Ensure schedules are loaded
            if 'persist_schedules' not in st.session_state:
                st.session_state.persist_schedules = self._load_schedules()
            
            # Validate index
            if not isinstance(index, int):
                print(f"Invalid index type: {type(index)}")
                return False
                
            # Check if index is within bounds
            if index < 0 or index >= len(st.session_state.persist_schedules):
                print(f"Index out of range: {index}")
                return False
                
            # Remove the schedule
            removed_schedule = st.session_state.persist_schedules.pop(index)
            print(f"Removed schedule: {removed_schedule}")
            
            # Save updated schedules
            if not self._save_schedules():
                print("Failed to save schedules after removal")
                # Revert the removal if save fails
                st.session_state.persist_schedules.insert(index, removed_schedule)
                return False
                
            return True
            
        except Exception as e:
            print(f"Error removing schedule: {str(e)}")
            return False

    def load_schedules(self) -> List[Dict[str, Any]]:
        """Load and return active schedules"""
        if 'persist_schedules' not in st.session_state:
            st.session_state.persist_schedules = self._load_schedules()

        # Validate and filter schedules
        current_date = datetime.now(timezone.utc).date()
        valid_schedules = []
        for s in st.session_state.persist_schedules:
            if (isinstance(s.get('start_time'), datetime)
                    and s['start_time'].date() >= current_date
                    and isinstance(s.get('power'), (int, float))
                    and isinstance(s.get('duration'), (int, float))
                    and isinstance(s.get('operation'), str)):
                valid_schedules.append(s)

        st.session_state.persist_schedules = valid_schedules
        return valid_schedules

    def clear_schedules(self) -> None:
        """Clear all schedules"""
        st.session_state.persist_schedules = []
        if os.path.exists(self.schedule_file):
            try:
                os.remove(self.schedule_file)
            except Exception as e:
                print(f"Error clearing schedules: {str(e)}")
