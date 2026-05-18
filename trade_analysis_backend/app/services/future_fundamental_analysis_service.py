from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.future_fundamental_analysis import FutureFundamentalAnalysis
from app.models.future_product import FutureProduct
from app.models.future_report_document import FutureReportDocument
from app.schemas.future_fundamental_analysis import (
    FutureFundamentalAnalysisCreate,
    FutureFundamentalAnalysisListItem,
    FutureFundamentalAnalysisUpdate,
)


class FutureFundamentalAnalysisService:
    def __init__(self, session: Session):
        self.session = session

    def list_items(self) -> list[FutureFundamentalAnalysisListItem]:
        statement = (
            select(FutureFundamentalAnalysis, FutureProduct, FutureReportDocument)
            .join(FutureProduct, FutureProduct.product_id == FutureFundamentalAnalysis.product_id)
            .join(
                FutureReportDocument,
                FutureReportDocument.report_id == FutureFundamentalAnalysis.report_id,
            )
            .order_by(FutureFundamentalAnalysis.updated_at.desc())
        )
        rows = self.session.exec(statement).all()
        items: list[FutureFundamentalAnalysisListItem] = []
        for analysis, product, report in rows:
            items.append(
                FutureFundamentalAnalysisListItem(
                    analysis_id=analysis.analysis_id,
                    product_id=analysis.product_id,
                    report_id=analysis.report_id,
                    supply_side=analysis.supply_side,
                    demand_side=analysis.demand_side,
                    inventory_side=analysis.inventory_side,
                    industry_profit=analysis.industry_profit,
                    substitution_linkage=analysis.substitution_linkage,
                    policy_macro=analysis.policy_macro,
                    conclusion=analysis.conclusion,
                    create_at=analysis.create_at,
                    updated_at=analysis.updated_at,
                    product_code=product.product_code,
                    product_display_name=product.display_name,
                    report_name=report.report_name,
                    report_storage_path=report.storage_path,
                )
            )
        return items

    def create_item(self, payload: FutureFundamentalAnalysisCreate) -> FutureFundamentalAnalysis:
        self._ensure_product_exists(payload.product_id)
        self._ensure_report_exists(payload.report_id)
        item = FutureFundamentalAnalysis(**payload.model_dump())
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def update_item(self, payload: FutureFundamentalAnalysisUpdate) -> FutureFundamentalAnalysis:
        item = self.session.get(FutureFundamentalAnalysis, payload.analysis_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Future fundamental analysis not found: {payload.analysis_id}",
            )

        update_data = payload.model_dump(
            exclude={"analysis_id"},
            exclude_unset=True,
        )
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No future fundamental analysis fields to update",
            )

        product_id = update_data.get("product_id")
        if product_id is not None:
            self._ensure_product_exists(product_id)

        report_id = update_data.get("report_id")
        if report_id is not None:
            self._ensure_report_exists(report_id)

        for field_name, value in update_data.items():
            setattr(item, field_name, value)
        item.updated_at = datetime.now(timezone.utc)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete_item(self, analysis_id: int) -> None:
        item = self.session.get(FutureFundamentalAnalysis, analysis_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Future fundamental analysis not found: {analysis_id}",
            )
        self.session.delete(item)
        self.session.commit()

    def _ensure_product_exists(self, product_id: int) -> None:
        if self.session.get(FutureProduct, product_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Future product not found: {product_id}",
            )

    def _ensure_report_exists(self, report_id: int) -> None:
        if self.session.get(FutureReportDocument, report_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Future report document not found: {report_id}",
            )
