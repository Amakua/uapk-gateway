"""Logs API endpoints - audit log export and verification."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DbSession, RequireOrgViewer
from app.models.interaction_record import Decision
from app.schemas.interaction_record import (
    ChainVerificationResult,
    InteractionRecordList,
    InteractionRecordQuery,
    InteractionRecordResponse,
    LogExportBundle,
    LogExportRequest,
    LogExportResponse,
)
from app.services.interaction_record import InteractionRecordService

router = APIRouter(prefix="/orgs/{org_id}/logs", tags=["Audit Logs"])


@router.get("", response_model=InteractionRecordList)
async def list_logs(
    org_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgViewer],
    uapk_id: str | None = Query(default=None, description="Filter by UAPK ID"),
    agent_id: str | None = Query(default=None, description="Filter by agent ID"),
    action_type: str | None = Query(default=None, description="Filter by action type"),
    tool: str | None = Query(default=None, description="Filter by tool name"),
    decision: Decision | None = Query(default=None, description="Filter by decision"),
    start_time: datetime | None = Query(
        default=None, alias="from", description="Start of time range (inclusive)"
    ),
    end_time: datetime | None = Query(
        default=None, alias="to", description="End of time range (inclusive)"
    ),
    limit: int = Query(default=50, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> InteractionRecordList:
    """List interaction records (audit logs) for an organization.

    Supports filtering by UAPK ID, agent, action type, tool, decision, and time range.
    Records are returned in reverse chronological order.
    """
    record_service = InteractionRecordService(db)

    query = InteractionRecordQuery(
        uapk_id=uapk_id,
        agent_id=agent_id,
        action_type=action_type,
        tool=tool,
        decision=decision,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    return await record_service.list_records(org_id=org_id, query=query)


@router.get("/{record_id}", response_model=InteractionRecordResponse)
async def get_log_record(
    org_id: UUID,
    record_id: str,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgViewer],
) -> InteractionRecordResponse:
    """Get a specific interaction record by ID.

    Returns the full record including request details, policy trace,
    result, and hash chain information.
    """
    record_service = InteractionRecordService(db)
    record = await record_service.get_record_by_id(record_id)

    if record is None or record.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )

    return InteractionRecordResponse.model_validate(record)


@router.get("/verify/{uapk_id}", response_model=ChainVerificationResult)
async def verify_chain(
    org_id: UUID,
    uapk_id: str,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgViewer],
    start_time: datetime | None = Query(
        default=None, alias="from", description="Start of time range"
    ),
    end_time: datetime | None = Query(
        default=None, alias="to", description="End of time range"
    ),
) -> ChainVerificationResult:
    """Verify the integrity of the hash chain for a UAPK.

    Performs the following checks:
    - Hash chain continuity (each record links to previous)
    - Record hash integrity (recompute and compare)
    - Signature validity (Ed25519 verification)

    Returns verification results including any errors found.
    """
    record_service = InteractionRecordService(db)

    return await record_service.verify_chain_integrity(
        org_id=org_id,
        uapk_id=uapk_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.post("/export", response_model=LogExportResponse)
async def create_export(
    org_id: UUID,
    request: LogExportRequest,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgViewer],
) -> LogExportResponse:
    """Create a log export request.

    Returns export metadata including chain verification status.
    Use the download endpoint to get the full export bundle.
    """
    record_service = InteractionRecordService(db)

    return await record_service.create_export_response(
        org_id=org_id,
        request=request,
    )


@router.post("/export/download", response_model=LogExportBundle)
async def download_export(
    org_id: UUID,
    request: LogExportRequest,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgViewer],
) -> LogExportBundle:
    """Download a complete log export bundle.

    Returns a JSON bundle containing:
    - All records in chronological order
    - Chain verification results
    - Optional manifest snapshot

    For JSONL format, use the /export/jsonl endpoint.
    """
    record_service = InteractionRecordService(db)

    return await record_service.export_logs(
        org_id=org_id,
        request=request,
    )


@router.post("/export/jsonl")
async def download_export_jsonl(
    org_id: UUID,
    request: LogExportRequest,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgViewer],
) -> StreamingResponse:
    """Download log export as JSONL (one record per line).

    Returns a streaming response with records in JSONL format.
    Each line is a complete JSON object representing one interaction record.

    Suitable for large exports and log processing tools.
    """
    import json

    record_service = InteractionRecordService(db)
    bundle = await record_service.export_logs(
        org_id=org_id,
        request=request,
    )

    async def generate_jsonl():
        # First line: metadata
        metadata = {
            "type": "metadata",
            "export_id": bundle.export_id,
            "exported_at": bundle.exported_at.isoformat(),
            "uapk_id": bundle.uapk_id,
            "org_id": bundle.org_id,
            "record_count": bundle.record_count,
            "chain_valid": bundle.chain_verification.is_valid,
            "verification_errors": bundle.chain_verification.errors,
        }
        yield json.dumps(metadata) + "\n"

        # Manifest snapshot if included
        if bundle.manifest_snapshot:
            manifest_line = {
                "type": "manifest",
                **bundle.manifest_snapshot,
            }
            yield json.dumps(manifest_line) + "\n"

        # Records
        for record in bundle.records:
            record_line = {"type": "record", **record}
            yield json.dumps(record_line) + "\n"

    return StreamingResponse(
        generate_jsonl(),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="{bundle.uapk_id}-logs.jsonl"',
        },
    )
