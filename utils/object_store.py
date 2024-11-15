import json
import os
from datetime import datetime, time, timezone
from typing import List, Dict, Any
import streamlit as st

class ObjectStore:
    def __init__(self):
        self.storage_file = 'schedules.json'
        if 'persist_schedules' not in st.session_state:
            st.session_state.persist_schedules = self._load_from_file()
    
    def _load_from_file(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    schedules = json.load(f)
                    # Convert string dates back to datetime with proper timezone handling
                    for s in schedules:
                        try:
                            s['start_time'] = datetime.fromisoformat(s['start_time'])
                        except (ValueError, TypeError):
                            # Handle invalid datetime strings or None values
                            continue
                    return [s for s in schedules if s.get('start_time')]  # Filter out invalid entries
            except Exception as e:
                print(f"Error loading schedules: {str(e)}")
                return []
        return []
    
    def _save_to_file(self) -> None:
        try:
            schedules = st.session_state.persist_schedules
            # Convert datetime to string for JSON serialization with proper timezone handling
            serializable_schedules = []
            for s in schedules:
                if s.get('start_time'):
                    s_copy = s.copy()
                    if isinstance(s_copy['start_time'], datetime):
                        s_copy['start_time'] = s_copy['start_time'].isoformat()
                    serializable_schedules.append(s_copy)
            
            with open(self.storage_file, 'w') as f:
                json.dump(serializable_schedules, f, indent=2)
        except Exception as e:
            print(f"Error saving schedules: {str(e)}")
    
    def save_schedule(self, schedule: Dict[str, Any]) -> None:
        try:
            if isinstance(schedule['start_time'], time):
                today = datetime.now(timezone.utc).date()
                schedule['start_time'] = datetime.combine(today, schedule['start_time'])
            elif not isinstance(schedule['start_time'], datetime):
                raise ValueError("Invalid start_time format")
                
            st.session_state.persist_schedules.append(schedule)
            self._save_to_file()
        except Exception as e:
            print(f"Error saving schedule: {str(e)}")
            raise
    
    def load_schedules(self) -> List[Dict[str, Any]]:
        current_date = datetime.now(timezone.utc).date()
        return [s for s in st.session_state.persist_schedules 
                if isinstance(s.get('start_time'), datetime) 
                and s['start_time'].date() >= current_date]
    
    def clear_schedules(self) -> None:
        st.session_state.persist_schedules = []
        if os.path.exists(self.storage_file):
            try:
                os.remove(self.storage_file)
            except Exception as e:
                print(f"Error clearing schedules: {str(e)}")
