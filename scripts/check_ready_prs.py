#!/usr/bin/env python3
"""
Check all open PRs by a user against the PR readiness checklist.

Usage:
    python check_ready_prs.py --user neubig
    python check_ready_prs.py --user neubig --ready-only
    python check_ready_prs.py --user neubig --draft-only
"""

import argparse
import json
import subprocess
import sys
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PRCheckResult:
    repo: str
    number: int
    title: str
    is_draft: bool
    
    # Structure checks
    has_summary: bool = False
    has_details: bool = False
    has_testing: bool = False
    has_evidence: bool = False
    has_checklist: bool = False
    sections_in_order: bool = False
    
    # Evidence checks
    has_conversation_link: bool = False
    evidence_has_command_output: bool = False
    evidence_mentions_tests: bool = False  # Should be False for good PRs
    
    # PR state checks
    unresolved_reviews: int = 0
    ci_failures: int = 0
    ci_pending: int = 0
    mergeable: Optional[bool] = None
    
    def passes_checklist(self) -> bool:
        """Check if PR passes all readiness requirements."""
        return (
            self.has_summary and
            self.has_testing and
            self.has_evidence and
            self.has_checklist and
            self.sections_in_order and
            (self.has_conversation_link or self.is_content_only()) and
            self.evidence_has_command_output and
            not self.evidence_mentions_tests and
            self.unresolved_reviews == 0 and
            self.ci_failures == 0 and
            self.mergeable in (True, None)  # None means not yet computed
        )
    
    def is_content_only(self) -> bool:
        """Check if this appears to be a content-only PR (docs, README, etc.)."""
        content_keywords = ['readme', 'documentation', 'docs', 'agents.md', 'changelog']
        return any(kw in self.title.lower() for kw in content_keywords)
    
    def get_issues(self) -> list[str]:
        """Get list of issues preventing readiness."""
        issues = []
        
        # Structure issues
        if not self.has_summary:
            issues.append("Missing ## Summary section")
        if not self.has_testing:
            issues.append("Missing ## Testing section")
        if not self.has_evidence:
            issues.append("Missing ## Evidence section")
        if not self.has_checklist:
            issues.append("Missing ## Checklist section")
        if not self.sections_in_order:
            issues.append("Sections not in correct order (Summary → Details → Testing → Evidence → Checklist)")
        
        # Evidence issues
        if not self.has_conversation_link and not self.is_content_only():
            issues.append("Missing conversation verification link in Evidence")
        if not self.evidence_has_command_output and not self.is_content_only():
            issues.append("Evidence lacks command output/screenshots")
        if self.evidence_mentions_tests:
            issues.append("Evidence section mentions tests (should be in Testing)")
        
        # State issues
        if self.unresolved_reviews > 0:
            issues.append(f"{self.unresolved_reviews} unresolved review comments")
        if self.ci_failures > 0:
            issues.append(f"{self.ci_failures} CI failures")
        if self.ci_pending > 0:
            issues.append(f"{self.ci_pending} CI checks pending")
        if self.mergeable == False:
            issues.append("Has merge conflicts")
        
        return issues


def run_gh_command(args: list[str]) -> str:
    """Run a gh CLI command and return output."""
    result = subprocess.run(['gh'] + args, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_all_prs(user: str) -> list[dict]:
    """Get all open PRs for a user with pagination."""
    prs = []
    page = 1
    per_page = 100
    
    while True:
        output = run_gh_command([
            'api', '-X', 'GET', '/search/issues',
            '-f', f'q=is:pr is:open author:{user}',
            '-f', f'per_page={per_page}',
            '-f', f'page={page}'
        ])
        
        if not output:
            break
            
        data = json.loads(output)
        items = data.get('items', [])
        
        if not items:
            break
            
        for item in items:
            repo_url = item['repository_url']
            repo_parts = repo_url.split('/')
            repo = f"{repo_parts[-2]}/{repo_parts[-1]}"
            
            prs.append({
                'repo': repo,
                'number': item['number'],
                'title': item['title'],
                'is_draft': item.get('draft', False)
            })
        
        if len(items) < per_page:
            break
        page += 1
    
    return prs


def check_pr_structure(body: str) -> dict:
    """Check PR description structure."""
    sections = {
        'summary': r'^## Summary',
        'details': r'^## Details',
        'testing': r'^## Testing',
        'evidence': r'^## Evidence',
        'checklist': r'^## Checklist'
    }
    
    results = {}
    positions = {}
    
    for name, pattern in sections.items():
        match = re.search(pattern, body, re.MULTILINE)
        results[f'has_{name}'] = match is not None
        positions[name] = match.start() if match else -1
    
    # Check order (Summary before Details before Testing before Evidence before Checklist)
    # Details is optional
    required_order = ['summary', 'testing', 'evidence', 'checklist']
    in_order = True
    last_pos = -1
    for section in required_order:
        pos = positions.get(section, -1)
        if pos != -1:
            if pos < last_pos:
                in_order = False
                break
            last_pos = pos
    
    results['sections_in_order'] = in_order
    return results


def check_evidence_section(body: str) -> dict:
    """Check Evidence section content."""
    results = {
        'has_conversation_link': False,
        'evidence_has_command_output': False,
        'evidence_mentions_tests': False
    }
    
    # Extract evidence section
    evidence_match = re.search(r'^## Evidence\s*\n(.*?)(?=^## |\Z)', body, re.MULTILINE | re.DOTALL)
    if not evidence_match:
        return results
    
    evidence = evidence_match.group(1)
    
    # Check for conversation link
    results['has_conversation_link'] = 'app.all-hands.dev/conversations/' in evidence
    
    # Check for command output (look for $ prompts, ``` code blocks with output)
    has_prompt = bool(re.search(r'^\s*\$\s+\w', evidence, re.MULTILINE))
    has_code_block = '```' in evidence
    has_output_indicators = any(x in evidence.lower() for x in ['output:', 'result:', '✓', '✅', 'passed', 'success'])
    results['evidence_has_command_output'] = has_prompt or (has_code_block and has_output_indicators)
    
    # Check if evidence mentions tests (bad - should be in Testing section)
    test_patterns = [
        r'\d+\s*(tests?\s+)?pass(ed|ing)?',
        r'all\s+\d+\s+tests',
        r'test.*pass',
        r'\d+/\d+\s+pass'
    ]
    for pattern in test_patterns:
        if re.search(pattern, evidence, re.IGNORECASE):
            results['evidence_mentions_tests'] = True
            break
    
    return results


def check_pr_state(repo: str, number: int) -> dict:
    """Check PR state (reviews, CI, conflicts)."""
    results = {
        'unresolved_reviews': 0,
        'ci_failures': 0,
        'ci_pending': 0,
        'mergeable': None
    }
    
    owner, repo_name = repo.split('/')
    
    # Check unresolved reviews
    query = f'''{{
        repository(owner: "{owner}", name: "{repo_name}") {{
            pullRequest(number: {number}) {{
                reviewThreads(first: 100) {{
                    nodes {{ isResolved }}
                }}
            }}
        }}
    }}'''
    
    output = run_gh_command(['api', 'graphql', '-f', f'query={query}'])
    if output:
        try:
            data = json.loads(output)
            threads = data.get('data', {}).get('repository', {}).get('pullRequest', {}).get('reviewThreads', {}).get('nodes', [])
            results['unresolved_reviews'] = sum(1 for t in threads if not t.get('isResolved', True))
        except:
            pass
    
    # Check CI status
    ci_output = run_gh_command(['pr', 'checks', str(number), '--repo', repo])
    if ci_output:
        for line in ci_output.split('\n'):
            if 'fail' in line.lower() or 'error' in line.lower():
                results['ci_failures'] += 1
            elif 'pending' in line.lower() or 'queued' in line.lower():
                results['ci_pending'] += 1
    
    # Check mergeable status
    pr_output = run_gh_command(['api', f'repos/{repo}/pulls/{number}', '--jq', '.mergeable'])
    if pr_output:
        if pr_output == 'true':
            results['mergeable'] = True
        elif pr_output == 'false':
            results['mergeable'] = False
    
    return results


def check_pr(repo: str, number: int, title: str, is_draft: bool) -> PRCheckResult:
    """Run all checks on a PR."""
    result = PRCheckResult(
        repo=repo,
        number=number,
        title=title,
        is_draft=is_draft
    )
    
    # Get PR body
    body = run_gh_command(['pr', 'view', str(number), '--repo', repo, '--json', 'body', '-q', '.body'])
    
    # Check structure
    structure = check_pr_structure(body)
    result.has_summary = structure['has_summary']
    result.has_details = structure['has_details']
    result.has_testing = structure['has_testing']
    result.has_evidence = structure['has_evidence']
    result.has_checklist = structure['has_checklist']
    result.sections_in_order = structure['sections_in_order']
    
    # Check evidence
    evidence = check_evidence_section(body)
    result.has_conversation_link = evidence['has_conversation_link']
    result.evidence_has_command_output = evidence['evidence_has_command_output']
    result.evidence_mentions_tests = evidence['evidence_mentions_tests']
    
    # Check state
    state = check_pr_state(repo, number)
    result.unresolved_reviews = state['unresolved_reviews']
    result.ci_failures = state['ci_failures']
    result.ci_pending = state['ci_pending']
    result.mergeable = state['mergeable']
    
    return result


def print_result(result: PRCheckResult, verbose: bool = False):
    """Print check result for a PR."""
    status = "✅ PASS" if result.passes_checklist() else "❌ FAIL"
    draft_indicator = " [DRAFT]" if result.is_draft else ""
    
    print(f"\n{'='*60}")
    print(f"{result.repo}#{result.number}{draft_indicator}: {status}")
    print(f"Title: {result.title[:50]}...")
    
    if verbose or not result.passes_checklist():
        print("\nStructure:")
        print(f"  Summary: {'✓' if result.has_summary else '✗'}")
        print(f"  Details: {'✓' if result.has_details else '○'} (optional)")
        print(f"  Testing: {'✓' if result.has_testing else '✗'}")
        print(f"  Evidence: {'✓' if result.has_evidence else '✗'}")
        print(f"  Checklist: {'✓' if result.has_checklist else '✗'}")
        print(f"  Order: {'✓' if result.sections_in_order else '✗'}")
        
        print("\nEvidence Quality:")
        print(f"  Conversation link: {'✓' if result.has_conversation_link else '✗'}")
        print(f"  Command output: {'✓' if result.evidence_has_command_output else '✗'}")
        print(f"  No test mentions: {'✓' if not result.evidence_mentions_tests else '✗'}")
        
        print("\nPR State:")
        print(f"  Unresolved reviews: {result.unresolved_reviews}")
        print(f"  CI failures: {result.ci_failures}")
        print(f"  CI pending: {result.ci_pending}")
        print(f"  Mergeable: {result.mergeable}")
    
    issues = result.get_issues()
    if issues:
        print("\nIssues:")
        for issue in issues:
            print(f"  - {issue}")


def main():
    parser = argparse.ArgumentParser(description='Check PRs against readiness checklist')
    parser.add_argument('--user', required=True, help='GitHub username')
    parser.add_argument('--ready-only', action='store_true', help='Only check ready PRs')
    parser.add_argument('--draft-only', action='store_true', help='Only check draft PRs')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show all details')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    args = parser.parse_args()
    
    print(f"Fetching PRs for {args.user}...")
    prs = get_all_prs(args.user)
    print(f"Found {len(prs)} open PRs")
    
    # Filter if needed
    if args.ready_only:
        prs = [p for p in prs if not p['is_draft']]
        print(f"Filtered to {len(prs)} ready PRs")
    elif args.draft_only:
        prs = [p for p in prs if p['is_draft']]
        print(f"Filtered to {len(prs)} draft PRs")
    
    results = []
    for pr in prs:
        print(f"Checking {pr['repo']}#{pr['number']}...", end=' ', flush=True)
        result = check_pr(pr['repo'], pr['number'], pr['title'], pr['is_draft'])
        results.append(result)
        print("done")
    
    # Print results
    if not args.summary:
        for result in results:
            print_result(result, args.verbose)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passing = [r for r in results if r.passes_checklist()]
    failing = [r for r in results if not r.passes_checklist()]
    
    print(f"\n✅ PASSING ({len(passing)}):")
    for r in passing:
        print(f"  - {r.repo}#{r.number}: {r.title[:40]}...")
    
    print(f"\n❌ FAILING ({len(failing)}):")
    for r in failing:
        issues = r.get_issues()
        print(f"  - {r.repo}#{r.number}: {issues[0] if issues else 'Unknown'}")
    
    # Return exit code
    sys.exit(0 if len(failing) == 0 else 1)


if __name__ == '__main__':
    main()
