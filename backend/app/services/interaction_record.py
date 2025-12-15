"""Interaction record service - audit log management with hash chain verification."""

import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import (
    canonicalize_json,
    compute_record_hash,
    verify_hash_chain,
    verify_record_signature,
)
from app.core.logging import get_logger
from app.models.interaction_record import Decision, InteractionRecord
from app.models.uapk_manifest import UapkManifest
from app.schemas.interaction_record import (
    ChainVerificationResult,
    InteractionRecordList,
    InteractionRecordQuery,
    InteractionRecordResponse,
    InteractionRecordSummary,
    LogExportBundle,
    LogExportRequest,
    LogExportResponse,
)

logger = get_logger("service.interaction_record")


def generate_export_id() -> str:
    """Generate a unique export ID."""
    return f"export-{secrets.token_hex(12)}"


class InteractionRecordService:
    """Service for managing interaction records (audit logs)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_record_by_id(
        self,
        record_id: str,
    ) -> InteractionRecord | None:
        """Get an interaction record by its record_id."""
        result = await self.db.execute(
            select(InteractionRecord).where(InteractionRecord.record_id == record_id)
        )
        return result.scalar_one_or_none()

    async def list_records(
        self,
        org_id: UUID,
        query: InteractionRecordQuery | None = None,
    ) -> InteractionRecordList:
        """List interaction records for an organization with filtering."""
        stmt = select(InteractionRecord).where(InteractionRecord.org_id == org_id)

        if query:
            if query.uapk_id:
                stmt = stmt.where(InteractionRecord.uapk_id == query.uapk_id)
            if query.agent_id:
                stmt = stmt.where(InteractionRecord.agent_id == query.agent_id)
            if query.action_type:
                stmt = stmt.where(InteractionRecord.action_type == query.action_type)
            if query.tool:
                stmt = stmt.where(InteractionRecord.tool == query.tool)
            if query.decision:
                stmt = stmt.where(InteractionRecord.decision == query.decision)
            if query.start_time:
                stmt = stmt.where(InteractionRecord.created_at >= query.start_time)
            if query.end_time:
                stmt = stmt.where(InteractionRecord.created_at <= query.end_time)

        # Get total count
        count_query = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        limit = query.limit if query else 50
        offset = query.offset if query else 0

        stmt = (
            stmt.order_by(desc(InteractionRecord.created_at))
            .offset(offset)
            .limit(limit + 1)
        )

        result = await self.db.execute(stmt)
        records = result.scalars().all()

        # Check if there are more records
        has_more = len(records) > limit
        if has_more:
            records = records[:limit]

        return InteractionRecordList(
            items=[InteractionRecordSummary.model_validate(r) for r in records],
            total=total,
            has_more=has_more,
        )

    async def list_records_by_uapk(
        self,
        org_id: UUID,
        uapk_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[InteractionRecord]:
        """List records for a specific UAPK in chronological order."""
        stmt = select(InteractionRecord).where(
            InteractionRecord.org_id == org_id,
            InteractionRecord.uapk_id == uapk_id,
        )

        if start_time:
            stmt = stmt.where(InteractionRecord.created_at >= start_time)
        if end_time:
            stmt = stmt.where(InteractionRecord.created_at <= end_time)

        stmt = stmt.order_by(asc(InteractionRecord.created_at)).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def verify_chain_integrity(
        self,
        org_id: UUID,
        uapk_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ChainVerificationResult:
        """Verify the integrity of the hash chain for a UAPK.

        Checks:
        - Hash chain continuity (each record links to previous)
        - Record hash integrity (recompute and compare)
        - Signature validity (Ed25519 verification)
        """
        records = await self.list_records_by_uapk(
            org_id=org_id,
            uapk_id=uapk_id,
            start_time=start_time,
            end_time=end_time,
        )

        if not records:
            return ChainVerificationResult(
                is_valid=True,
                record_count=0,
                verified_at=datetime.now(UTC),
            )

        # Convert to dicts for verification
        record_dicts = []
        for record in records:
            record_dicts.append({
                "record_id": record.record_id,
                "org_id": str(record.org_id),
                "uapk_id": record.uapk_id,
                "agent_id": record.agent_id,
                "action_type": record.action_type,
                "tool": record.tool,
                "request_hash": record.request_hash,
                "decision": record.decision.value,
                "reasons_json": record.reasons_json,
                "policy_trace_json": record.policy_trace_json,
                "result_hash": record.result_hash,
                "previous_record_hash": record.previous_record_hash,
                "record_hash": record.record_hash,
                "gateway_signature": record.gateway_signature,
                "created_at": record.created_at,
            })

        # Verify the chain
        is_valid, errors = verify_hash_chain(record_dicts)

        return ChainVerificationResult(
            is_valid=is_valid,
            record_count=len(records),
            first_record_id=records[0].record_id if records else None,
            last_record_id=records[-1].record_id if records else None,
            first_record_hash=records[0].record_hash if records else None,
            last_record_hash=records[-1].record_hash if records else None,
            errors=errors,
            verified_at=datetime.now(UTC),
        )

    async def export_logs(
        self,
        org_id: UUID,
        request: LogExportRequest,
    ) -> LogExportBundle:
        """Export logs for a UAPK with verification and optional manifest snapshot.

        Creates a complete export bundle containing:
        - All records in chronological order
        - Chain verification results
        - Optional manifest snapshot
        """
        export_id = generate_export_id()

        # Get records
        records = await self.list_records_by_uapk(
            org_id=org_id,
            uapk_id=request.uapk_id,
            start_time=request.start_time,
            end_time=request.end_time,
        )

        # Verify chain integrity
        verification = await self.verify_chain_integrity(
            org_id=org_id,
            uapk_id=request.uapk_id,
            start_time=request.start_time,
            end_time=request.end_time,
        )

        # Get manifest snapshot if requested
        manifest_snapshot: dict[str, Any] | None = None
        if request.include_manifest:
            manifest_result = await self.db.execute(
                select(UapkManifest).where(
                    UapkManifest.org_id == org_id,
                    UapkManifest.uapk_id == request.uapk_id,
                )
            )
            manifest = manifest_result.scalar_one_or_none()
            if manifest:
                manifest_snapshot = {
                    "uapk_id": manifest.uapk_id,
                    "version": manifest.version,
                    "manifest_hash": manifest.manifest_hash,
                    "status": manifest.status.value,
                    "manifest_json": manifest.manifest_json,
                    "created_at": manifest.created_at.isoformat(),
                }

        # Build record list
        record_list = []
        for record in records:
            record_list.append({
                "record_id": record.record_id,
                "org_id": str(record.org_id),
                "uapk_id": record.uapk_id,
                "agent_id": record.agent_id,
                "action_type": record.action_type,
                "tool": record.tool,
                "request": record.request,
                "request_hash": record.request_hash,
                "decision": record.decision.value,
                "decision_reason": record.decision_reason,
                "reasons_json": record.reasons_json,
                "policy_trace_json": record.policy_trace_json,
                "risk_snapshot_json": record.risk_snapshot_json,
                "result": record.result,
                "result_hash": record.result_hash,
                "duration_ms": record.duration_ms,
                "previous_record_hash": record.previous_record_hash,
                "record_hash": record.record_hash,
                "gateway_signature": record.gateway_signature,
                "created_at": record.created_at.isoformat(),
            })

        # Determine time range
        time_range: dict[str, datetime | None] = {
            "start": records[0].created_at if records else None,
            "end": records[-1].created_at if records else None,
        }

        logger.info(
            "logs_exported",
            export_id=export_id,
            org_id=str(org_id),
            uapk_id=request.uapk_id,
            record_count=len(records),
            chain_valid=verification.is_valid,
        )

        return LogExportBundle(
            export_id=export_id,
            exported_at=datetime.now(UTC),
            uapk_id=request.uapk_id,
            org_id=str(org_id),
            record_count=len(records),
            time_range=time_range,
            chain_verification=verification,
            manifest_snapshot=manifest_snapshot,
            records=record_list,
        )

    async def create_export_response(
        self,
        org_id: UUID,
        request: LogExportRequest,
    ) -> LogExportResponse:
        """Create a summary response for an export request."""
        export_id = generate_export_id()

        # Get records for summary
        records = await self.list_records_by_uapk(
            org_id=org_id,
            uapk_id=request.uapk_id,
            start_time=request.start_time,
            end_time=request.end_time,
        )

        # Verify chain
        verification = await self.verify_chain_integrity(
            org_id=org_id,
            uapk_id=request.uapk_id,
            start_time=request.start_time,
            end_time=request.end_time,
        )

        return LogExportResponse(
            export_id=export_id,
            uapk_id=request.uapk_id,
            record_count=len(records),
            start_time=records[0].created_at if records else None,
            end_time=records[-1].created_at if records else None,
            first_record_hash=records[0].record_hash if records else None,
            last_record_hash=records[-1].record_hash if records else None,
            chain_valid=verification.is_valid,
        )
