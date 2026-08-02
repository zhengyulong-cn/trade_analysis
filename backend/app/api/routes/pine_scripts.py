from fastapi import APIRouter, status

from app.api.dependencies import PineScriptServiceDep
from app.schemas.pine_script import (
    PineScriptCreate,
    PineScriptDeleteRequest,
    PineScriptRead,
    PineScriptUpdate,
)

router = APIRouter()


@router.get("", response_model=list[PineScriptRead])
def list_pine_scripts(service: PineScriptServiceDep) -> list[PineScriptRead]:
    return [PineScriptRead.model_validate(item) for item in service.list_pine_scripts()]


@router.post("/create", response_model=PineScriptRead, status_code=status.HTTP_201_CREATED)
def create_pine_script(
    payload: PineScriptCreate,
    service: PineScriptServiceDep,
) -> PineScriptRead:
    return PineScriptRead.model_validate(service.create_pine_script(payload))


@router.post("/update", response_model=PineScriptRead)
def update_pine_script(
    payload: PineScriptUpdate,
    service: PineScriptServiceDep,
) -> PineScriptRead:
    return PineScriptRead.model_validate(service.update_pine_script(payload))


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_pine_script(
    payload: PineScriptDeleteRequest,
    service: PineScriptServiceDep,
) -> None:
    service.delete_pine_script(payload.script_id)
