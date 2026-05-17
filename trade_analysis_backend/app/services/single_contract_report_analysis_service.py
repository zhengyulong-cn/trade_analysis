from datetime import datetime, timezone
from typing import Iterable

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.single_contract_report_analysis import SingleContractReportAnalysis
from app.schemas.single_contract_report_analysis import (
    SingleContractReportAnalysisResult,
    SingleContractReportAnalysisRunRequest,
)
from app.services.contract_prompt_profile_service import ContractPromptProfileService
from app.services.contract_service import ContractService
from app.services.deepseek_llm_service import DeepSeekLLMService
from app.services.report_document_service import ReportDocumentService


class SingleContractReportAnalysisService:
    def __init__(
        self,
        session: Session,
        contract_service: ContractService,
        prompt_profile_service: ContractPromptProfileService,
        report_document_service: ReportDocumentService,
        deepseek_service: DeepSeekLLMService,
    ):
        self.session = session
        self.contract_service = contract_service
        self.prompt_profile_service = prompt_profile_service
        self.report_document_service = report_document_service
        self.deepseek_service = deepseek_service

    def list_analyses(
        self,
        contract_id: int | None = None,
        report_id: int | None = None,
    ) -> list[SingleContractReportAnalysis]:
        statement = select(SingleContractReportAnalysis).order_by(
            SingleContractReportAnalysis.create_at.desc()
        )
        if contract_id is not None:
            statement = statement.where(SingleContractReportAnalysis.contract_id == contract_id)
        if report_id is not None:
            statement = statement.where(SingleContractReportAnalysis.report_id == report_id)
        return list(self.session.exec(statement).all())

    def get_analysis_by_id(self, analysis_id: int) -> SingleContractReportAnalysis:
        analysis = self.session.get(SingleContractReportAnalysis, analysis_id)
        if analysis is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Single contract report analysis not found: {analysis_id}",
            )
        return analysis

    def run_analysis(
        self,
        payload: SingleContractReportAnalysisRunRequest,
    ) -> SingleContractReportAnalysis:
        contract = self.contract_service.get_contract_by_id(payload.contract_id)
        report = self.report_document_service.get_document_by_id(payload.report_id)
        profile = self.prompt_profile_service.get_profile_by_contract_id(payload.contract_id)

        if profile.is_active != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"AI profile is disabled for contract: {contract.symbol}",
            )

        matched_snippets = self._extract_relevant_snippets(
            raw_text=report.raw_text,
            contract_symbol=contract.symbol,
            contract_name=contract.name,
            focus_dimensions=profile.focus_dimensions,
        )
        system_prompt, user_prompt = self._build_prompts(
            contract_symbol=contract.symbol,
            contract_name=contract.name,
            report_title=report.title or report.original_name,
            report_source=report.source,
            report_published_at=report.published_at.isoformat() if report.published_at else None,
            focus_dimensions=profile.focus_dimensions,
            analysis_style=profile.analysis_style,
            extra_instruction=profile.extra_instruction,
            output_preference=profile.output_preference,
            matched_snippets=matched_snippets,
        )
        print(matched_snippets)

        result = self.deepseek_service.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=SingleContractReportAnalysisResult,
        )

        now = datetime.now(timezone.utc)
        analysis = SingleContractReportAnalysis(
            contract_id=contract.contract_id,
            report_id=report.report_id,
            profile_id=profile.profile_id,
            contract_symbol=contract.symbol,
            contract_name=contract.name,
            report_title=report.title or report.original_name,
            report_source=report.source,
            status="success",
            profile_snapshot={
                "focus_dimensions": profile.focus_dimensions,
                "analysis_style": profile.analysis_style,
                "extra_instruction": profile.extra_instruction,
                "output_preference": profile.output_preference,
                "is_active": profile.is_active,
            },
            matched_snippets=matched_snippets,
            result_json=result.model_dump(),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            create_at=now,
            updated_at=now,
        )
        self.session.add(analysis)
        self.session.commit()
        self.session.refresh(analysis)
        return analysis

    def _extract_relevant_snippets(
        self,
        raw_text: str,
        contract_symbol: str,
        contract_name: str,
        focus_dimensions: list[str],
    ) -> list[str]:
        normalized_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        paragraphs = [item.strip() for item in normalized_text.split("\n\n") if item.strip()]
        if not paragraphs:
            return []

        keywords = self._build_keywords(contract_symbol, contract_name, focus_dimensions)
        matched: list[str] = []
        for paragraph in paragraphs:
            score = sum(1 for keyword in keywords if keyword and keyword.lower() in paragraph.lower())
            if score > 0:
                matched.append(paragraph)
            if len(matched) >= 12:
                break

        if not matched:
            matched = paragraphs[:6]

        snippets: list[str] = []
        total_length = 0
        for item in matched:
            compact = " ".join(item.split())
            if not compact:
                continue
            clipped = compact[:800]
            snippets.append(clipped)
            total_length += len(clipped)
            if total_length >= 6000:
                break
        return snippets

    def _build_keywords(
        self,
        contract_symbol: str,
        contract_name: str,
        focus_dimensions: Iterable[str],
    ) -> list[str]:
        keywords = [contract_symbol.strip(), contract_name.strip()]
        product_prefix = "".join(char for char in contract_symbol if char.isalpha())
        if product_prefix:
            keywords.append(product_prefix)
        keywords.extend(item.strip() for item in focus_dimensions if item.strip())
        deduped: list[str] = []
        seen: set[str] = set()
        for keyword in keywords:
            lowered = keyword.lower()
            if not keyword or lowered in seen:
                continue
            deduped.append(keyword)
            seen.add(lowered)
        return deduped

    def _build_prompts(
        self,
        contract_symbol: str,
        contract_name: str,
        report_title: str,
        report_source: str | None,
        report_published_at: str | None,
        focus_dimensions: list[str],
        analysis_style: str | None,
        extra_instruction: str | None,
        output_preference: str | None,
        matched_snippets: list[str],
    ) -> tuple[str, str]:
        focus_text = "、".join(focus_dimensions) if focus_dimensions else "供需、库存、基差、估值、政策、情绪"
        system_prompt = (
            "你是期货研究分析助手。"
            "你的任务是只围绕指定单一品种，结合该品种的AI画像配置，"
            "从提供的研报片段中提炼与该品种相关的观点。"
            "禁止分析无关品种，禁止虚构原文未提及的信息。"
            "请只返回JSON，不要输出Markdown代码块。"
        )

        snippet_text = "\n\n".join(
            f"[片段{i + 1}]\n{snippet}" for i, snippet in enumerate(matched_snippets)
        )
        user_prompt = f"""
目标品种：
- 合约代码：{contract_symbol}
- 品种名称：{contract_name}

研报信息：
- 标题：{report_title}
- 来源：{report_source or "未提供"}
- 发布日期：{report_published_at or "未提供"}

AI画像配置：
- 关注维度：{focus_text}
- 分析风格：{analysis_style or "未配置"}
- 额外提示：{extra_instruction or "未配置"}
- 输出偏好：{output_preference or "未配置"}

请基于下面这些与目标品种相关的研报片段，输出一个JSON对象，字段必须严格包含：
- relevance: high | medium | low | none
- stance: bullish | bearish | neutral | mixed
- horizon: 字符串，表示观点时效，如“短期/中期/季度”
- confidence: 0到100的整数
- summary: 2到4句，概括该研报对目标品种的核心观点
- drivers: 字符串数组，列出主要驱动因素
- risks: 字符串数组，列出主要风险点
- evidence: 字符串数组，列出支持结论的原文要点，可转述但不要编造

研报片段：
{snippet_text}
""".strip()
        return system_prompt, user_prompt
