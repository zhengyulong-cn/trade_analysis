from fastapi import APIRouter, status
import re

from app.api.dependencies import ContractServiceDep, QuoteProviderDep
from app.schemas.contract import (
    ContractCreate,
    ContractRead,
    ContractUpdate,
    MainContractCandidateRead,
    MainContractSyncPayload,
    MainContractSyncResult,
)

router = APIRouter()

# 排除的合约，成交量太小不适合分析操作
EXCLUDED_MAIN_CONTRACT_PRODUCTS = {"JR","PM","RI","WH","ZC", "bb", "wr", "RS", "rr", "fb", "lg", "op", "CY", "pd", "pt", "PL", "ad", "cs", "T", "TF", "TS", "TL"}

def _extract_product_prefix(symbol: str) -> str:
    match = re.match(r"([A-Za-z]+)", symbol)
    if not match:
        return symbol.upper()
    return match.group(1).upper()


def _is_allowed_main_contract(symbol: str) -> bool:
    # 先按品种前缀做黑名单过滤。
    # RR: 粳米
    # ZC: 动力煤
    return _extract_product_prefix(symbol) not in EXCLUDED_MAIN_CONTRACT_PRODUCTS

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


@router.get("/main-contracts", response_model=list[MainContractCandidateRead])
def list_main_contracts(
    quote_provider: QuoteProviderDep,
    has_night: bool = True,
) -> list[MainContractCandidateRead]:
    return [
        MainContractCandidateRead(
            symbol=item.symbol,
            exchange=item.exchange,
            provider_symbol=item.provider_symbol,
            name=item.name,
        )
        for item in quote_provider.list_main_contracts(has_night=has_night)
        if _is_allowed_main_contract(item.symbol)
    ]


@router.post("/main-contracts/sync", response_model=MainContractSyncResult)
def sync_main_contracts(
    payload: MainContractSyncPayload,
    service: ContractServiceDep,
) -> MainContractSyncResult:
    created, updated, items = service.sync_main_contracts(payload.items)
    return MainContractSyncResult(
        created=created,
        updated=updated,
        items=[ContractRead.model_validate(item) for item in items],
    )
