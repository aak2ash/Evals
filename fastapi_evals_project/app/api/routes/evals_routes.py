from fastapi import APIRouter, UploadFile, File, Depends, Body, HTTPException
from typing import Any, Dict

from app.api.controllers.evals_controller import EvalsController
from app.services.evals_service import EvalsService
from app.models.schema import (
    TextFieldsInput, 
    TextFieldsResponse, 
    ExcelDataResponse, 
    ProcessDatasetResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    OutputDetailResponse,
    OutputListResponse
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
    result = await controller.handle_excel_read(file)
    return result


@router.post("/text-fields", response_model=TextFieldsResponse)
async def process_text_fields(
    fields: Dict[str, str] = Body(..., example={"client_code": "value1", "transcript": "value2", "lead_data": "value3", "latest_message": "value4", "expected_output": "value5"}),
    controller: EvalsController = Depends(get_controller)
):
    result = controller.handle_text_fields(fields)
    return result


@router.get("/documents", response_model=DocumentListResponse)
async def list_all_documents(
    controller: EvalsController = Depends(get_controller)
):
    result = controller.list_all_documents()
    return result


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document_by_id(
    document_id: str,
    controller: EvalsController = Depends(get_controller)
):
    try:
        result = controller.get_document_by_id(document_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/process_document/{document_id}", response_model=ProcessDatasetResponse)
async def process_document_by_id(
    document_id: str,
    controller: EvalsController = Depends(get_controller)
):
    try:
        result = await controller.process_document_by_id(document_id)
        await controller.shutdown()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.get("/outputs", response_model=OutputListResponse)
async def list_all_outputs(
    controller: EvalsController = Depends(get_controller)
):
    result = controller.list_all_outputs()
    return result


@router.get("/outputs/{output_document_id}", response_model=OutputDetailResponse)
async def get_output_by_id(
    output_document_id: str,
    controller: EvalsController = Depends(get_controller)
):
    try:
        result = controller.get_output_by_id(output_document_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

