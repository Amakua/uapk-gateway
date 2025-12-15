"""UI routes for the operator dashboard."""

import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import DbSession, get_current_user_optional
from app.core.security import decode_access_token
from app.models.approval import ApprovalStatus
from app.models.interaction_record import Decision
from app.models.user import User
from app.schemas.interaction_record import InteractionRecordQuery, LogExportRequest
from app.services import approval as approval_service
from app.services.approval import ApprovalError
from app.services.api_key import ApiKeyService
from app.services.auth import AuthService
from app.services.interaction_record import InteractionRecordService

router = APIRouter(tags=["UI"])

templates = Jinja2Templates(directory="app/ui/templates")


async def get_ui_user(
    db: DbSession,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User | None:
    """Get current user from session cookie."""
    if access_token is None:
        return None

    payload = decode_access_token(access_token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    from uuid import UUID

    auth_service = AuthService(db)
    return await auth_service.get_user_by_id(UUID(user_id))


UIUser = Annotated[User | None, Depends(get_ui_user)]


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: UIUser) -> Response:
    """Render the main operator dashboard."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"title": "UAPK Gateway - Dashboard", "user": user},
    )


@router.get("/ui/login", response_class=HTMLResponse)
async def login_page(request: Request, user: UIUser, error: str | None = None) -> Response:
    """Render the login page."""
    if user is not None:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"title": "UAPK Gateway - Login", "error": error},
    )


@router.post("/ui/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    db: DbSession,
    email: str = Form(...),
    password: str = Form(...),
) -> Response:
    """Handle login form submission."""
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(email, password)

    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "title": "UAPK Gateway - Login",
                "error": "Invalid email or password",
            },
        )

    # Create token and set cookie
    token_response = await auth_service.create_token_for_user(user)

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token_response.access_token,
        httponly=True,
        max_age=token_response.expires_in,
        samesite="lax",
    )
    return response


@router.get("/ui/logout", response_class=HTMLResponse)
async def logout(request: Request) -> Response:
    """Logout and clear session cookie."""
    response = RedirectResponse(url="/ui/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.get("/agents", response_class=HTMLResponse)
async def agents_list(request: Request, user: UIUser) -> Response:
    """Render the agents management page."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="agents.html",
        context={"title": "UAPK Gateway - Agents", "user": user},
    )


@router.get("/policies", response_class=HTMLResponse)
async def policies_list(request: Request, user: UIUser) -> Response:
    """Render the policies management page."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="policies.html",
        context={"title": "UAPK Gateway - Policies", "user": user},
    )


@router.get("/ui/logs", response_class=HTMLResponse)
async def interaction_logs(
    request: Request,
    user: UIUser,
    db: DbSession,
    uapk_id: str | None = None,
    agent_id: str | None = None,
    tool: str | None = None,
    decision: str | None = None,
    start_time: datetime | None = Query(default=None, alias="from"),
    end_time: datetime | None = Query(default=None, alias="to"),
    limit: int = 50,
    offset: int = 0,
) -> Response:
    """Render the interaction logs page."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    if not user.default_org_id:
        return templates.TemplateResponse(
            request=request,
            name="logs.html",
            context={
                "title": "UAPK Gateway - Interaction Logs",
                "user": user,
                "error": "You must belong to an organization",
            },
        )

    # Parse decision filter
    decision_enum = None
    if decision and decision in ["approved", "denied", "pending", "timeout"]:
        decision_enum = Decision(decision)

    # Build query
    query = InteractionRecordQuery(
        uapk_id=uapk_id,
        agent_id=agent_id,
        tool=tool,
        decision=decision_enum,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    # Get records
    record_service = InteractionRecordService(db)
    records_result = await record_service.list_records(
        org_id=user.default_org_id,
        query=query,
    )

    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "title": "UAPK Gateway - Interaction Logs",
            "user": user,
            "records": records_result.items,
            "total": records_result.total,
            "has_more": records_result.has_more,
            "offset": offset,
            "limit": limit,
            "uapk_id": uapk_id,
            "agent_id": agent_id,
            "tool": tool,
            "decision_filter": decision,
            "start_time": start_time,
            "end_time": end_time,
        },
    )


@router.get("/ui/logs/verify", response_class=HTMLResponse)
async def verify_logs(
    request: Request,
    user: UIUser,
    db: DbSession,
    uapk_id: str,
    start_time: datetime | None = Query(default=None, alias="from"),
    end_time: datetime | None = Query(default=None, alias="to"),
) -> Response:
    """Render the chain verification page."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    if not user.default_org_id:
        return RedirectResponse(url="/ui/logs", status_code=302)

    record_service = InteractionRecordService(db)
    verification = await record_service.verify_chain_integrity(
        org_id=user.default_org_id,
        uapk_id=uapk_id,
        start_time=start_time,
        end_time=end_time,
    )

    return templates.TemplateResponse(
        request=request,
        name="log_verify.html",
        context={
            "title": f"UAPK Gateway - Verify Chain: {uapk_id}",
            "user": user,
            "uapk_id": uapk_id,
            "verification": verification,
        },
    )


@router.get("/ui/logs/export", response_class=HTMLResponse)
async def export_logs(
    request: Request,
    user: UIUser,
    db: DbSession,
    uapk_id: str,
    format: str = "json",
    start_time: datetime | None = Query(default=None, alias="from"),
    end_time: datetime | None = Query(default=None, alias="to"),
) -> Response:
    """Export logs for download."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    if not user.default_org_id:
        return RedirectResponse(url="/ui/logs", status_code=302)

    record_service = InteractionRecordService(db)
    export_request = LogExportRequest(
        uapk_id=uapk_id,
        start_time=start_time,
        end_time=end_time,
        include_manifest=True,
        format=format,
    )

    bundle = await record_service.export_logs(
        org_id=user.default_org_id,
        request=export_request,
    )

    if format == "jsonl":
        # Return JSONL format
        def generate_jsonl():
            # Metadata line
            metadata = {
                "type": "metadata",
                "export_id": bundle.export_id,
                "exported_at": bundle.exported_at.isoformat(),
                "uapk_id": bundle.uapk_id,
                "org_id": bundle.org_id,
                "record_count": bundle.record_count,
                "chain_valid": bundle.chain_verification.is_valid,
            }
            yield json.dumps(metadata) + "\n"

            # Manifest
            if bundle.manifest_snapshot:
                yield json.dumps({"type": "manifest", **bundle.manifest_snapshot}) + "\n"

            # Records
            for record in bundle.records:
                yield json.dumps({"type": "record", **record}) + "\n"

        return StreamingResponse(
            generate_jsonl(),
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": f'attachment; filename="{uapk_id}-logs.jsonl"',
            },
        )
    else:
        # Return JSON format
        content = bundle.model_dump_json(indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{uapk_id}-logs.json"',
            },
        )


@router.get("/ui/logs/{record_id}", response_class=HTMLResponse)
async def log_detail(
    request: Request,
    record_id: str,
    user: UIUser,
    db: DbSession,
) -> Response:
    """Render the log detail page."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    if not user.default_org_id:
        return RedirectResponse(url="/ui/logs", status_code=302)

    record_service = InteractionRecordService(db)
    record = await record_service.get_record_by_id(record_id)

    if record is None or record.org_id != user.default_org_id:
        return RedirectResponse(url="/ui/logs", status_code=302)

    # Format JSON fields for display
    request_json = json.dumps(record.request, indent=2) if record.request else "{}"
    result_json = json.dumps(record.result, indent=2) if record.result else None
    policy_trace_json = record.policy_trace_json
    reasons_json = record.reasons_json
    risk_snapshot_json = record.risk_snapshot_json

    # Pretty print JSON strings
    try:
        policy_trace_json = json.dumps(json.loads(record.policy_trace_json), indent=2)
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        reasons_json = json.dumps(json.loads(record.reasons_json), indent=2)
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        if record.risk_snapshot_json:
            risk_snapshot_json = json.dumps(json.loads(record.risk_snapshot_json), indent=2)
    except (json.JSONDecodeError, TypeError):
        pass

    return templates.TemplateResponse(
        request=request,
        name="log_detail.html",
        context={
            "title": f"UAPK Gateway - Record {record_id}",
            "user": user,
            "record": record,
            "request_json": request_json,
            "result_json": result_json,
            "policy_trace_json": policy_trace_json,
            "reasons_json": reasons_json,
            "risk_snapshot_json": risk_snapshot_json,
        },
    )


@router.get("/ui/api-keys", response_class=HTMLResponse)
async def api_keys_page(request: Request, user: UIUser, db: DbSession) -> Response:
    """Render the API keys management page."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    # Get user's organizations and API keys
    auth_service = AuthService(db)
    user_with_orgs = await auth_service.get_user_with_orgs(user.id)

    api_key_service = ApiKeyService(db)
    org_ids = [org.org_id for org in user_with_orgs.organizations] if user_with_orgs else []
    api_keys = await api_key_service.list_user_api_keys(user.id, org_ids)

    return templates.TemplateResponse(
        request=request,
        name="api_keys.html",
        context={
            "title": "UAPK Gateway - API Keys",
            "user": user,
            "user_with_orgs": user_with_orgs,
            "api_keys": api_keys.items,
        },
    )


@router.get("/ui/manifests", response_class=HTMLResponse)
async def manifests_page(request: Request, user: UIUser) -> Response:
    """Render the manifests management page (placeholder)."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="manifests.html",
        context={"title": "UAPK Gateway - Manifests", "user": user},
    )


@router.get("/ui/approvals", response_class=HTMLResponse)
async def approvals_list(
    request: Request,
    user: UIUser,
    db: DbSession,
    status_filter: str | None = None,
) -> Response:
    """Render the approvals management page."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    if not user.default_org_id:
        return templates.TemplateResponse(
            request=request,
            name="approvals.html",
            context={
                "title": "UAPK Gateway - Approvals",
                "user": user,
                "error": "You must belong to an organization",
            },
        )

    # Parse status filter
    filter_status = None
    if status_filter and status_filter in ["pending", "approved", "denied", "expired"]:
        filter_status = ApprovalStatus(status_filter)

    # Get approvals
    approvals = await approval_service.list_approvals(
        db=db,
        org_id=user.default_org_id,
        status_filter=filter_status,
        limit=50,
    )

    # Get stats
    stats = await approval_service.get_approval_stats(db=db, org_id=user.default_org_id)

    return templates.TemplateResponse(
        request=request,
        name="approvals.html",
        context={
            "title": "UAPK Gateway - Approvals",
            "user": user,
            "approvals": approvals.items,
            "stats": stats,
            "status_filter": status_filter,
        },
    )


@router.get("/ui/approvals/{approval_id}", response_class=HTMLResponse)
async def approval_detail(
    request: Request,
    approval_id: str,
    user: UIUser,
    db: DbSession,
) -> Response:
    """Render the approval detail page."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    if not user.default_org_id:
        return RedirectResponse(url="/ui/approvals", status_code=302)

    approval = await approval_service.get_approval(
        db=db,
        org_id=user.default_org_id,
        approval_id=approval_id,
    )

    if approval is None:
        return RedirectResponse(url="/ui/approvals", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="approval_detail.html",
        context={
            "title": f"UAPK Gateway - Approval {approval_id}",
            "user": user,
            "approval": approval,
        },
    )


@router.post("/ui/approvals/{approval_id}/approve", response_class=HTMLResponse)
async def ui_approve_action(
    request: Request,
    approval_id: str,
    user: UIUser,
    db: DbSession,
    notes: str = Form(""),
) -> Response:
    """Handle approval form submission."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    if not user.default_org_id:
        return RedirectResponse(url="/ui/approvals", status_code=302)

    from app.schemas.approval import ApproveRequest

    try:
        result = await approval_service.approve_action(
            db=db,
            org_id=user.default_org_id,
            approval_id=approval_id,
            request=ApproveRequest(notes=notes if notes else None),
            user_id=str(user.id),
        )

        # Redirect back to detail page with success message
        return templates.TemplateResponse(
            request=request,
            name="approval_result.html",
            context={
                "title": "UAPK Gateway - Approval Result",
                "user": user,
                "result": result,
                "action": "approved",
            },
        )
    except ApprovalError as e:
        approval = await approval_service.get_approval(
            db=db,
            org_id=user.default_org_id,
            approval_id=approval_id,
        )
        return templates.TemplateResponse(
            request=request,
            name="approval_detail.html",
            context={
                "title": f"UAPK Gateway - Approval {approval_id}",
                "user": user,
                "approval": approval,
                "error": str(e),
            },
        )


@router.post("/ui/approvals/{approval_id}/deny", response_class=HTMLResponse)
async def ui_deny_action(
    request: Request,
    approval_id: str,
    user: UIUser,
    db: DbSession,
    reason: str = Form(""),
    notes: str = Form(""),
) -> Response:
    """Handle denial form submission."""
    if user is None:
        return RedirectResponse(url="/ui/login", status_code=302)

    if not user.default_org_id:
        return RedirectResponse(url="/ui/approvals", status_code=302)

    from app.schemas.approval import DenyRequest

    try:
        result = await approval_service.deny_action(
            db=db,
            org_id=user.default_org_id,
            approval_id=approval_id,
            request=DenyRequest(reason=reason if reason else None, notes=notes if notes else None),
            user_id=str(user.id),
        )

        return templates.TemplateResponse(
            request=request,
            name="approval_result.html",
            context={
                "title": "UAPK Gateway - Approval Result",
                "user": user,
                "result": result,
                "action": "denied",
            },
        )
    except ApprovalError as e:
        approval = await approval_service.get_approval(
            db=db,
            org_id=user.default_org_id,
            approval_id=approval_id,
        )
        return templates.TemplateResponse(
            request=request,
            name="approval_detail.html",
            context={
                "title": f"UAPK Gateway - Approval {approval_id}",
                "user": user,
                "approval": approval,
                "error": str(e),
            },
        )
