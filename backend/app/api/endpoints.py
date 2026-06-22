from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.db.session import get_db_client

router = APIRouter()

@router.post("/alunos/{aluno_id}/mover-direto")
async def mover_direto(aluno_id: str, novo_orientador_id: str, db = Depends(get_db_client)):
    aluno = await db.alunos.find_one({"_id": aluno_id})
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
        
    orientador = await db.orientadores.find_one({"_id": novo_orientador_id})
    if not orientador:
        raise HTTPException(status_code=404, detail="Orientador não encontrado")
    
    # Bloqueio de Programa Cruzado para Mover Direto
    if aluno["programa_id"] != orientador["programa_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operação bloqueada. Mover-direto é restrito para o mesmo programa acadêmico."
        )
        
    await db.alunos.update_one(
        {"_id": aluno_id},
        {"$set": {"orientador_id": novo_orientador_id}}
    )
    return {"message": "Orientador atualizado com sucesso dentro do mesmo programa"}