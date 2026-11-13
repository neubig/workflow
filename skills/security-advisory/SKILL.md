---
name: security-advisory
description: This skill should be used when the user asks to "handle a security report", "prepare a security advisory", "request a CVE", "publish an advisory", or "check whether a security fix has shipped". Guides coordinated vulnerability disclosure through private triage, patch review, release and downstream adoption verification, advisory metadata, CVE coordination, publication, and notification.
---

# Security advisory workflow

Handle vulnerabilities in a project's own code from report to verified public disclosure. Distinguish this process from upgrading a dependency to resolve an existing upstream CVE.

Treat **patch merged**, **component released**, **downstream product released**, **CVE requested**, **CVE assigned**, and **advisory published** as separate states. Never infer one from another.

## Guardrails

- Read the project's public security policy and agree on the disclosure owner, remediation owner, reviewer, release owner, affected products, and intended disclosure timing.
- Keep unpublished reports, reproductions, private advisory identifiers, correspondence, and evidence in authorized private systems. Never copy them into public issues, skills, logs, PR descriptions, or examples. Use synthetic placeholders in reusable documentation.
- Ask for the authorized coordination destination and original thread; never assume a channel name or audience. Confirm access without broadening membership or changing permissions.
- Separate investigation from mutation. Obtain explicit approval before contacting reporters, changing advisory metadata, opening or pushing patches, merging, releasing, requesting CVEs, publishing, or posting announcements. Approval for one action does not authorize the others.
- Prefer authenticated service APIs and MCP tools. Treat missing permissions as unknown status, not proof that an advisory does not exist or is already public. Request the specific access needed or hand the operation to an authorized maintainer.
- Include a brief AI-on-behalf-of disclosure in human-facing content posted by the agent. Do not include private evidence in that attribution.

## 1. Establish the report and scope

1. Resolve the exact repository and advisory from authorized evidence. Match identifiers, affected component, and behavior; do not substitute a similar vulnerability found in another discussion.
2. Acknowledge receipt according to the project's policy once authorized. Preserve reporter credit and agree on communication and disclosure expectations.
3. Reproduce only in an authorized isolated environment using synthetic data and harmless actions. Record the exact version, configuration, prerequisites, expected behavior, observed behavior, and test limitations.
4. Check current supported releases as well as the reported version. Distinguish default behavior from an explicitly configured deployment. Do not extrapolate an affected range from one tested version.
5. Identify the owning repository and related reports. Preserve original references and credit if moving ownership or proposing duplicate closure. Require a separate regression for each distinct affected path, even when one patch fixes several reports.
6. Record confirmed facts separately from hypotheses, untested configurations, and follow-up findings.

## 2. Develop and review the private patch

Use a draft repository advisory and its temporary private fork when appropriate. Add only authorized collaborators. Keep unpublished reproductions and patch discussion out of public tickets.

- Add a regression that fails before the fix and passes afterward. Exercise the real affected boundary, including creation, resume/cold-load, alternate transports, and configured authentication where relevant.
- Test the smallest fix against normal behavior and the vulnerable configuration. Record commands, results, and residual risks in the authorized review context.
- Check whether private-fork CI is supported before relying on it. Never trigger public automation or upload artifacts that disclose the report. If CI cannot run, provide local test evidence and obtain a maintainer's explicit decision on remaining validation gaps; do not mark missing checks as passed.
- Review the fix independently. Split newly discovered issues from the current patch unless they are required to close the original vulnerability.

Merge temporary-fork PRs through the advisory's **Collaborate on a patch → Merge pull request(s)** control rather than assuming an ordinary PR merge is equivalent. Follow the current [GitHub private-fork guidance](https://docs.github.com/en/code-security/tutorials/fix-reported-vulnerabilities/collaborate-in-a-fork).

If branch protections block the advisory merge, report the blocker and ask an authorized administrator for a narrow, approved resolution. Do not silently bypass reviews, disable protections, or assume a rebase fixes it. Restore any approved temporary protection changes afterward. Record the resulting upstream fix commit.

## 3. Prove the fix shipped

Build an evidence chain before recommending disclosure:

| Gate | Required evidence |
| --- | --- |
| Upstream merge | Fix commit exists on the intended upstream branch |
| Component release | Published release tag contains the fix; intended packages/images are available |
| Downstream adoption | Relevant released product pins or resolves the fixed component |
| Artifact validation | Relevant built artifact uses the expected dependency and passes targeted verification |

Identify the **first fixed release**, not merely the latest release. Check supported release lines and any required backports independently. Inspect a release tag's dependency manifest, lockfile, build configuration, image provenance, or installed package metadata rather than relying only on version-number ordering or release prose.

For Git ancestry, use read-only checks such as:

```bash
git merge-base --is-ancestor FIX_COMMIT RELEASE_TAG
# Or inspect status/ahead_by/behind_by in:
gh api repos/OWNER/REPO/compare/FIX_COMMIT...RELEASE_TAG
```

Resolve placeholders before execution. An ancestor result proves source inclusion, not successful artifact publication or deployment. A downstream branch's updated pin does not prove a released product includes it. A released product does not prove existing installations have upgraded.

Agree which downstream releases or deployments must be ready before publication. If a fix is unavailable or disclosure is urgent, escalate the disclosure timing and mitigation decision to the owner instead of inventing an unconditional release rule.

## 4. Prepare advisory metadata and CVE coordination

Review the current draft with the remediation reviewer:

- Correct package ecosystem and package name for each affected component.
- Evidence-based affected ranges and first patched versions for each supported line.
- Severity and CVSS vector reflecting actual privileges, exposure, user interaction, and impact; appropriate CWE.
- Clear impact, prerequisites, affected configurations, fix, upgrade instructions, and workarounds. Avoid overstating sandbox-local behavior as host compromise without evidence.
- Fix commit and release links, related advisories, and accurate reporter, remediation-developer, and remediation-reviewer credits. Confirm credit acceptance where applicable.
- Public-safe wording and a final review of the full description and linked material that will become visible.

Check whether a CVE is already assigned or requested. With explicit approval, request one through the exact advisory's **Request CVE** control when needed. Do not request duplicates. Record whether the request is pending or an identifier has been assigned.

Follow the current [GitHub publication and CVE instructions](https://docs.github.com/en/code-security/security-advisories/working-with-repository-security-advisories/publishing-a-repository-security-advisory). CVE requests are optional in that guidance; do not invent a universal requirement to wait for assignment. Check the current UI/API constraints and the project's agreed policy, and surface any pending-request blocker before proceeding.

## 5. Obtain the publication decision

Present a concise readiness report with links to authorized evidence:

- Exact advisory or coordinated advisory set.
- Fix commit, first fixed component release, and downstream release/artifact evidence.
- Regression results and any unverified deployment or supported release line.
- Metadata/credits review status and CVE request or assignment status.
- Remaining blockers and the precise action requested from the owner.

Request explicit approval to publish the reviewed advisory content. Coordinate related advisories for the same disclosure window when appropriate; do not assume every report sharing a patch should share a CVE.

## 6. Publish, verify, and communicate

1. Re-fetch advisory and release state immediately before the approved operation. Stop if the content, scope, or readiness changed materially.
2. Ensure required patch work has been merged and retained upstream before publication: GitHub deletes the advisory's temporary private fork when publishing.
3. Publish only the approved advisories using an available authorized API or maintainer UI handoff. If the operation is unavailable, provide exact links and instructions; do not claim completion.
4. Verify each advisory's published state, public URL, version ranges, credits, and CVE status afterward. If a user reports publishing but independent verification is unavailable, label the status as user-confirmed rather than independently verified.
5. With approval, reply in the original coordination thread and post a concise update to the agreed broader audience. Include public advisory links, first patched versions, downstream upgrade guidance, accurate CVE status, and appropriate credit. Exclude unpublished follow-ups and private discussion.
6. Update the authorized tracker with publication and release links. Keep any unfinished follow-up investigations open. Report partial publication or notification failures explicitly.

## Completion summary

Return the verified public advisory links, first fixed versions, relevant downstream release links, CVE status, and notification links. State any blocked actions or remaining checks. Never equate sending an announcement with successful advisory publication.
