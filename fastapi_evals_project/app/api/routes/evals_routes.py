from fastapi import APIRouter, UploadFile, File, Depends, Body
from typing import Any, Dict

from app.api.controllers.evals_controller import EvalsController
from app.services.evals_service import EvalsService
from app.models.schema import (
    TextFieldsInput, 
    TextFieldsResponse, 
    ExcelDataResponse, 
    UniversalDatasetResponse,
    ProcessDatasetResponse
)


router = APIRouter(prefix="/api/evals", tags=["evals"])

def get_controller() -> EvalsController:
    service = EvalsService()
    return EvalsController(service=service)


@router.post("/upload")
async def upload_eval_file(
    file: UploadFile = File(...),
    controller: EvalsController = Depends(get_controller)
):
    result = await controller.handle_upload_and_process(file)
    await controller.shutdown()
    return result


@router.post("/read-excel", response_model=ExcelDataResponse)
async def read_excel_file(
    file: UploadFile = File(...),
    controller: EvalsController = Depends(get_controller)
):
    """
    Upload an Excel file and receive its data
    """
    result = await controller.handle_excel_read(file)
    return result


@router.post("/text-fields", response_model=TextFieldsResponse)
async def process_text_fields(
    fields: Dict[str, str] = Body(..., example={"client_code": "value1", "transcript": "value2", "lead_data": "value3", "latest_message": "value4", "expected_output": "value5"}),
    controller: EvalsController = Depends(get_controller)
):
    """
    Submit multiple text fields and receive the data back
    """
    result = controller.handle_text_fields(fields)
    return result


@router.get("/display_data_set", response_model=UniversalDatasetResponse)
async def display_universal_dataset(
    controller: EvalsController = Depends(get_controller)
):
    """
    Display all data from the universal dataset (both excel uploads and text field submissions)
    """
    result = controller.get_universal_dataset()
    return result


@router.post("/process_universal_dataset", response_model=ProcessDatasetResponse)
async def process_universal_dataset(
    controller: EvalsController = Depends(get_controller)
):
    """
    Process the universal dataset through the evaluation pipeline.
    This uses the same logic as the upload route but processes the accumulated universal dataset.
    
    The universal dataset should contain records with the fields:
    - client_code
    - transcript
    - lead_data
    - latest_message
    - expected_output
    """
    result = await controller.process_universal_dataset()
    await controller.shutdown()
    return result

