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
    """Single record in the universal dataset with metadata"""
    id: int
    timestamp: str
    source: str
    client_code: Optional[str] = None
    transcript: Optional[str] = None
    lead_data: Optional[str] = None
    latest_message: Optional[str] = None
    expected_output: Optional[str] = None


class UniversalDatasetResponse(BaseModel):
    total_records: int
    data: List[UniversalDataRecord]
    message: str = "Universal dataset retrieved successfully"


class ProcessDatasetResponse(BaseModel):
    success: bool
    message: str
    output_file: Optional[str]
    total_records: Optional[int] = None
