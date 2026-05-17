from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import ContractPromptProfileServiceDep
from app.schemas.contract_prompt_profile import (
    ContractPromptProfileCreate,
    ContractPromptProfileDeleteRequest,
    ContractPromptProfileRead,
    ContractPromptProfileUpdate,
)

router = APIRouter()


@router.get("", response_model=list[ContractPromptProfileRead])
def list_contract_prompt_profiles(
    service: ContractPromptProfileServiceDep,
) -> list[ContractPromptProfileRead]:
    return [
        ContractPromptProfileRead.model_validate(profile)
        for profile in service.list_profiles()
    ]


@router.get("/item", response_model=ContractPromptProfileRead)
def get_contract_prompt_profile(
    service: ContractPromptProfileServiceDep,
    profile_id: int | None = Query(default=None),
    contract_id: int | None = Query(default=None),
) -> ContractPromptProfileRead:
    if profile_id is not None:
        return ContractPromptProfileRead.model_validate(
            service.get_profile_by_id(profile_id)
        )
    if contract_id is not None:
        return ContractPromptProfileRead.model_validate(
            service.get_profile_by_contract_id(contract_id)
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="profile_id or contract_id is required",
    )


@router.post("/create", response_model=ContractPromptProfileRead, status_code=status.HTTP_201_CREATED)
def create_contract_prompt_profile(
    payload: ContractPromptProfileCreate,
    service: ContractPromptProfileServiceDep,
) -> ContractPromptProfileRead:
    return ContractPromptProfileRead.model_validate(service.create_profile(payload))


@router.post("/update", response_model=ContractPromptProfileRead)
def update_contract_prompt_profile(
    payload: ContractPromptProfileUpdate,
    service: ContractPromptProfileServiceDep,
) -> ContractPromptProfileRead:
    return ContractPromptProfileRead.model_validate(service.update_profile(payload))


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract_prompt_profile(
    payload: ContractPromptProfileDeleteRequest,
    service: ContractPromptProfileServiceDep,
) -> None:
    service.delete_profile(payload.profile_id)
