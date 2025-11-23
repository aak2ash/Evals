from typing import List, Dict, Any
from fastapi import UploadFile
import aiofiles
import os
import tempfile
import pandas as pd
from app.services import transcript_client
from app.services.evals_service import EvalsService
from app.services.data_store import universal_data_store
from app.models.schema import TextFieldsResponse, ExcelDataResponse, UniversalDatasetResponse
# from app.utils.openai_client import OpenAIClient


class EvalsController:
    def __init__(self, service: EvalsService):
        self.service = service
        self.transcript_analyzer = service.transcript_client  # already created inside service

    async def handle_upload_and_process(self, upload_file: UploadFile) -> List[Dict[str, Any]]:
        suffix = os.path.splitext(upload_file.filename)[1] or ".xlsx"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp_path = tmp.name
        tmp.close()

        async with aiofiles.open(tmp_path, 'wb') as out:
            await out.write(await upload_file.read())

        try:
            results_path = await self.service.process_excel(tmp_path)
            return {"output_file": results_path}
        finally:
            os.remove(tmp_path)

    async def shutdown(self):
        await self.service.close()

    async def handle_excel_read(self, upload_file: UploadFile) -> ExcelDataResponse:
        """Read an excel file and return its data"""
        suffix = os.path.splitext(upload_file.filename)[1] or ".xlsx"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp_path = tmp.name
        tmp.close()

        async with aiofiles.open(tmp_path, 'wb') as out:
            await out.write(await upload_file.read())

        try:
            # Read all sheets from excel file
            excel_file = pd.ExcelFile(tmp_path)
            sheet_names = excel_file.sheet_names
            
            # Read data from all sheets
            all_data = []
            uniform_records = []
            
            for sheet_name in sheet_names:
                df = pd.read_excel(tmp_path, sheet_name=sheet_name)
                # Convert DataFrame to list of dictionaries
                sheet_data = df.to_dict(orient='records')
                for record in sheet_data:
                    record['_sheet_name'] = sheet_name
                    all_data.append(record)
                    
                    # Extract uniform fields from Excel record
                    uniform_record = {
                        "client_code": record.get("client_code"),
                        "transcript": record.get("transcript"),
                        "lead_data": record.get("lead_data"),
                        "latest_message": record.get("latest_message"),
                        "expected_output": record.get("expected_output")
                    }
                    uniform_records.append(uniform_record)
            
            total_rows = len(all_data)
            
            # Add all records to universal dataset with uniform structure
            universal_data_store.add_uniform_records(uniform_records, source="excel_upload")
            
            return ExcelDataResponse(
                data=all_data,
                sheet_names=sheet_names,
                total_rows=total_rows
            )
        finally:
            os.remove(tmp_path)

    def handle_text_fields(self, fields_data: Dict[str, str]) -> TextFieldsResponse:
        """Process multiple text fields and return the data"""
        # Add the text fields data to universal dataset with uniform structure
        universal_data_store.add_uniform_record(
            client_code=fields_data.get("client_code"),
            transcript=fields_data.get("transcript"),
            lead_data=fields_data.get("lead_data"),
            latest_message=fields_data.get("latest_message"),
            expected_output=fields_data.get("expected_output"),
            source="text_fields"
        )
        
        return TextFieldsResponse(
            received_data=fields_data
        )
    
    def get_universal_dataset(self) -> UniversalDatasetResponse:
        """Retrieve all data from the universal dataset"""
        all_data = universal_data_store.get_all_data()
        total_records = universal_data_store.get_data_count()
        
        return UniversalDatasetResponse(
            total_records=total_records,
            data=all_data
        )
    
    async def process_universal_dataset(self) -> Dict[str, Any]:
        """
        Process the universal dataset through the same evaluation pipeline 
        as handle_upload_and_process, but using the accumulated dataset
        """
        # Get all data from universal dataset
        all_data = universal_data_store.get_all_data()
        
        if not all_data:
            return {
                "success": False,
                "message": "No data in universal dataset. Please add data first.",
                "output_file": None
            }
        
        # Convert universal dataset to DataFrame
        df = pd.DataFrame(all_data)
        
        # Create temporary Excel file from the dataset
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        tmp_path = tmp.name
        tmp.close()
        
        try:
            # Write the dataset to temporary Excel file
            df.to_excel(tmp_path, index=False, engine='openpyxl')
            
            # Process the Excel file using the same logic as handle_upload_and_process
            results_path = await self.service.process_excel(tmp_path, output_filename="universal_dataset_evaluated.xlsx")
            
            return {
                "success": True,
                "message": f"Successfully processed {len(all_data)} records from universal dataset",
                "output_file": results_path,
                "total_records": len(all_data)
            }
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)