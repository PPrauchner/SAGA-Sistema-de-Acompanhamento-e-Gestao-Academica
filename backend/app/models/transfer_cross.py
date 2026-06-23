# backend/app/models/transfer_cross.py
from pydantic import BaseModel, Field

class TransferRequestCreate(BaseModel):
    student_id: str = Field(..., description="ID do discente a ser transferido")
    orientador_destino_id: str = Field(..., description="ID do orientador receptor")
    programa_origem_id: str = Field(default="prog_default", description="Matriz/Programa atual")
    programa_destino_id: str = Field(..., description="Nova matriz acadêmica de destino")

class TransferRejectPayload(BaseModel):
    motivo: str = Field(..., min_length=5, description="Justificativa obrigatória para rejeição")