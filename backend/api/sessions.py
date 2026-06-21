# sessions api router -session CRUD and history endpoints

from fastapi import APIRouter, HTTPException, Query 
from db.database import list_sessions, get_session_history, create_session

router = APIRouter(prefix="/sessions", tags=["sessions"])

# list recent sessions and most recently update 1st  
@router.get("")
async def get_sessions(limit: int = Query(default = 20, le=100)):
    return await list_sessions(limit)



# create a new blank session and return its id 
@router.post("")
async def new_session():
    sid =await create_session()
    return {"session_id": sid}


@router.get("/{session_id}/ history")
async def get_history(session_id: str, limit: int = Query(default=20, le=100)):
    history = await get_session_history(session_id, limit)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "messages": history}
