from datetime import datetime
from typing import List, Dict, Any
import streamlit as st

class ObjectStore:
    def __init__(self):
        if 'schedules' not in st.session_state:
            st.session_state.schedules = []
    
    def save_schedule(self, schedule: Dict[str, Any]) -> None:
        if isinstance(schedule['start_time'], datetime.time):  # Compare directly with datetime.time
            today = datetime.today().date()
            schedule['start_time'] = datetime.combine(today, schedule['start_time'])
        st.session_state.schedules.append(schedule)
    
    def load_schedules(self) -> List[Dict[str, Any]]:
        return [s for s in st.session_state.schedules 
                if isinstance(s['start_time'], datetime) 
                and s['start_time'].date() >= datetime.now().date()]
    
    def clear_schedules(self) -> None:
        st.session_state.schedules = []
