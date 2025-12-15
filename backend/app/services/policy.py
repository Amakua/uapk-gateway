"""Policy service - CRUD and evaluation of policies."""

import fnmatch
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import Policy, PolicyScope, PolicyType
from app.schemas.policy import PolicyCreate, PolicyList, PolicyResponse, PolicyUpdate


class PolicyService:
    """Service for managing and evaluating policies."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_policy(
        self,
        data: PolicyCreate,
        user_id: UUID | None = None,
    ) -> Policy:
        """Create a new policy."""
        policy = Policy(
            org_id=data.org_id,
            name=data.name,
            description=data.description,
            policy_type=data.policy_type,
            scope=data.scope,
            priority=data.priority,
            rules=data.rules.model_dump(mode="json"),
            enabled=data.enabled,
            created_by_user_id=user_id,
        )

        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def get_policy_by_id(self, policy_id: UUID) -> Policy | None:
        """Get a policy by its ID."""
        result = await self.db.execute(select(Policy).where(Policy.id == policy_id))
        return result.scalar_one_or_none()

    async def list_policies(
        self,
        org_id: UUID,
        enabled_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> PolicyList:
        """List policies for an organization."""
        query = select(Policy).where(Policy.org_id == org_id)

        if enabled_only:
            query = query.where(Policy.enabled.is_(True))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get items with pagination, ordered by priority (highest first)
        query = query.order_by(Policy.priority.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        policies = result.scalars().all()

        return PolicyList(
            items=[PolicyResponse.model_validate(p) for p in policies],
            total=total,
        )

    async def get_applicable_policies(
        self,
        org_id: UUID,
        action: str,
        agent_id: str,
    ) -> list[Policy]:
        """Get policies applicable to an action request, ordered by priority."""
        result = await self.db.execute(
            select(Policy)
            .where(
                Policy.org_id == org_id,
                Policy.enabled.is_(True),
            )
            .order_by(Policy.priority.desc())
        )
        all_policies = result.scalars().all()

        # Filter policies that match the action and agent
        applicable = []
        for policy in all_policies:
            if self._policy_matches(policy, action, agent_id):
                applicable.append(policy)

        return applicable

    def _policy_matches(self, policy: Policy, action: str, agent_id: str) -> bool:
        """Check if a policy matches the given action and agent."""
        rules = policy.rules

        # Check action pattern match
        action_pattern = rules.get("action_pattern")
        if action_pattern:
            if not fnmatch.fnmatch(action, action_pattern):
                return False

        # Check agent ID match
        agent_ids = rules.get("agent_ids")
        if agent_ids:
            if agent_id not in agent_ids:
                return False

        # Check scope
        if policy.scope == PolicyScope.ACTION and not action_pattern:
            return False
        if policy.scope == PolicyScope.AGENT and not agent_ids:
            return False

        return True

    async def update_policy(
        self,
        policy_id: UUID,
        data: PolicyUpdate,
    ) -> Policy | None:
        """Update a policy."""
        policy = await self.get_policy_by_id(policy_id)
        if policy is None:
            return None

        if data.name is not None:
            policy.name = data.name
        if data.description is not None:
            policy.description = data.description
        if data.policy_type is not None:
            policy.policy_type = data.policy_type
        if data.scope is not None:
            policy.scope = data.scope
        if data.priority is not None:
            policy.priority = data.priority
        if data.rules is not None:
            policy.rules = data.rules.model_dump(mode="json")
        if data.enabled is not None:
            policy.enabled = data.enabled

        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def delete_policy(self, policy_id: UUID) -> bool:
        """Delete a policy. Returns True if deleted."""
        policy = await self.get_policy_by_id(policy_id)
        if policy is None:
            return False

        await self.db.delete(policy)
        await self.db.commit()
        return True


class PolicyEvaluator:
    """Evaluates policies against action requests."""

    def __init__(self, policy_service: PolicyService) -> None:
        self.policy_service = policy_service

    async def evaluate(
        self,
        org_id: UUID,
        action: str,
        agent_id: str,
        capabilities: list[str],
        parameters: dict,
    ) -> tuple[PolicyType | None, list[dict], str | None]:
        """Evaluate policies for an action request.

        Returns:
            - Final decision (PolicyType.ALLOW, DENY, or REQUIRE_APPROVAL)
            - List of policy evaluation results
            - Reason for the decision
        """
        # First check if the action is in the agent's capabilities
        if not self._capability_allows_action(capabilities, action):
            return (
                PolicyType.DENY,
                [],
                f"Action '{action}' not in granted capabilities",
            )

        policies = await self.policy_service.get_applicable_policies(
            org_id, action, agent_id
        )

        evaluations = []
        final_decision = PolicyType.ALLOW  # Default to allow if no policies deny
        decision_reason = "No applicable policies deny the action"

        for policy in policies:
            result = self._evaluate_policy(policy, action, agent_id, parameters)
            evaluations.append({
                "policy_id": str(policy.id),
                "policy_name": policy.name,
                "result": result["result"],
                "reason": result.get("reason"),
            })

            # First deny wins
            if policy.policy_type == PolicyType.DENY and result["result"] == "fail":
                return (
                    PolicyType.DENY,
                    evaluations,
                    f"Denied by policy: {policy.name}",
                )

            # Track if any policy requires approval
            if policy.policy_type == PolicyType.REQUIRE_APPROVAL and result["result"] == "fail":
                final_decision = PolicyType.REQUIRE_APPROVAL
                decision_reason = f"Requires approval: {policy.name}"

        return final_decision, evaluations, decision_reason

    def _capability_allows_action(self, capabilities: list[str], action: str) -> bool:
        """Check if the action is allowed by any of the capabilities."""
        action_parts = action.split(":")
        if len(action_parts) != 2:
            return False

        action_domain, action_operation = action_parts

        for cap in capabilities:
            cap_parts = cap.split(":")
            if len(cap_parts) != 2:
                continue

            cap_domain, cap_operation = cap_parts

            # Check domain match
            if cap_domain != action_domain and cap_domain != "*":
                continue

            # Check operation match (supports * wildcard)
            if cap_operation == "*" or cap_operation == action_operation:
                return True

            # Support glob pattern matching
            if fnmatch.fnmatch(action_operation, cap_operation):
                return True

        return False

    def _evaluate_policy(
        self,
        policy: Policy,
        action: str,
        agent_id: str,
        parameters: dict,
    ) -> dict:
        """Evaluate a single policy.

        Returns {"result": "pass"|"fail"|"skip", "reason": ...}
        """
        rules = policy.rules

        # Check parameter constraints
        param_constraints = rules.get("parameters")
        if param_constraints:
            for key, constraint in param_constraints.items():
                if key not in parameters:
                    if constraint.get("required"):
                        return {
                            "result": "fail",
                            "reason": f"Missing required parameter: {key}",
                        }
                    continue

                value = parameters[key]

                # Check max length
                if "max_length" in constraint and len(str(value)) > constraint["max_length"]:
                    return {
                        "result": "fail",
                        "reason": f"Parameter '{key}' exceeds max length",
                    }

                # Check allowed values
                if "allowed_values" in constraint and value not in constraint["allowed_values"]:
                    return {
                        "result": "fail",
                        "reason": f"Parameter '{key}' has disallowed value",
                    }

        # If we get here, the policy conditions are met
        if policy.policy_type == PolicyType.ALLOW:
            return {"result": "pass", "reason": "Allowed by policy"}
        elif policy.policy_type == PolicyType.DENY:
            return {"result": "fail", "reason": "Denied by policy"}
        else:  # REQUIRE_APPROVAL
            return {"result": "fail", "reason": "Requires human approval"}
