from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
import os


class UniversalDataStore:
    """In-memory storage for universal dataset with uniform structure"""
    
    def __init__(self, excel_file_path: str = "outputs/universal_dataset.xlsx"):
        # Store uniform records with required fields
        self._data: List[Dict[str, Any]] = []
        self.excel_file_path = excel_file_path
        # Create outputs directory if it doesn't exist
        os.makedirs(os.path.dirname(excel_file_path), exist_ok=True)
    
    def add_uniform_record(self, 
                          client_code: str = None,
                          transcript: str = None,
                          lead_data: str = None,
                          latest_message: str = None,
                          expected_output: str = None,
                          source: str = "unknown"):
        """Add a single uniform record to the universal dataset"""
        entry = {
            "id": len(self._data) + 1,
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "client_code": client_code,
            "transcript": transcript,
            "lead_data": lead_data,
            "latest_message": latest_message,
            "expected_output": expected_output
        }
        self._data.append(entry)
        # Update Excel file after adding record
        self._update_excel_file()
    
    def add_uniform_records(self, records: List[Dict[str, Any]], source: str = "unknown"):
        """Add multiple uniform records to the universal dataset"""
        for record in records:
            self.add_uniform_record(
                client_code=record.get("client_code"),
                transcript=record.get("transcript"),
                lead_data=record.get("lead_data"),
                latest_message=record.get("latest_message"),
                expected_output=record.get("expected_output"),
                source=source
            )
    
    def get_all_data(self) -> List[Dict[str, Any]]:
        """Retrieve all data from the universal dataset"""
        return self._data
    
    def get_data_count(self) -> int:
        """Get total number of records"""
        return len(self._data)
    
    def clear_data(self):
        """Clear all data from the universal dataset"""
        self._data = []
        # Clear Excel file
        if os.path.exists(self.excel_file_path):
            os.remove(self.excel_file_path)
    
    def _update_excel_file(self):
        """Update the Excel file with current data"""
        if self._data:
            df = pd.DataFrame(self._data)
            df.to_excel(self.excel_file_path, index=False, engine='openpyxl')
    
    def get_excel_file_path(self) -> str:
        """Get the path to the Excel file"""
        return self.excel_file_path


# Global instance of the data store
universal_data_store = UniversalDataStore()

