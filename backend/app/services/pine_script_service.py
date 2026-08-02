from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.pine_script import PineScript
from app.schemas.pine_script import PineScriptCreate, PineScriptUpdate


class PineScriptService:
    def __init__(self, session: Session):
        self.session = session

    def list_pine_scripts(self) -> list[PineScript]:
        statement = select(PineScript).order_by(PineScript.updated_at.desc(), PineScript.script_id.desc())
        return list(self.session.exec(statement).all())

    def create_pine_script(self, payload: PineScriptCreate) -> PineScript:
        script = PineScript.model_validate(payload.model_dump())
        self.session.add(script)
        self.session.commit()
        self.session.refresh(script)
        return script

    def update_pine_script(self, payload: PineScriptUpdate) -> PineScript:
        script = self.get_pine_script_by_id(payload.script_id)
        update_data = payload.model_dump(exclude={"script_id"}, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pine script fields to update",
            )

        for field_name, value in update_data.items():
            setattr(script, field_name, value)

        script.updated_at = datetime.now(timezone.utc)
        self.session.add(script)
        self.session.commit()
        self.session.refresh(script)
        return script

    def delete_pine_script(self, script_id: int) -> None:
        script = self.get_pine_script_by_id(script_id)
        self.session.delete(script)
        self.session.commit()

    def get_pine_script_by_id(self, script_id: int) -> PineScript:
        script = self.session.get(PineScript, script_id)
        if script is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pine script not found: {script_id}",
            )
        return script
