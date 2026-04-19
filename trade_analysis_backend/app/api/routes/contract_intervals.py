from fastapi import APIRouter, status

from app.api.dependencies import ContractIntervalServiceDep
from app.schemas.contract_interval import ContractIntervalCreate, ContractIntervalRead

router = APIRouter()


@router.post(
    "/",
    response_model=ContractIntervalRead,
    status_code=status.HTTP_201_CREATED,
)
def create_contract_interval(
    payload: ContractIntervalCreate,
    service: ContractIntervalServiceDep,
) -> ContractIntervalRead:
    return ContractIntervalRead.model_validate(service.create_interval(payload))


@router.get("/", response_model=list[ContractIntervalRead])
def list_contract_intervals(
    service: ContractIntervalServiceDep,
) -> list[ContractIntervalRead]:
    return [
        ContractIntervalRead.model_validate(interval)
        for interval in service.list_intervals()
    ]
