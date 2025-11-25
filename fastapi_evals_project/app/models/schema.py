from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict

class EvalRow(BaseModel):
    transcript: Optional[str]
    lead_data: Optional[str]
    latest_message: Optional[str]

class EvalResult(BaseModel):
    original_row: Dict[str, Any]
    llm_output: Optional[Dict[str, Any]]
    feedback: Optional[str]
    success: bool = True

class TextFieldsInput(BaseModel):
    fields: Dict[str, str] = Field(..., description="Dictionary of field names and their values")

class TextFieldsResponse(BaseModel):
    received_data: Dict[str, str]
    message: str = "Data received successfully"

class ExcelDataResponse(BaseModel):
    data: List[Dict[str, Any]]
    sheet_names: List[str]
    total_rows: int
    message: str = "Excel data extracted successfully"

class UniversalDataRecord(BaseModel):
    id: int
    timestamp: str
    source: str
    client_code: Optional[str] = None
    transcript: Optional[str] = None
    lead_data: Optional[str] = None
    latest_message: Optional[str] = None
    expected_output: Optional[str] = None

class ProcessDatasetResponse(BaseModel):
    success: bool
    message: str
    output_file: Optional[str]
    output_document_id: Optional[str] = None
    total_records: Optional[int] = None

class DocumentSummary(BaseModel):
    document_id: str
    document_type: str
    created_updated_at: str
    record_count: int
    description: Optional[str] = None


class DocumentListResponse(BaseModel):
    total_documents: int
    excel_uploads: List[DocumentSummary]
    text_field_entries: List[DocumentSummary]
    universal_dataset: Optional[DocumentSummary] = None
    message: str = "Documents retrieved successfully"


class DocumentDetailResponse(BaseModel):
    document_id: str
    document_type: str
    created_updated_at: str
    record_count: int
    records: List[Dict[str, Any]]
    message: str = "Document retrieved successfully"


class OutputDetailResponse(BaseModel):
    output_document_id: str
    source_document_id: str
    processed_at: str
    record_count: int
    output_file_path: str
    processed_records: List[Dict[str, Any]]
    message: str = "Output retrieved successfully"


class OutputListResponse(BaseModel):
    total_outputs: int
    outputs: List[Dict[str, Any]]
    message: str = "Outputs retrieved successfully"
