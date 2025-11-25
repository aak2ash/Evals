from typing import List, Dict, Any
from fastapi import UploadFile
import aiofiles
import os
import tempfile
import pandas as pd
from app.services import transcript_client
from app.services.evals_service import EvalsService
from app.services.data_store import universal_data_store
from app.models.schema import (
    TextFieldsResponse, 
    ExcelDataResponse, 
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentSummary,
    OutputDetailResponse,
    OutputListResponse
)


class EvalsController:
    def __init__(self, service: EvalsService):
        self.service = service
        self.transcript_analyzer = service.transcript_client

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
        suffix = os.path.splitext(upload_file.filename)[1] or ".xlsx"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp_path = tmp.name
        tmp.close()

        async with aiofiles.open(tmp_path, 'wb') as out:
            await out.write(await upload_file.read())

        try:
            excel_file = pd.ExcelFile(tmp_path)
            sheet_names = excel_file.sheet_names
            
            all_data = []
            uniform_records = []
            
            for sheet_name in sheet_names:
                df = pd.read_excel(tmp_path, sheet_name=sheet_name)
                sheet_data = df.to_dict(orient='records')
                for record in sheet_data:
                    record['_sheet_name'] = sheet_name
                    all_data.append(record)
                    
                    uniform_record = {
                        "client_code": record.get("client_code"),
                        "transcript": record.get("transcript"),
                        "lead_data": record.get("lead_data"),
                        "latest_message": record.get("latest_message"),
                        "expected_output": record.get("expected_output")
                    }
                    uniform_records.append(uniform_record)
            
            total_rows = len(all_data)
            
            universal_data_store.add_uniform_records(uniform_records, source="excel_upload")
            
            return ExcelDataResponse(
                data=all_data,
                sheet_names=sheet_names,
                total_rows=total_rows
            )
        finally:
            os.remove(tmp_path)

    def handle_text_fields(self, fields_data: Dict[str, str]) -> TextFieldsResponse:
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
    
    async def process_document_by_id(self, document_id: str) -> Dict[str, Any]:
        doc = universal_data_store.get_document_by_id(document_id)
        
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found")
        
        document_type = doc.get("document_type")
        
        if document_type == "excel_upload":
            records = doc.get("records", [])
            output_filename = f"{document_id}_evaluated.xlsx"
        elif document_type == "text_field_entry":
            records = [doc.get("entry", {})]
            output_filename = f"{document_id}_evaluated.xlsx"
        elif document_type == "universal_dataset":
            records = doc.get("records", [])
            output_filename = "universal_dataset_evaluated.xlsx"
        else:
            raise ValueError(f"Unknown document type: {document_type}")
        
        if not records:
            return {
                "success": False,
                "message": f"No records found in document '{document_id}'",
                "output_file": None
            }
        
        df = pd.DataFrame(records)
        
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        tmp_path = tmp.name
        tmp.close()
        
        try:
            df.to_excel(tmp_path, index=False, engine='openpyxl')
            
            results_path = await self.service.process_excel(tmp_path, output_filename=output_filename)
            
            processed_df = pd.read_excel(results_path, engine='openpyxl')
            processed_records = processed_df.to_dict(orient='records')
            
            output_document_id = universal_data_store.store_processed_output(
                source_document_id=document_id,
                processed_records=processed_records,
                output_file_path=results_path
            )
            
            return {
                "success": True,
                "message": f"Successfully processed {len(records)} records from document '{document_id}'",
                "output_file": results_path,
                "output_document_id": output_document_id,
                "total_records": len(records)
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def list_all_documents(self) -> DocumentListResponse:
        excel_uploads = universal_data_store.get_all_excel_uploads()
        excel_summaries = []
        for doc in excel_uploads:
            summary = DocumentSummary(
                document_id=doc.get("document_id"),
                document_type=doc.get("document_type"),
                created_updated_at=doc.get("uploaded_at", ""),
                record_count=doc.get("record_count", 0),
                description=f"Excel upload with {doc.get('record_count', 0)} records"
            )
            excel_summaries.append(summary)
        
        text_field_entries = universal_data_store.get_all_text_field_entries()
        text_field_summaries = []
        for doc in text_field_entries:
            summary = DocumentSummary(
                document_id=doc.get("document_id"),
                document_type=doc.get("document_type"),
                created_updated_at=doc.get("created_at", ""),
                record_count=1,  
                description=f"Text field entry"
            )
            text_field_summaries.append(summary)
        
        universal_doc = universal_data_store.get_universal_dataset_from_mongo()
        universal_summary = None
        if universal_doc:
            universal_summary = DocumentSummary(
                document_id=universal_doc.get("document_id"),
                document_type=universal_doc.get("document_type"),
                created_updated_at=universal_doc.get("updated_at", ""),
                record_count=universal_doc.get("record_count", 0),
                description=f"Universal dataset containing all {universal_doc.get('record_count', 0)} records"
            )
        
        total_documents = len(excel_summaries) + len(text_field_summaries) + (1 if universal_summary else 0)
        
        return DocumentListResponse(
            total_documents=total_documents,
            excel_uploads=excel_summaries,
            text_field_entries=text_field_summaries,
            universal_dataset=universal_summary
        )
    
    def get_document_by_id(self, document_id: str) -> DocumentDetailResponse:
        doc = universal_data_store.get_document_by_id(document_id)
        
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found")
        
        document_type = doc.get("document_type")
        
        if document_type == "excel_upload":
            records = doc.get("records", [])
            created_updated_at = doc.get("uploaded_at", "")
        elif document_type == "text_field_entry":
            records = [doc.get("entry", {})]
            created_updated_at = doc.get("created_at", "")
        elif document_type == "universal_dataset":
            records = doc.get("records", [])
            created_updated_at = doc.get("updated_at", "")
        else:
            records = []
            created_updated_at = ""
        
        return DocumentDetailResponse(
            document_id=document_id,
            document_type=document_type,
            created_updated_at=created_updated_at,
            record_count=len(records),
            records=records
        )
    
    def get_output_by_id(self, output_document_id: str) -> OutputDetailResponse:
        output_doc = universal_data_store.get_output_by_id(output_document_id)
        
        if not output_doc:
            raise ValueError(f"Output document with ID '{output_document_id}' not found")
        
        return OutputDetailResponse(
            output_document_id=output_doc.get("output_document_id"),
            source_document_id=output_doc.get("source_document_id"),
            processed_at=output_doc.get("processed_at", ""),
            record_count=output_doc.get("record_count", 0),
            output_file_path=output_doc.get("output_file_path", ""),
            processed_records=output_doc.get("processed_records", [])
        )
    
    def list_all_outputs(self) -> OutputListResponse:
        all_outputs = universal_data_store.get_all_outputs()
        
        output_summaries = []
        for output in all_outputs:
            summary = {
                "output_document_id": output.get("output_document_id"),
                "source_document_id": output.get("source_document_id"),
                "processed_at": output.get("processed_at"),
                "record_count": output.get("record_count"),
                "output_file_path": output.get("output_file_path")
            }
            output_summaries.append(summary)
        
        return OutputListResponse(
            total_outputs=len(output_summaries),
            outputs=output_summaries
        )