# PyPI Publishing Automation Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix automated PyPI publishing by adding manual trigger capability and recreating v0.2.1 release through the corrected automation pipeline.

**Architecture:** Add `workflow_dispatch` trigger to `publish.yml` workflow enabling manual runs with tag selection. Delete existing v0.2.1 GitHub release/tag to allow clean recreation. Commit a minor change to trigger `release.yml`, which will create new v0.2.1 release via semantic-release, which will then trigger `publish.yml` to build and publish to PyPI.

**Tech Stack:** GitHub Actions workflows, semantic-release, Git, PyPI trusted publishing

---

## Task 1: Add workflow_dispatch trigger to publish.yml

**Files:**
- Modify: `.github/workflows/publish.yml:1-5`

**Step 1: Understand workflow_dispatch requirements**

The `workflow_dispatch` trigger allows manual workflow execution from GitHub Actions UI. We need to:
- Add `workflow_dispatch:` trigger to the `on:` section
- Add `inputs:` section to accept tag parameter for flexibility

Reference: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch

**Step 2: Modify publish.yml to add workflow_dispatch trigger**

Edit `.github/workflows/publish.yml` lines 1-5:

**Current code:**
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]
```

**Replace with:**
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      tag:
        description: 'Git tag to build and publish (e.g., v0.2.1)'
        required: true
        type: string
        default: ''
```

**Step 3: Update checkout step to use workflow_dispatch input**

Modify `.github/workflows/publish.yml` line 18:

**Current code:**
```yaml
        with:
          ref: ${{ github.event.release.tag_name }}
```

**Replace with:**
```yaml
        with:
          ref: ${{ inputs.tag || github.event.release.tag_name }}
```

This allows:
- Manual runs: uses `inputs.tag` parameter from workflow_dispatch UI
- Automated runs: uses `github.event.release.tag_name` from release event

**Step 4: Run linting on workflow file**

GitHub Actions workflows use YAML. We don't have a YAML linter configured, but we can validate syntax:

Run: `cat .github/workflows/publish.yml | grep -E "^[^#]" | head -20`
Expected: Clean YAML output showing trigger structure

**Step 5: Commit workflow change**

```bash
git add .github/workflows/publish.yml
git commit -m "feat: add workflow_dispatch trigger to publish.yml

- Add manual workflow execution capability
- Accept tag parameter for flexible manual runs
- Maintain backward compatibility with automated release triggers
- Enables manual re-publishing of specific versions"
```

---

## Task 2: Delete v0.2.1 GitHub release and tag

**Files:**
- None (Git operations only)

**Step 1: Verify current v0.2.1 state**

Run: `gh release view v0.2.1 --json tagName,isDraft,isPrerelease,createdAt,publishedAt,author`
Expected: Shows release exists, created by github-actions[bot] on 2026-01-02T03:58:33Z

Run: `git tag -l v0.2.1`
Expected: Shows v0.2.1 tag exists locally

**Step 2: Fetch all tags to ensure we have remote tags**

Run: `git fetch --tags origin`
Expected: Updates local tag references

**Step 3: Delete v0.2.1 GitHub release**

Run: `gh release delete v0.2.1 --yes`
Expected: `✓ Deleted release v0.2.1`

**Step 4: Delete v0.2.1 local and remote tags**

Run: `git tag -d v0.2.1 && git push origin :refs/tags/v0.2.1`
Expected:
- `Deleted tag 'v0.2.1' (was a43c83160716994c37be7ba1d68a1bb1a2d8320f)`
- `To github.com:saadiqhorton/nexus-ai.git`
- ` - [deleted]         v0.2.1`

**Step 5: Verify deletion**

Run: `git tag -l v0.2.1`
Expected: No output (tag does not exist)

Run: `gh release list | grep v0.2.1`
Expected: No output (release does not exist)

**Step 6: No commit needed**

This step only deletes existing release/tag. No commit required.

---

## Task 3: Create commit to trigger release workflow

**Files:**
- Modify: `nexus/__init__.py:1` or any source file

**Step 1: Choose appropriate file to modify**

We need a meaningful change to trigger release.yml. Let's update a docstring or add a small enhancement. Check current version file:

Run: `cat nexus/__init__.py`
Expected: `__version__ = "0.2.1"`

**Step 2: Add helpful docstring comment**

We'll add a comment explaining the PyPI package name to help users:

Edit `nexus/__init__.py` line 1:

**Current code:**
```python
__version__ = "0.2.1"
```

**Replace with:**
```python
# Package published on PyPI as 'nexus-ai-cli'
__version__ = "0.2.1"
```

**Step 3: Verify syntax**

Run: `python -c "exec(open('nexus/__init__.py').read()); print(__version__)"`
Expected: `0.2.1`

**Step 4: Run tests to ensure no regression**

Run: `pytest -x -q`
Expected: All tests pass (403 passed, 11 skipped in ~70s)

**Step 5: Run linting**

Run: `ruff check . && ruff format .`
Expected: No errors, any formatting auto-applied

**Step 6: Commit the change**

```bash
git add nexus/__init__.py
git commit -m "docs: add PyPI package name comment to __init__.py

Clarifies that the package is published as 'nexus-ai-cli' on PyPI
to help users understand installation naming."
```

---

## Task 4: Push to master and monitor release workflow

**Files:**
- None (Git operations only)

**Step 1: Push commit to master**

Run: `git push origin master`
Expected: Pushes commit, triggers GitHub Actions `release.yml` workflow

**Step 2: Wait for release workflow to start**

Run: `sleep 10 && gh run list --workflow=release.yml --limit 1`
Expected: Shows workflow triggered, status "in_progress" or "queued"

**Step 3: Monitor release workflow**

Run: `gh run watch --exit-status --interval 30 $(gh run list --workflow=release.yml --limit 1 --json databaseId --jq '.[0].databaseId')`
Expected: Workflow completes successfully (may take 2-5 minutes)

**Step 4: Verify new v0.2.1 release created**

Run: `gh release list | grep v0.2.1`
Expected: Shows v0.2.1 release

Run: `git ls-remote --tags origin | grep v0.2.1`
Expected: Shows refs/tags/v0.2.1

**Step 5: Verify release details**

Run: `gh release view v0.2.1 --json tagName,isDraft,isPrerelease,createdAt,publishedAt,author`
Expected:
- tagName: "v0.2.1"
- isDraft: false
- isPrerelease: false
- author: github-actions[bot]
- publishedAt: within last 5 minutes

**Step 6: No commit needed**

This step is monitoring, no changes required.

---

## Task 5: Verify publish workflow triggers and succeeds

**Files:**
- None (Monitoring and verification only)

**Step 1: Wait for publish workflow to trigger**

Release creation should trigger `publish.yml`. Wait 30-60 seconds for trigger:

Run: `sleep 45 && gh run list --workflow=publish.yml --limit 3`
Expected: Shows new workflow run for v0.2.1

**Step 2: Monitor publish workflow**

Get workflow ID and watch:

Run: `PUBLISH_ID=$(gh run list --workflow=publish.yml --limit 1 --json databaseId --jq '.[0].databaseId') && gh run watch --exit-status --interval 30 $PUBLISH_ID`
Expected: Workflow completes successfully (may take 2-3 minutes)

**Step 3: Verify workflow succeeded**

Run: `gh run view $PUBLISH_ID --json conclusion,status,name --jq '{status, conclusion, name}'`
Expected:
- status: "completed"
- conclusion: "success"
- name: "v0.2.1"

**Step 4: Verify v0.2.1 on PyPI**

Run: `curl -s https://pypi.org/pypi/nexus-ai-cli/json | jq '.releases | keys' | grep 0.2.1`
Expected: Shows `"0.2.1"` in the list

Or visit: https://pypi.org/project/nexus-ai-cli/

Expected: Version 0.2.1 shows as latest version

**Step 5: Verify package metadata**

Run: `pip index versions nexus-ai-cli | grep 0.2.1`
Expected: Shows 0.2.1 in available versions

**Step 6: Verify installation works**

Run: `pipx run --spec https://files.pythonhosted.org/packages/py3/n/nexus_ai_cli/nexus_ai_cli-0.2.1-py3-none-any.whl nexus --help`
Expected: Shows nexus CLI help output

Or in clean environment:
```bash
pip install nexus-ai-cli==0.2.1
nexus --version
```
Expected: `nexus 0.2.1`

**Step 7: No commit needed**

This is verification only.

---

## Task 6: Test manual workflow_dispatch for future use

**Files:**
- None (Testing workflow_dispatch capability)

**Step 1: Verify workflow_dispatch available in UI**

Open: https://github.com/saadiqhorton/nexus-ai/actions/workflows/publish.yml

Expected: Blue "Run workflow" button visible on right side

**Step 2: Test manual workflow run**

Click "Run workflow" button
- Branch: `master`
- Tag: Enter `v0.2.1`
- Click "Run workflow" (green button)

Expected: Workflow starts immediately, shows in Actions tab

**Step 3: Monitor manual run**

Run: `gh run list --workflow=publish.yml --limit 1`
Expected: Shows new manual workflow run (event: workflow_dispatch)

**Step 4: Verify build uses correct tag**

In workflow run details, check "Checkout code" step logs.

Expected: Shows `Checking out refs/tags/v0.2.1`

**Step 5: Verify build artifact version**

In workflow "Build package" step logs, check version.

Expected: Shows `Successfully built nexus_ai_cli-0.2.1...`

**Step 6: Verify PyPI skip-existing works**

Since v0.2.1 is already on PyPI from previous step, this manual run should skip upload.

In "Publish to PyPI" step logs:

Expected: Shows something like `File already exists, skipping upload` or completes with warning but no error.

**Step 7: Document manual trigger usage**

Create or update documentation about manual workflow triggering. Since we don't have extensive docs, add comment to README or create simple notes file:

Create file: `docs/WORKFLOW_MANUAL_PUBLISH.md`

```markdown
# Manual PyPI Publishing

The `publish.yml` workflow supports both automated and manual triggering.

## Automated (Default)
Triggered automatically when a GitHub Release is published. Normal release flow:
1. Commit to master
2. `release.yml` runs → semantic-release creates GitHub Release
3. `publish.yml` triggers → builds and publishes to PyPI

## Manual
For re-publishing a specific version or testing:

1. Go to Actions → Publish to PyPI
2. Click "Run workflow" button
3. Select branch (usually `master`)
4. Enter tag name (e.g., `v0.2.1`)
5. Click green "Run workflow" button

The workflow will:
- Checkout the specified tag
- Build package artifacts
- Publish to PyPI

## Notes
- Use `skip-existing: true` to avoid errors if version already exists
- Manual runs are useful for:
  - Re-publishing after PyPI issues
  - Testing new workflow changes
  - Publishing from a specific tag without creating new release
```

**Step 8: Commit documentation**

```bash
git add docs/WORKFLOW_MANUAL_PUBLISH.md
git commit -m "docs: add manual workflow publishing guide

Documents workflow_dispatch trigger usage for manual PyPI publishing
and explains automated vs manual publishing workflows."
```

---

## Task 7: Final verification and cleanup

**Files:**
- None (Verification only)

**Step 1: Verify all workflow files are correct**

Run: `cat .github/workflows/publish.yml | grep -E "(workflow_dispatch|inputs|tag)" -A 3`
Expected: Shows workflow_dispatch trigger with tag input

Run: `cat .github/workflows/release.yml | grep -E "(on:|branches:)" -A 3`
Expected: Shows push to master triggers release workflow

**Step 2: Verify local and remote state**

Run: `git status`
Expected: Clean working tree, all changes committed

Run: `git log --oneline -5`
Expected: Shows commits from this plan:
- docs: add manual workflow publishing guide
- docs: add PyPI package name comment to __init__.py
- feat: add workflow_dispatch trigger to publish.yml

**Step 3: Verify PyPI package**

Run: `curl -s https://pypi.org/pypi/nexus-ai-cli/json | jq '{name, version, releases: (.releases | keys | length)}'`
Expected:
```json
{
  "name": "nexus-ai-cli",
  "version": "0.2.1",
  "releases": 2  (or more - versions available)
}
```

**Step 4: Test package installation in clean environment**

If possible, test fresh install:

```bash
# Create test venv
python -m venv /tmp/test-nexus-install
source /tmp/test-nexus-install/bin/activate

# Install from PyPI
pip install nexus-ai-cli

# Verify
nexus --version

# Cleanup
deactivate
rm -rf /tmp/test-nexus-install
```

Expected:
- Installation succeeds
- `nexus 0.2.1` or similar version output

**Step 5: No commit needed**

All verification complete.

---

## Success Criteria

After completing all tasks:

✅ `publish.yml` has `workflow_dispatch` trigger with tag input
✅ v0.2.1 GitHub release exists (newly created)
✅ v0.2.1 is published on PyPI
✅ Package installs correctly via `pip install nexus-ai-cli`
✅ Manual workflow trigger works from GitHub Actions UI
✅ Documentation exists for manual publishing usage
✅ All commits pushed to master
✅ Working tree clean
✅ All tests pass

---

## Rollback Plan

If anything goes wrong:

### If release workflow fails
- Check `release.yml` logs in GitHub Actions
- Verify semantic-release configuration in `pyproject.toml`
- Manually create release: `gh release create v0.2.1 --notes "Release notes"`

### If publish workflow fails
- Check `publish.yml` logs in GitHub Actions
- Verify trusted publishing setup in PyPI
- Manually publish: `python -m build && twine upload dist/*`

### If PyPI upload fails
- Check PyPI account and trusted publishing configuration
- Verify PyPI API token (if using manual upload)
- Check for PyPI outages: https://status.python.org/

### If wrong version published
- Delete release/tag: `gh release delete vX.Y.Z --yes && git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z`
- Fix version in files: `pyproject.toml`, `nexus/__init__.py`
- Re-run this plan from Task 2

---

## Notes

- **DRY**: Manual trigger capability added once, reused for all future versions
- **YAGNI**: Only essential changes to workflow files, no over-engineering
- **TDD**: Workflow changes verified by actual execution in GitHub Actions
- **Frequent commits**: Each logical task committed independently
- **Verification**: Every step has verification command with expected output
