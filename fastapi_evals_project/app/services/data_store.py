from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
import os
from pymongo import MongoClient
import certifi
import uuid
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI", "")
mongo_db_name = os.getenv("MONGO_DB_NAME", "")
mongo_input_collection = os.getenv("MONGO_INPUT_COLLECTION", "")
mongo_output_collection = os.getenv("MONGO_OUTPUT_COLLECTION", "")

client = MongoClient(
    mongo_uri,
    tls=True,
    tlsCAFile=certifi.where()
)
db = client[mongo_db_name]
input_collection = db[mongo_input_collection]
output_collection = db[mongo_output_collection]

class UniversalDataStore:
    
    def __init__(self, excel_file_path: str = "outputs/universal_dataset.xlsx"):
        self._data: List[Dict[str, Any]] = []
        self.excel_file_path = excel_file_path
        os.makedirs(os.path.dirname(excel_file_path), exist_ok=True)
    
    def add_uniform_record(self, 
        client_code: str = None,
        transcript: str = None,
        lead_data: str = None,
        latest_message: str = None,
        expected_output: str = None,
        source: str = "unknown",
        update_mongo: bool = True):
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
        
        if source == "text_fields":
            self._insert_text_field_document(entry)
            
        self._update_excel_file()
        
        if update_mongo:
            self.insert_batch_into_mongodb()
    
    def add_uniform_records(self, records: List[Dict[str, Any]], source: str = "unknown"):
        for record in records:
            self.add_uniform_record(
                client_code=record.get("client_code"),
                transcript=record.get("transcript"),
                lead_data=record.get("lead_data"),
                latest_message=record.get("latest_message"),
                expected_output=record.get("expected_output"),
                source=source,
                update_mongo=False  
            )
        
        if source == "excel_upload":
            self._insert_excel_upload_document(records)
        
        self.insert_batch_into_mongodb()
    
    def _insert_excel_upload_document(self, records: List[Dict[str, Any]]):
        document_id = f"excel_upload_{uuid.uuid4().hex[:12]}"
        
        excel_doc = {
            "document_id": document_id,
            "document_type": "excel_upload",
            "uploaded_at": datetime.now().isoformat(),
            "record_count": len(records),
            "records": records
        }
        input_collection.insert_one(excel_doc)
        return document_id
    
    def _insert_text_field_document(self, entry: Dict[str, Any]):
        document_id = f"text_field_{uuid.uuid4().hex[:12]}"
        
        text_field_doc = {
            "document_id": document_id,
            "document_type": "text_field_entry",
            "created_at": datetime.now().isoformat(),
            "entry": entry
        }
        input_collection.insert_one(text_field_doc)
        return document_id
    
    def insert_batch_into_mongodb(self):
        if not self._data:
            return
        
        universal_doc = {
            "document_id": "universal_dataset_main",
            "document_type": "universal_dataset",
            "updated_at": datetime.now().isoformat(),
            "record_count": len(self._data),
            "records": self._data
        }
        
        input_collection.update_one(
            {"document_type": "universal_dataset"},  
            {"$set": universal_doc},                  
            upsert=True                             
        )
    
    def clear_data(self):
        self._data = []
        if os.path.exists(self.excel_file_path):
            os.remove(self.excel_file_path)
    
    def _update_excel_file(self):
        if self._data:
            df = pd.DataFrame(self._data)
            df.to_excel(self.excel_file_path, index=False, engine='openpyxl')
    
    def get_excel_file_path(self) -> str:
        return self.excel_file_path

    def insert_single_record_into_mongodb(self, entry: Dict[str, Any]):
        doc = dict(entry)
        doc.pop("_id", None)
        input_collection.insert_many([doc])
    
    def get_document_by_id(self, document_id: str) -> Dict[str, Any]:
        return input_collection.find_one({"document_id": document_id})
    
    def get_all_excel_uploads(self) -> List[Dict[str, Any]]:
        return list(input_collection.find({"document_type": "excel_upload"}))
    
    def get_all_text_field_entries(self) -> List[Dict[str, Any]]:
        return list(input_collection.find({"document_type": "text_field_entry"}))
    
    def get_universal_dataset_from_mongo(self) -> Dict[str, Any]:
        return input_collection.find_one({"document_id": "universal_dataset_main"})
    
    def store_processed_output(self, source_document_id: str, processed_records: List[Dict[str, Any]], output_file_path: str) -> str:
        output_document_id = f"output_{uuid.uuid4().hex[:12]}"
        
        output_doc = {
            "output_document_id": output_document_id,
            "source_document_id": source_document_id,
            "processed_at": datetime.now().isoformat(),
            "record_count": len(processed_records),
            "output_file_path": output_file_path,
            "processed_records": processed_records
        }
        
        output_collection.insert_one(output_doc)
        return output_document_id
    
    def get_output_by_id(self, output_document_id: str) -> Dict[str, Any]:
        return output_collection.find_one({"output_document_id": output_document_id})
    
    def get_all_outputs(self) -> List[Dict[str, Any]]:
        return list(output_collection.find())

universal_data_store = UniversalDataStore()

