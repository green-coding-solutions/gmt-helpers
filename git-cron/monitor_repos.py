#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import sys
from typing import Any, Dict, Optional

from urllib.parse import urlparse, quote_plus

import requests
import time
from datetime import datetime
import builtins

original_print = print

def print_with_timestamp(*args, **kwargs):
    """Print with timestamp prefix."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    args = (f"[{timestamp}]",) + args
    original_print(*args, **kwargs)

builtins.print = print_with_timestamp

# ---- GMT submit ----

class APIEmptyResponse204(Exception):
    pass


class APIError(Exception):
    pass

@dataclass
class APIClient:
    api_url: str
    token: Optional[str] = None
    timeout: int = 30

    def _auth_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Authentication"] = self.token
        return headers

    def _request(self, path: str, method: str = "GET", json_body: Optional[Dict[str, Any]] = None,) -> Optional[Dict[str, Any]]:
        url = self.api_url.rstrip("/") + path

        resp = requests.request(
            method=method.upper(),
            url=url,
            json=json_body if json_body is not None else None,
            headers=self._auth_headers(),
            timeout=self.timeout,
        )

        if resp.status_code == 204:
            raise APIEmptyResponse204("No data (HTTP 204)")
        if resp.status_code == 202:
            return None  # Accepted

        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            try:
                data = resp.json()
            except Exception:
                raise APIError(f"HTTP {resp.status_code}: {resp.text}") from e
            err = data.get("err", data)
            raise APIError(f"HTTP {resp.status_code}: {err}") from e

        try:
            data = resp.json()
        except ValueError as e:
            raise APIError(f"Expected JSON but got: {resp.text[:200]}...") from e

        if isinstance(data, dict) and data.get("success") is not True:
            err = data.get("err")
            if isinstance(err, list) and err:
                first = err[0]
                msg = (first.get("msg") if isinstance(first, dict) else str(first)) or str(err)
                raise APIError(msg)
            raise APIError(str(err))
        
        return data

    def submit_software(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Trim string values
        for k, v in list(payload.items()):
            if isinstance(v, str):
                payload[k] = v.strip()
        return self._request("/v1/software/add", method="POST", json_body=payload)


# ---- Git helpers: get latest commit for GitHub / GitLab ----

class GitError(Exception):
    pass


def get_latest_commit(repo_url: str, branch: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    """
    For a GitHub or GitLab repo URL, return the latest commit hash (str) on the
    requested branch (default branch if none given), or None if not found.

    GitHub:
      https://github.com/{owner}/{repo}
      -> GET https://api.github.com/repos/{owner}/{repo}/commits?per_page=1[&sha=branch]
         -> data[0]['sha']

    GitLab:
      https://gitlab.com/{group}/{project}
      -> GET https://gitlab.com/api/v4/projects/{urlencoded(group/project)}/repository/commits?per_page=1[&ref_name=branch]
         -> data[0]['id']
    """
    parsed = urlparse(repo_url)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if not path:
        raise GitError(f"Repo URL seems incomplete: {repo_url}")

    path_parts = [part for part in path.split("/") if part]
    if not path_parts:
        raise GitError(f"Repo URL seems incomplete: {repo_url}")

    if "github.com" in host:
        # path = owner/repo[/...]; we only need first two segments
        if len(path_parts) < 2:
            raise GitError(f"Cannot parse GitHub repo from URL: {repo_url}")
        owner, repo = path_parts[0], path_parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        if not repo:
            raise GitError(f"Cannot parse GitHub repo from URL: {repo_url}")
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {"per_page": 1}
        if branch:
            params["sha"] = branch
        try:
            resp = requests.get(api_url, params=params, timeout=timeout)
        except Exception as exc:
            raise GitError(f"Request to GitHub API failed: {exc}") from exc
        if resp.status_code != 200:
            raise GitError(f"GitHub API error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if not data:
            return None
        return data[0].get("sha")

    elif "gitlab" in host:
        # works for gitlab.com and self-hosted GitLab domains containing "gitlab"
        normalized_parts = list(path_parts)
        if normalized_parts[-1].endswith(".git"):
            normalized_parts[-1] = normalized_parts[-1][:-4]
        normalized_project = "/".join(part for part in normalized_parts if part)
        if not normalized_project:
            raise GitError(f"Cannot parse GitLab project from URL: {repo_url}")
        project = quote_plus(normalized_project)
        api_root = f"{parsed.scheme}://{parsed.netloc}"
        api_url = f"{api_root}/api/v4/projects/{project}/repository/commits"
        params = {"per_page": 1}
        if branch:
            params["ref_name"] = branch
        try:
            resp = requests.get(api_url, params=params, timeout=timeout)
        except Exception as exc:
            raise GitError(f"Request to GitLab API failed: {exc}") from exc
        if resp.status_code != 200:
            raise GitError(f"GitLab API error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if not data:
            return None
        # GitLab uses "id" for commit hash
        return data[0].get("id")

    else:
        raise GitError(f"Unsupported git host in URL: {repo_url} (only GitHub/GitLab supported)")


# ---- State helpers ----

def load_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


# ---- Main monitoring logic ----

def build_payload_for_run(default_name: str, run_cfg: Dict[str, Any], latest_commit: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "name": run_cfg.get("name", default_name),
        "repo_url": run_cfg["repo_to_run"],
        "machine_id": run_cfg["machine_id"],
        "branch": run_cfg.get("branch_to_run", "main"),
        "filename": run_cfg.get("filename", "usage_scenario.yml"),
        "schedule_mode": "one-off",
    }

    if run_cfg.get("email"):
        payload["email"] = run_cfg["email"]

    vars_cfg = run_cfg.get("variables")
    if isinstance(vars_cfg, dict) and vars_cfg:
        resolved_vars: Dict[str, Any] = {}
        for key, value in vars_cfg.items():
            resolved_vars[key] = latest_commit if value == "__GIT_HASH__" else value
        payload["usage_scenario_variables"] = resolved_vars

    return payload


def process_repo(client: APIClient, repo_cfg: Dict[str, Any], state: Dict[str, Any], global_timeout: int) -> None:
    
    repo_to_watch: str = repo_cfg["repo_to_watch"]
    name: str = repo_cfg.get("name", repo_to_watch)
    branch_to_watch: Optional[str] = repo_cfg.get("branch_to_watch", "main")

    print(f"Checking repo: {name} ({repo_to_watch}:{branch_to_watch})")

    try:
        latest_commit = get_latest_commit(repo_to_watch, branch=branch_to_watch, timeout=global_timeout)
    except GitError as e:
        print(f"[ERROR] {e}")
        return

    if not latest_commit:
        print("No commits found on remote (empty repo?). Skipping.")
        return

    state_key = f"{repo_to_watch}#{branch_to_watch}" if branch_to_watch else repo_to_watch
    repo_state = state.get(state_key, {})
    last_seen = repo_state.get("last_commit", None)

    print(f"  Last seen: {last_seen}")
    print(f"  Latest   : {latest_commit}")

    if last_seen == latest_commit:
        print("  No new commits. Nothing to do.")
        return

    runs = repo_cfg.get("runs", [])
    if not isinstance(runs, list) or not runs:
        print("  No runs configured under repo['runs']. Skipping submission.")
        return

    print(f"  New commit detected. Submitting {len(runs)} run(s).")

    attempted_submissions = False
    for index, run_cfg in enumerate(runs, start=1):
        if not isinstance(run_cfg, dict):
            print(f"  Run {index}: invalid format (expected object), skipping.")
            continue

        missing = [field for field in ("repo_to_run", "machine_id") if field not in run_cfg]
        if missing:
            print(f"  Run {index}: missing required field(s): {', '.join(missing)}. Skipping.")
            continue

        payload = build_payload_for_run(name, run_cfg, latest_commit)
        attempted_submissions = True
        print(
            f"  Run {index}: submitting {payload['repo_url']} "
            f"({payload['branch']}, {payload['filename']})"
        )

        try:
            resp = client.submit_software(payload)
            if resp is None:
                print(f"  Run {index}: accepted (202), queued.")
            else:
                print(f"  Run {index}: unexpected response: {resp}")
        except APIEmptyResponse204:
            print(f"  Run {index}: API returned 204 No Content.")
        except APIError as e:
            print(f"  Run {index}: API error: {e}")
        except requests.RequestException as e:
            print(f"  Run {index}: HTTP error: {e}")

    if not attempted_submissions:
        print("  No valid runs to submit. State not updated.")
        return

    # Only update state after attempting valid submissions
    state[state_key] = {"last_commit": latest_commit}
    print(f"Updated state: last_commit = {latest_commit}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Monitor GitHub/GitLab repos and submit GMT jobs on new commits."
    )
    p.add_argument(
        "--config",
        default="config.json",
        help="Path to JSON config file (see script docstring for structure).",
    )
    p.add_argument(
        "--state",
        default="repo_state.json",
        help="Path to JSON state file (will be created/updated). Default: repo_state.json",
    )
    return p


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    # Load config
    config = load_json(args.config)
    if not config:
        print(f"Failed to read config file {args.config}", file=sys.stderr)
        sys.exit(1)

    api_cfg = config.get("api", {})
    api_url = api_cfg.get("api_url", "https://api.green-coding.io/").strip()
    token = api_cfg.get("token", "DEFAULT").strip()
    timeout = int(api_cfg.get("timeout", 30))

    repos = config.get("repos", [])
    if not repos:
        print("No repos configured under config['repos'].", file=sys.stderr)
        sys.exit(1)

    client = APIClient(api_url=api_url, token=token, timeout=timeout)

    state = load_json(args.state)

    for repo_cfg in repos:
        process_repo(client, repo_cfg, state, timeout)

    save_json(args.state, state)

if __name__ == "__main__":
    main()
