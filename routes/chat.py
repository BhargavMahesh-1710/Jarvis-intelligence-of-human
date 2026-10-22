from pathlib import Path
import subprocess
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from core.agent import jarvis_agent, execute_tool
from core.memory import memory_store
from core.rag import rag_pipeline
from core.safety import safety_manager

from tools.device_control import open_app, find_and_open_laptop_file

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    tools_used: Optional[List[str]] = None
    plan: Optional[List[str]] = None
    pending_action: Optional[Dict[str, Any]] = None
    open_url: Optional[str] = None
    action_type: Optional[str] = None
    target: Optional[str] = None
    folder_path: Optional[str] = None
    folder_name: Optional[str] = None
    files: Optional[List[Dict[str, Any]]] = None
    file_url: Optional[str] = None
    is_image: Optional[bool] = None
    path: Optional[str] = None
    embed_url: Optional[str] = None
    video_id: Optional[str] = None
    action: Optional[str] = None
    aux_display: Optional[Dict[str, Any]] = None

class OpenFileRequest(BaseModel):
    path: str

class OpenFolderRequest(BaseModel):
    folder: str

class ConfirmRequest(BaseModel):
    action_id: str
    approved: bool

class MemoryItemRequest(BaseModel):
    fact: str

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """
    Main communication endpoint between Frontend UI and JARVIS Agent.
    Routes intent through Universal 11-step Orchestrator with verification and event streaming.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    # Indicate this request comes from the web UI so device tools avoid opening duplicate tabs
    from tools.device_control import set_web_context
    set_web_context(True)

    from core.orchestrator import orchestrator
    exec_res = orchestrator.process(req.message)
    res_dict = exec_res.model_dump()
    reply_safe = str(res_dict.get('reply', '')).encode('ascii', errors='replace').decode('ascii')
    print(f">>> [JARVIS ORCHESTRATOR RESULT] Intent: {res_dict.get('intent')} | Tools: {res_dict.get('tools_used')} | Verified: {res_dict.get('verified')} | Reply: {reply_safe}\n")
    return ChatResponse(**res_dict)

@router.post("/chat/confirm")
def confirm_action_endpoint(req: ConfirmRequest):
    """
    Handles user confirmation for consequential actions.
    Supports both PermissionGatekeeper (11-step architecture) and legacy SafetyManager.
    """
    from core.permissions import permission_gatekeeper
    from tools.registry import tool_registry
    from core.event_bus import event_bus, EventType

    # Check new PermissionGatekeeper
    pending = permission_gatekeeper.get_pending(req.action_id)
    if pending:
        permission_gatekeeper.resolve_authorization(req.action_id, req.approved)
        if req.approved:
            res = tool_registry.execute(pending.tool_name, pending.arguments)
            event_bus.publish_sync(EventType.SUCCESS, {
                "tool": pending.tool_name,
                "message": f"Action approved and executed: {pending.tool_name}",
                "output": res.output
            })
            return {
                "success": res.success,
                "status": "executed" if res.success else "error",
                "message": res.message,
                "result": res.output
            }
        else:
            event_bus.publish_sync(EventType.STATUS_UPDATE, {
                "message": f"Action '{pending.tool_name}' rejected by user."
            })
            return {
                "success": True,
                "status": "cancelled",
                "message": f"Action '{pending.tool_name}' was cancelled."
            }

    # Fallback to legacy safety_manager
    action = safety_manager.resolve_action(req.action_id, req.approved)
    if not action:
        raise HTTPException(status_code=404, detail=f"Pending action '{req.action_id}' not found or already processed.")

    if req.approved:
        try:
            execution_result = execute_tool(action.tool_name, action.arguments)
            safety_manager.log_event(
                tool_name=action.tool_name,
                arguments=action.arguments,
                status="executed",
                details=execution_result,
                is_consequential=True
            )
            return {
                "success": True,
                "status": "executed",
                "message": f"Action approved and executed: {action.description}",
                "result": execution_result
            }
        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "message": f"Execution error: {str(e)}"
            }
    else:
        return {
            "success": True,
            "status": "cancelled",
            "message": f"Action was rejected by user: {action.description}"
        }

@router.get("/chat/memory")
def get_memories():
    """Returns stored memories."""
    return {"memories": memory_store.load_memory()}

@router.post("/chat/memory")
def add_memory(req: MemoryItemRequest):
    """Adds a fact to long-term memory."""
    saved = memory_store.save_memory(req.fact)
    return {"success": True, "saved": saved}

@router.delete("/chat/memory")
def clear_memories():
    """Clears all stored memories."""
    memory_store.clear_memory()
    return {"success": True, "message": "Memory cleared."}

@router.get("/chat/knowledge")
def get_knowledge_summary():
    """Returns information on ingested RAG documents."""
    docs = rag_pipeline.load_documents()
    return {
        "documents_count": len(docs),
        "chunks_count": len(rag_pipeline.vector_db.chunks),
        "documents": [d["source"] for d in docs]
    }

@router.post("/chat/knowledge/reload")
def reload_knowledge():
    """Reloads and re-indexes all knowledge documents."""
    docs_cnt, chunks_cnt = rag_pipeline.reload_documents()
    return {
        "success": True,
        "documents_count": docs_cnt,
        "chunks_count": chunks_cnt,
        "message": f"Indexed {docs_cnt} documents into {chunks_cnt} vector chunks."
    }

@router.post("/chat/open-file")
def open_file_endpoint(req: OpenFileRequest):
    """Directly opens a file on user's laptop using default program."""
    return find_and_open_laptop_file(req.path)

@router.post("/chat/open-folder")
def open_folder_endpoint(req: OpenFolderRequest):
    """Directly opens a folder in File Explorer on user's laptop."""
    return open_app(req.folder)

@router.get("/chat/file-content")
def get_file_content(path: str):
    """Serves raw file or image bytes for direct in-browser holographic preview."""
    p = Path(path)
    if p.exists() and p.is_file():
        ext = p.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".mp4": "video/mp4"
        }
        return FileResponse(str(p), media_type=media_types.get(ext, "application/octet-stream"))
    raise HTTPException(status_code=404, detail="File not found")

@router.post("/chat/open-paint")
def open_paint_endpoint(req: OpenFileRequest):
    """Launches image in Windows Paint."""
    subprocess.Popen(["mspaint", req.path])
    return {"success": True, "message": f"Opened '{Path(req.path).name}' in Paint."}

class WorkspaceFileWriteRequest(BaseModel):
    filename: str
    content: str

@router.get("/api/workspace/files")
def get_workspace_files():
    """Lists all files in the sandboxed project workspace."""
    from tools.files import list_files
    return list_files()

@router.get("/api/workspace/file")
def get_workspace_file_content(name: str):
    """Reads content of a file in the workspace."""
    from tools.files import read_file
    return read_file(name)

@router.post("/api/workspace/file")
def create_workspace_file(req: WorkspaceFileWriteRequest):
    """Creates or updates a file in the project workspace."""
    from tools.files import write_file
    return write_file(req.filename, req.content)

@router.delete("/api/workspace/file")
def delete_workspace_file(name: str):
    """Deletes a file in the project workspace."""
    from tools.files import delete_file
    return delete_file(name)

@router.get("/api/tasks/pending")
def get_pending_tasks():
    """Returns all unexpired authorization requests requiring user confirmation."""
    from core.permissions import permission_gatekeeper
    pending = permission_gatekeeper.list_pending()
    return {
        "pending": [
            {
                "action_id": v.action_id,
                "tool_name": v.tool_name,
                "description": v.description,
                "risk_level": v.risk_level.value,
                "arguments": v.arguments,
                "created_at": v.created_at,
                "expires_at": v.expires_at
            }
            for v in pending.values()
        ]
    }

@router.get("/api/history")
def get_activity_history():
    """Returns sliding-window conversation and directive history."""
    from core.context import context_manager
    history = context_manager.get_conversation_history()
    return {"history": history}

@router.get("/api/system/telemetry")
def get_system_telemetry():
    """Returns real-time laptop telemetry (Time, Battery, CPU load, RAM usage)."""
    from tools.device_control import get_system_status
    return get_system_status()
