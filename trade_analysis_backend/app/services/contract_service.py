from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.contract import Contract
from app.models.product import Product
from app.schemas.contract import ContractCreate, MainContractSyncItem, ContractUpdate


class ContractService:
    def __init__(self, session: Session):
        self.session = session

    def create_contract(self, payload: ContractCreate) -> Contract:
        self._validate_product_exists(payload.product_id)
        self._validate_binary_flag(
            field_name="is_favorite",
            value=payload.is_favorite,
        )
        contract = Contract.model_validate(payload)
        self.session.add(contract)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contract already exists for the exchange",
            ) from exc
        self.session.refresh(contract)
        return contract

    def update_contract(self, payload: ContractUpdate) -> Contract:
        contract = self.get_contract_by_id(payload.contract_id)
        update_data = payload.model_dump(
            exclude={"contract_id"},
            exclude_none=True,
            exclude_unset=True,
        )
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No contract fields to update",
            )
        if "is_favorite" in update_data:
            self._validate_binary_flag(
                field_name="is_favorite",
                value=update_data["is_favorite"],
            )
        if "product_id" in update_data:
            self._validate_product_exists(update_data["product_id"])

        for field_name, value in update_data.items():
            setattr(contract, field_name, value)
        contract.updated_at = datetime.now(timezone.utc)
        self.session.add(contract)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contract already exists for the exchange",
            ) from exc
        self.session.refresh(contract)
        return contract

    def list_contracts(self) -> list[Contract]:
        statement = select(Contract).order_by(
            Contract.is_favorite.desc(),
            Contract.symbol,
        )
        return list(self.session.exec(statement).all())

    def get_contract_by_id(self, contract_id: int) -> Contract:
        contract = self.session.get(Contract, contract_id)
        if contract is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract not found: {contract_id}",
            )
        return contract

    def get_contract_by_symbol(self, symbol: str) -> Contract:
        statement = select(Contract).where(Contract.symbol == symbol)
        contract = self.session.exec(statement).first()
        if contract is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract not found: {symbol}",
            )
        return contract

    def get_contract_by_symbol_exchange(self, symbol: str, exchange: str) -> Contract | None:
        statement = select(Contract).where(
            Contract.symbol == symbol,
            Contract.exchange == exchange,
        )
        return self.session.exec(statement).first()

    def touch_contract(self, contract: Contract) -> Contract:
        contract.updated_at = datetime.now(timezone.utc)
        self.session.add(contract)
        self.session.commit()
        self.session.refresh(contract)
        return contract

    def sync_main_contracts(self, items: list[MainContractSyncItem]) -> tuple[int, int, list[Contract]]:
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No main contracts selected",
            )

        created = 0
        updated = 0
        synced_contracts: list[Contract] = []

        for item in items:
            symbol = item.symbol.strip()
            exchange = item.exchange.strip().upper()
            name = item.name.strip() or symbol
            product_code = self._extract_product_code(symbol)
            product = self.get_product_by_code_exchange(product_code=product_code, exchange=exchange)
            if product is None:
                product = Product(product_code=product_code, exchange=exchange, name=name)
                self.session.add(product)
                self.session.flush()

            existing = self.get_contract_by_symbol_exchange(symbol=symbol, exchange=exchange)
            if existing is None:
                contract = Contract(
                    product_id=product.product_id,
                    symbol=symbol,
                    exchange=exchange,
                    name=name,
                )
                self.session.add(contract)
                synced_contracts.append(contract)
                created += 1
                continue

            changed = False
            if existing.product_id != product.product_id:
                existing.product_id = product.product_id
                changed = True
            if existing.name != name:
                existing.name = name
                changed = True
            if changed:
                existing.updated_at = datetime.now(timezone.utc)
                self.session.add(existing)
                updated += 1
            synced_contracts.append(existing)

        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to sync main contracts",
            ) from exc

        for contract in synced_contracts:
            self.session.refresh(contract)
        return created, updated, synced_contracts

    def get_product_by_code_exchange(self, product_code: str, exchange: str) -> Product | None:
        statement = select(Product).where(
            Product.product_code == product_code,
            Product.exchange == exchange,
        )
        return self.session.exec(statement).first()

    def _extract_product_code(self, symbol: str) -> str:
        return "".join(char for char in symbol.strip() if char.isalpha()).upper() or symbol.strip().upper()

    def _validate_product_exists(self, product_id: int) -> None:
        product = self.session.get(Product, product_id)
        if product is not None:
            return
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {product_id}",
        )

    def _validate_binary_flag(self, field_name: str, value: int) -> None:
        if value in (0, 1):
            return
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be 0 or 1",
        )
