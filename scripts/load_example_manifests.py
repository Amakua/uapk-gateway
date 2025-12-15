#!/usr/bin/env python3
"""
Load 47er example manifests into the UAPK Gateway database.

This script loads pre-built micro-business agent templates from the
examples/47ers directory into the gateway for demonstration or as
starting points for customization.

Usage:
    python scripts/load_example_manifests.py [OPTIONS]

Options:
    --all               Load all templates
    --template NAME     Load a specific template by ID
    --list              List available templates
    --var KEY=VALUE     Set placeholder values (can be repeated)
    --org-id UUID       Organization ID to load manifests into
    --api-url URL       Gateway API URL (default: http://localhost:8000)
    --token TOKEN       Bearer token for authentication
    --demo              Enable demo/mock mode for connectors
    --dry-run           Print manifests without loading

Examples:
    # List all available templates
    python scripts/load_example_manifests.py --list

    # Load all templates with default placeholders
    python scripts/load_example_manifests.py --all --org-id $ORG_ID --token $TOKEN

    # Load specific template with custom values
    python scripts/load_example_manifests.py \\
        --template kyc-onboarding \\
        --var ORG_SLUG=acme-corp \\
        --var ORG_DOMAIN=acme.com \\
        --org-id $ORG_ID --token $TOKEN
"""

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# Default placeholder values
DEFAULT_VARS = {
    "ORG_SLUG": "demo-org",
    "ORG_DOMAIN": "demo.example.com",
    "ORG_NAME": "Demo Organization",
    "DEFAULT_FROM_EMAIL": "noreply@demo.example.com",
    "DEMO_MODE": "true",
    "SMTP_HOST": "localhost",
    "SMTP_USERNAME": "demo",
    "CRM_API_URL": "https://api.demo.example.com",
    "CRM_CLIENT_ID": "demo-client",
    "CRM_TOKEN_URL": "https://api.demo.example.com/oauth/token",
}


def get_examples_dir() -> Path:
    """Get the path to the examples/47ers directory."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    examples_dir = repo_root / "examples" / "47ers"

    if not examples_dir.exists():
        print(f"Error: Examples directory not found: {examples_dir}", file=sys.stderr)
        sys.exit(1)

    return examples_dir


def load_index(examples_dir: Path) -> dict:
    """Load the 47ers index file."""
    index_path = examples_dir / "index.json"

    if not index_path.exists():
        print(f"Error: Index file not found: {index_path}", file=sys.stderr)
        sys.exit(1)

    with open(index_path) as f:
        return json.load(f)


def list_templates(index: dict) -> None:
    """List all available templates."""
    print("\n47ers Library - Available Templates")
    print("=" * 50)

    for category_id, category in index.get("categories", {}).items():
        print(f"\n{category['name']}:")
        print("-" * 40)

        templates_in_category = [
            t for t in index.get("templates", [])
            if t.get("category") == category_id
        ]

        for template in templates_in_category:
            print(f"  {template['id']}")
            print(f"    {template['name']}")
            print(f"    {template['description']}")
            print(f"    Complexity: {template.get('complexity', 'unknown')}")
            print()


def substitute_placeholders(content: str, variables: dict[str, str]) -> str:
    """Substitute {{PLACEHOLDER}} patterns with values."""
    def replace(match):
        key = match.group(1)
        return variables.get(key, match.group(0))

    return re.sub(r'\{\{(\w+)\}\}', replace, content)


def load_template(
    examples_dir: Path,
    template_path: str,
    variables: dict[str, str]
) -> dict:
    """Load and process a single template."""
    full_path = examples_dir / template_path

    if not full_path.exists():
        raise FileNotFoundError(f"Template not found: {full_path}")

    # Read raw content
    with open(full_path) as f:
        content = f.read()

    # Substitute placeholders
    content = substitute_placeholders(content, variables)

    # Parse JSON
    return json.loads(content)


def convert_to_manifest(template: dict) -> dict:
    """Convert a 47er template to a standard UAPK manifest."""
    # Extract the core manifest fields, removing template-specific metadata
    manifest = {
        "version": template.get("version", "1.0"),
        "agent": template.get("agent", {}),
        "capabilities": template.get("capabilities", {}),
        "constraints": template.get("constraints", {}),
        "metadata": template.get("metadata", {}),
    }

    # Add constraints from action_types if present
    if "action_types" in template:
        action_types = template["action_types"]
        require_approval = []

        for action_name, action_config in action_types.items():
            if action_config.get("require_approval"):
                # Add the tools that require approval
                tools = action_config.get("tools", [])
                require_approval.extend(tools)

        if require_approval:
            if "require_human_approval" not in manifest["constraints"]:
                manifest["constraints"]["require_human_approval"] = []
            manifest["constraints"]["require_human_approval"].extend(require_approval)
            # Deduplicate
            manifest["constraints"]["require_human_approval"] = list(
                set(manifest["constraints"]["require_human_approval"])
            )

    return manifest


def api_request(
    method: str,
    url: str,
    token: str,
    data: dict | None = None
) -> dict:
    """Make an API request using available HTTP library."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    if HAS_HTTPX:
        with httpx.Client() as client:
            if method == "GET":
                response = client.get(url, headers=headers)
            elif method == "POST":
                response = client.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

    elif HAS_REQUESTS:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    else:
        raise RuntimeError(
            "No HTTP library available. Install httpx or requests:\n"
            "  pip install httpx\n"
            "  pip install requests"
        )


def load_manifest_to_gateway(
    api_url: str,
    org_id: str,
    token: str,
    manifest: dict,
    template_name: str,
    dry_run: bool = False
) -> dict | None:
    """Load a manifest into the gateway."""
    if dry_run:
        print(f"\n[DRY RUN] Would load manifest for: {template_name}")
        print(json.dumps(manifest, indent=2))
        return None

    url = f"{api_url}/api/v1/orgs/{org_id}/manifests"

    try:
        result = api_request("POST", url, token, manifest)
        print(f"  ✓ Loaded: {template_name} -> {result.get('manifest_id', 'unknown')}")
        return result
    except Exception as e:
        print(f"  ✗ Failed: {template_name} - {e}", file=sys.stderr)
        return None


def print_demo_commands(templates_loaded: list[dict], api_url: str, org_id: str) -> None:
    """Print curl commands to interact with loaded manifests."""
    print("\n" + "=" * 60)
    print("DEMO COMMANDS")
    print("=" * 60)
    print("\nSet your token:")
    print('  export TOKEN="your-bearer-token"')
    print(f'  export ORG_ID="{org_id}"')
    print(f'  export API_URL="{api_url}"')

    print("\n--- List Manifests ---")
    print(f'''curl "$API_URL/api/v1/orgs/$ORG_ID/manifests" \\
  -H "Authorization: Bearer $TOKEN"''')

    if templates_loaded:
        # Pick the first template for examples
        first = templates_loaded[0]
        agent_id = first.get("agent", {}).get("id", "demo-agent")

        print(f"\n--- Execute Action ({agent_id}) ---")
        print(f'''curl -X POST "$API_URL/api/v1/gateway/execute" \\
  -H "X-API-Key: $API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "uapk_id": "{agent_id}",
    "agent_id": "{agent_id}",
    "action": {{
      "type": "email",
      "tool": "send",
      "params": {{
        "to": "test@example.com",
        "subject": "Test",
        "body": "Demo message"
      }}
    }}
  }}'
''')

        print("\n--- View Pending Approvals ---")
        print(f'''curl "$API_URL/api/v1/orgs/$ORG_ID/approvals?status=pending" \\
  -H "Authorization: Bearer $TOKEN"''')

        print("\n--- Verify Log Chain ---")
        print(f'''curl "$API_URL/api/v1/orgs/$ORG_ID/logs/verify/{agent_id}" \\
  -H "Authorization: Bearer $TOKEN"''')

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Load 47er example manifests into UAPK Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--all", action="store_true",
        help="Load all templates"
    )
    parser.add_argument(
        "--template", type=str,
        help="Load a specific template by ID"
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_templates",
        help="List available templates"
    )
    parser.add_argument(
        "--var", action="append", default=[],
        help="Set placeholder value (KEY=VALUE)"
    )
    parser.add_argument(
        "--org-id", type=str,
        help="Organization ID"
    )
    parser.add_argument(
        "--api-url", type=str, default="http://localhost:8000",
        help="Gateway API URL"
    )
    parser.add_argument(
        "--token", type=str,
        help="Bearer token for authentication"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Enable demo mode"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print manifests without loading"
    )

    args = parser.parse_args()

    # Get examples directory
    examples_dir = get_examples_dir()

    # Load index
    index = load_index(examples_dir)

    # Handle --list
    if args.list_templates:
        list_templates(index)
        return

    # Require --all or --template
    if not args.all and not args.template:
        parser.print_help()
        print("\nError: Specify --all or --template NAME", file=sys.stderr)
        sys.exit(1)

    # Check required args for loading
    if not args.dry_run and (not args.org_id or not args.token):
        print("Error: --org-id and --token required (unless --dry-run)", file=sys.stderr)
        sys.exit(1)

    # Build variables dict
    variables = DEFAULT_VARS.copy()
    for var in args.var:
        if "=" not in var:
            print(f"Error: Invalid --var format: {var}", file=sys.stderr)
            sys.exit(1)
        key, value = var.split("=", 1)
        variables[key] = value

    if args.demo:
        variables["DEMO_MODE"] = "true"

    # Determine templates to load
    if args.all:
        templates_to_load = index.get("templates", [])
    else:
        templates_to_load = [
            t for t in index.get("templates", [])
            if t["id"] == args.template or t["id"].endswith(args.template)
        ]

        if not templates_to_load:
            print(f"Error: Template not found: {args.template}", file=sys.stderr)
            print("\nAvailable templates:")
            for t in index.get("templates", []):
                print(f"  - {t['id']}")
            sys.exit(1)

    # Load templates
    print(f"\nLoading {len(templates_to_load)} template(s)...")
    print("-" * 40)

    loaded = []
    for template_info in templates_to_load:
        try:
            template = load_template(
                examples_dir,
                template_info["path"],
                variables
            )
            manifest = convert_to_manifest(template)

            result = load_manifest_to_gateway(
                args.api_url,
                args.org_id or "demo-org",
                args.token or "demo-token",
                manifest,
                template_info["name"],
                args.dry_run
            )

            if result or args.dry_run:
                loaded.append(template)

        except Exception as e:
            print(f"  ✗ Error loading {template_info['id']}: {e}", file=sys.stderr)

    # Summary
    print("-" * 40)
    print(f"Loaded: {len(loaded)}/{len(templates_to_load)}")

    # Print demo commands
    if loaded and not args.dry_run:
        print_demo_commands(loaded, args.api_url, args.org_id)


if __name__ == "__main__":
    main()
