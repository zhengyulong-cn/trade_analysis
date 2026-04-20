from fastapi import APIRouter, status

from app.api.dependencies import ContractServiceDep
from app.schemas.contract import ContractCreate, ContractRead, ContractUpdate

router = APIRouter()

@router.get("", response_model=list[ContractRead])
def list_contracts(service: ContractServiceDep) -> list[ContractRead]:
    return [ContractRead.model_validate(contract) for contract in service.list_contracts()]


@router.post("/create", response_model=ContractRead, status_code=status.HTTP_201_CREATED)
def create_contract(
    payload: ContractCreate,
    service: ContractServiceDep,
) -> ContractRead:
    return ContractRead.model_validate(service.create_contract(payload))


@router.post("/update", response_model=ContractRead)
def update_contract(
    payload: ContractUpdate,
    service: ContractServiceDep,
) -> ContractRead:
    return ContractRead.model_validate(service.update_contract(payload))
