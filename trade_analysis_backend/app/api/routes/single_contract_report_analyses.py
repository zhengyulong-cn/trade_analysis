from fastapi import APIRouter, status

from app.api.dependencies import SingleContractReportAnalysisServiceDep
from app.schemas.single_contract_report_analysis import (
    SingleContractReportAnalysisListItem,
    SingleContractReportAnalysisRead,
    SingleContractReportAnalysisRunRequest,
)

router = APIRouter()


@router.get("", response_model=list[SingleContractReportAnalysisListItem])
def list_single_contract_report_analyses(
    service: SingleContractReportAnalysisServiceDep,
    product_id: int | None = None,
    report_id: int | None = None,
) -> list[SingleContractReportAnalysisListItem]:
    return [
        SingleContractReportAnalysisListItem.model_validate(item)
        for item in service.list_analyses(product_id=product_id, report_id=report_id)
    ]


@router.get("/item/{analysis_id}", response_model=SingleContractReportAnalysisRead)
def get_single_contract_report_analysis(
    analysis_id: int,
    service: SingleContractReportAnalysisServiceDep,
) -> SingleContractReportAnalysisRead:
    return SingleContractReportAnalysisRead.model_validate(service.get_analysis_by_id(analysis_id))


@router.post("/run", response_model=SingleContractReportAnalysisRead, status_code=status.HTTP_201_CREATED)
def run_single_contract_report_analysis(
    payload: SingleContractReportAnalysisRunRequest,
    service: SingleContractReportAnalysisServiceDep,
) -> SingleContractReportAnalysisRead:
    return SingleContractReportAnalysisRead.model_validate(service.run_analysis(payload))
