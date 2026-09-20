# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

release_audit = importlib.import_module("scripts.audit_release")
fixture_generator = importlib.import_module("scripts.generate_synthetic_sample")


PROHIBITED_WORD = "".join(
    chr(code) for code in (99, 101, 108, 101, 98, 114, 105, 116, 105, 101, 115)
)
SOURCE_LINK = "".join(
    chr(code)
    for code in (
        104,
        116,
        116,
        112,
        115,
        58,
        47,
        47,
        115,
        111,
        117,
        114,
        99,
        101,
        46,
        101,
        120,
        97,
        109,
        112,
        108,
        101,
        46,
        99,
        111,
        109,
        47,
        105,
        116,
        101,
        109,
    )
)
ASSIGNED_CREDENTIAL = "".join(
    chr(code)
    for code in (
        97,
        112,
        105,
        95,
        107,
        101,
        121,
        61,
        39,
        48,
        49,
        50,
        51,
        52,
        53,
        54,
        55,
        56,
        57,
        97,
        98,
        99,
        100,
        101,
        102,
        39,
    )
)


def git(repository: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def write_file(repository: Path, relative: str, content: str) -> Path:
    path = repository.joinpath(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def stage_file(repository: Path, relative: str, content: str) -> Path:
    path = write_file(repository, relative, content)
    git(repository, "add", "--force", "--", relative)
    return path


def inspect_candidate() -> tuple[release_audit.Audit, release_audit.CandidateSurface]:
    audit = release_audit.Audit()
    surface = release_audit.scan_repository([], audit)
    return audit, surface


def assert_error(audit: release_audit.Audit, expected_fragment: str) -> None:
    assert any(expected_fragment in error for error in audit.errors), audit.errors


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    git(tmp_path, "init", "--quiet")
    monkeypatch.setattr(release_audit, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        release_audit,
        "FIXTURE_ROOT",
        tmp_path / "examples" / "synthetic_examples",
    )
    return tmp_path


def test_clean_repository_passes(repository: Path) -> None:
    stage_file(repository, "safe.txt", "fictional interview fixture\n")

    audit, surface = inspect_candidate()

    assert audit.errors == []
    assert surface.files == {"safe.txt": b"fictional interview fixture\n"}


def test_prohibited_terminology_is_rejected(repository: Path) -> None:
    stage_file(repository, "notes.txt", PROHIBITED_WORD)

    audit, _ = inspect_candidate()

    assert_error(audit, "prohibited public terminology")


def test_nonignored_untracked_file_is_scanned(repository: Path) -> None:
    write_file(repository, "untracked.txt", PROHIBITED_WORD)

    audit, surface = inspect_candidate()

    assert "untracked.txt" in surface.files
    assert_error(audit, "prohibited public terminology")


def test_local_git_exclude_cannot_hide_untracked_file(
    repository: Path,
) -> None:
    write_file(repository, ".git/info/exclude", "hidden.txt\n")
    write_file(repository, "hidden.txt", PROHIBITED_WORD)

    audit, surface = inspect_candidate()

    assert "hidden.txt" in surface.files
    assert_error(audit, "prohibited public terminology")


def test_nested_ignore_file_is_rejected(repository: Path) -> None:
    write_file(repository, "notes/.gitignore", "*\n")
    write_file(repository, "notes/hidden.txt", PROHIBITED_WORD)

    audit, _ = inspect_candidate()

    assert_error(audit, "nested ignore files")


@pytest.mark.parametrize(
    "relative",
    (
        "build/poison.txt",
        "dist/poison.txt",
        "cache/poison.txt",
        "package.egg-info/poison.txt",
    ),
)
def test_force_staged_ignored_file_is_scanned(repository: Path, relative: str) -> None:
    stage_file(
        repository,
        ".gitignore",
        "build/\ndist/\ncache/\n*.egg-info/\n",
    )
    write_file(repository, relative, PROHIBITED_WORD)
    git(repository, "add", "--force", "--", relative)

    audit, surface = inspect_candidate()

    assert relative in surface.files
    assert_error(audit, "prohibited public terminology")


def test_staged_then_reverted_content_is_rejected(repository: Path) -> None:
    path = stage_file(repository, "notes.txt", "safe\n")
    path.write_text(PROHIBITED_WORD, encoding="utf-8")
    git(repository, "add", "--", "notes.txt")
    path.write_text("safe\n", encoding="utf-8")

    audit, _ = inspect_candidate()

    assert_error(audit, "prohibited public terminology")
    assert_error(audit, "worktree content differs from index")


def test_symbolic_link_is_rejected(repository: Path) -> None:
    stage_file(repository, "target.txt", "safe\n")
    link = repository / "shortcut"
    os.symlink("target.txt", link)
    git(repository, "add", "--", "shortcut")

    audit, _ = inspect_candidate()

    assert_error(audit, "symbolic links are not allowed")


@pytest.mark.parametrize(
    ("content", "expected"),
    (
        (SOURCE_LINK, "unapproved link"),
        (ASSIGNED_CREDENTIAL, "assigned secret"),
        ("owner" + "@" + "example" + "." + "com", "email address"),
        ("/" + "Users/research/private.txt", "internal path"),
    ),
    ids=("source-link", "assigned-secret", "email", "internal-path"),
)
def test_sensitive_content_is_rejected(repository: Path, content: str, expected: str) -> None:
    stage_file(repository, "details.txt", content)

    audit, _ = inspect_candidate()

    assert_error(audit, expected)


def test_contributing_urls_are_allowed_only_in_contributing_file() -> None:
    url = "https:" + "//" + "cla." + "salesforce." + "com/sign-cla"
    approved = release_audit.Audit()
    rejected = release_audit.Audit()

    release_audit.scan_candidate("CONTRIBUTING.md", url.encode(), [], approved, "CONTRIBUTING.md")
    release_audit.scan_candidate("notes.txt", url.encode(), [], rejected, "notes.txt")

    assert approved.errors == []
    assert_error(rejected, "unapproved link")


def test_reviewed_binary_image_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    relative = "assets/reviewed.png"
    data = release_audit.PNG_SIGNATURE + b"reviewed image bytes"
    monkeypatch.setattr(
        release_audit,
        "ALLOWED_BINARY_DIGESTS",
        {relative: hashlib.sha256(data).hexdigest()},
    )
    audit = release_audit.Audit()

    release_audit.scan_candidate(relative, data, [], audit, relative)

    assert audit.errors == []


def test_modified_binary_image_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    relative = "assets/reviewed.png"
    data = release_audit.PNG_SIGNATURE + b"reviewed image bytes"
    monkeypatch.setattr(
        release_audit,
        "ALLOWED_BINARY_DIGESTS",
        {relative: hashlib.sha256(data).hexdigest()},
    )
    audit = release_audit.Audit()

    release_audit.scan_candidate(relative, data + b"changed", [], audit, relative)

    assert_error(audit, "differs from its reviewed content")


def test_reviewed_governance_template_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    relative = "SECURITY.md"
    data = ("Report to security" + "@" + "example" + "." + "invalid\n").encode()
    monkeypatch.setattr(
        release_audit,
        "APPROVED_TEMPLATE_DIGESTS",
        {relative: hashlib.sha256(data).hexdigest()},
    )
    audit = release_audit.Audit()

    release_audit.scan_candidate(relative, data, [], audit, relative)

    assert audit.errors == []


def test_modified_governance_template_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    relative = "SECURITY.md"
    data = b"reviewed security policy\n"
    monkeypatch.setattr(
        release_audit,
        "APPROVED_TEMPLATE_DIGESTS",
        {relative: hashlib.sha256(data).hexdigest()},
    )
    audit = release_audit.Audit()

    release_audit.scan_candidate(relative, data + b"changed\n", [], audit, relative)

    assert_error(audit, "governance template differs from reviewed content")


def test_unexpected_binary_file_is_rejected() -> None:
    audit = release_audit.Audit()

    release_audit.scan_candidate("artifact.bin", b"opaque\0content", [], audit, "artifact.bin")

    assert_error(audit, "unexpected binary file")


def test_required_governance_files_are_enforced() -> None:
    surface = release_audit.CandidateSurface(
        files={relative: b"reviewed\n" for relative in release_audit.REQUIRED_RELEASE_FILES}
    )
    audit = release_audit.Audit()

    release_audit.validate_release_files(audit, surface)

    assert audit.errors == []


def test_template_instruction_file_is_rejected() -> None:
    files = {relative: b"reviewed\n" for relative in release_audit.REQUIRED_RELEASE_FILES}
    files["how_to_license.md"] = b"template instructions\n"
    audit = release_audit.Audit()

    release_audit.validate_release_files(
        audit,
        release_audit.CandidateSurface(files=files),
    )

    assert_error(audit, "template instruction file")


def test_fixture_loader_uses_candidate_blob(repository: Path) -> None:
    path = write_file(
        repository,
        "examples/synthetic_examples/manifest.json",
        '{"value": "worktree"}',
    )
    relative = "examples/synthetic_examples/manifest.json"
    surface = release_audit.CandidateSurface(
        files={relative: b'{"value": "candidate"}'},
        scanned_files=1,
    )
    audit = release_audit.Audit()

    document = release_audit.load_json(path, audit, surface)

    assert audit.errors == []
    assert document == {"value": "candidate"}


def test_fixture_text_rejects_proper_noun_like_word() -> None:
    audit = release_audit.Audit()

    release_audit.validate_fixture_text(
        {"question": "What did Properword change?"},
        "fixture.json",
        audit,
    )

    assert_error(audit, "proper-noun-like named entity")


def test_fixture_text_rejects_structural_id() -> None:
    audit = release_audit.Audit()

    release_audit.validate_fixture_text(
        {"response": "I copied PERSONALITY_001 into the answer."},
        "fixture.json",
        audit,
    )

    assert_error(audit, "structural identifier appears in free text")


def test_runtime_private_denylist_is_scanned(repository: Path) -> None:
    stage_file(repository, "notes.txt", "fictional identity marker")
    audit = release_audit.Audit()

    release_audit.scan_repository(["identity marker"], audit)

    assert_error(audit, "runtime private-denylist entry")


def test_fixture_must_match_generator_exactly(
    repository: Path,
) -> None:
    prefix = "examples/synthetic_examples/"
    documents = fixture_generator.build_fixture_documents()
    files = {
        prefix + relative: fixture_generator.serialize(document).encode()
        for relative, document in documents.items()
    }
    altered_manifest = dict(documents["manifest.json"])
    altered_manifest["generation_seed"] = 1
    files[prefix + "manifest.json"] = fixture_generator.serialize(altered_manifest).encode()
    surface = release_audit.CandidateSurface(files=files)
    audit = release_audit.Audit()

    release_audit.validate_fixture(audit, surface)

    assert_error(audit, "differs from deterministic generator output")


def test_private_denylist_must_be_outside_repository(
    repository: Path,
) -> None:
    path = write_file(repository, "denylist.json", json.dumps(["marker"]))
    audit = release_audit.Audit()

    entries = release_audit.load_private_denylist(path, audit)

    assert entries == []
    assert_error(audit, "must remain outside")
