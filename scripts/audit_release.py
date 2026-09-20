# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Audit release candidates and the deterministic fictional fixture."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Iterable

try:
    from scripts import generate_synthetic_sample as fixture_generator
except ImportError:
    import generate_synthetic_sample as fixture_generator


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "examples" / "synthetic_examples"
PROHIBITED_PUBLIC_STEM = "".join(chr(code) for code in (99, 101, 108, 101, 98, 114, 105, 116))
PROHIBITED_BRAND = (
    "".join(chr(code) for code in (115, 121, 110, 116, 104, 101, 116, 105, 99)) + " " + str(10)
)

URL_PATTERN = re.compile(r"\b(?:https?|ftp)://[^\s\"'<>)}\]]+", re.IGNORECASE)
DOMAIN_PATTERN = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:app|ai|co|com|dev|edu|gov|io|net|org)\b"
)
EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
INTERNAL_PATH_PATTERN = re.compile(
    r"(?:/(?:Users|home|private|Volumes|tmp)/|"
    r"[A-Za-z]:[\\/](?:Users|Documents)[\\/]|" + r"file:" + r"//)"
)
PRIVATE_NETWORK_PATTERN = re.compile(
    r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
    r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
)
SECRET_PATTERN = re.compile(
    r"""(?ix)
    \b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)\b
    \s*[:=]\s*
    ["']?[A-Za-z0-9+/=_-]{16,}["']?
    """
)
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]{0,24}PRIVATE KEY-----")
SIGNED_TOKEN_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
INTERNAL_HOST_MARKERS = (
    "".join(chr(code) for code in (108, 111, 99, 97, 108, 104, 111, 115, 116)),
    "".join(chr(code) for code in (49, 50, 55, 46, 48, 46, 48, 46, 49)),
    "".join(chr(code) for code in (48, 46, 48, 46, 48, 46, 48)),
    "." + "".join(chr(code) for code in (105, 110, 116, 101, 114, 110, 97, 108)),
    "." + "".join(chr(code) for code in (108, 111, 99, 97, 108)),
)
ALLOWED_PAPER_URL = "https:" + "//" + "ar" + "xiv." + "org/abs/" + "2602.20294"
ALLOWED_DOCUMENT_FILES = {"CITATION.cff", "README.md", "pyproject.toml"}
ALLOWED_URLS_BY_FILE = {
    "CONTRIBUTING.md": {
        "https:" + "//" + "cla." + "salesforce." + "com/sign-cla",
        "https:" + "//" + "github." + "com/SalesforceAIResearch/InterviewSim/issues",
    },
}
APPROVED_TEMPLATE_DIGESTS = {
    # pragma: allowlist nextline secret - SHA-256 checksum of the reviewed repository file.
    "CODEOWNERS": "bdb22edc9e12adacf9b808746d9d178233dd327322bda4c20b1836962435dab5",
    # pragma: allowlist nextline secret - SHA-256 checksum of the reviewed repository file.
    "CODE_OF_CONDUCT.md": "040016d1dc62e03b7bfdd52baea12a23f2321bbd019304746a90e0e15c2d59c3",
    # pragma: allowlist nextline secret - SHA-256 checksum of the reviewed repository file.
    "LICENSE.txt": "7bd3e1134121808826eece04ab5f6c808f24c4591234e5d6cf874b75801855e7",
    # pragma: allowlist nextline secret - SHA-256 checksum of the reviewed repository file.
    "SECURITY.md": "37caf6b653d0268398424ff0aeefdd5ffc5fd09db0b84b721a2bd676c4b8c775",
}
REQUIRED_RELEASE_FILES = {
    "CODEOWNERS",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE.txt",
    "README.md",
    "SECURITY.md",
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ALLOWED_BINARY_DIGESTS = {
    # pragma: allowlist nextline secret - SHA-256 checksum of the reviewed repository file.
    "assets/framework.png": ("60c13c7ce8b0293e4d24a413ef3f83b25bcc3bc8aaac5ad6fb43e0bd9a03fdd0"),
}

PROHIBITED_FIELDS = {
    "channel_id",
    "citation",
    "citations",
    "date",
    "dates",
    "domain",
    "domains",
    "external_id",
    "external_ids",
    "file_path",
    "origin",
    "origins",
    "platform",
    "platform_id",
    "provenance",
    "source",
    "source_id",
    "source_ids",
    "source_path",
    "source_paths",
    "source_pointer",
    "source_pointers",
    "source_uri",
    "source_uris",
    "source_url",
    "source_urls",
    "uri",
    "uris",
    "url",
    "urls",
    "video_id",
}
FREE_TEXT_FIELDS = {
    "answer",
    "explanation",
    "long_profile",
    "profile",
    "question",
    "rationale",
    "response",
    "summary",
    "text",
}
STRUCTURAL_ID_PATTERN = re.compile(
    r"\b(?:PERSONALITY|INTERVIEW|QA|FACT|ATOMIC_QA|MCQ|OPTION|RESPONSE)_"
)
CAPITALIZED_PATTERN = re.compile(r"\b[A-Z][a-z]+\b")
ALL_CAPS_PATTERN = re.compile(r"\b[A-Z]{2,}\b")
EXACT_DATE_PATTERN = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b")
MONTH_DATE_PATTERN = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2}\b"
)


class Audit:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def add(self, location: str, message: str) -> None:
        self.errors.append(f"{location}: {message}")

    def require(self, condition: bool, location: str, message: str) -> None:
        if not condition:
            self.add(location, message)


@dataclass
class CandidateSurface:
    files: dict[str, bytes]
    scanned_files: int = 0


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def load_private_denylist(path: Path | None, audit: Audit) -> list[str]:
    if path is None:
        return []
    resolved = path.expanduser().resolve()
    if path_is_within(resolved, REPO_ROOT.resolve()):
        audit.add(
            "private denylist",
            "runtime denylist must remain outside the release repository",
        )
        return []
    try:
        raw = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        audit.add("private denylist", f"could not read runtime file: {error}")
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        entries = [
            line.strip()
            for line in raw.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    else:
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            audit.add(
                "private denylist",
                "runtime file must be a string array or one entry per line",
            )
            return []
        entries = [item.strip() for item in parsed if item.strip()]
    normalized = sorted({entry.casefold() for entry in entries if len(entry) >= 3})
    if not normalized:
        audit.add("private denylist", "runtime file contains no usable entries")
    return normalized


def allowed_document_url(relative: str, url: str) -> bool:
    if url in ALLOWED_URLS_BY_FILE.get(relative, set()):
        return True
    is_documentation = relative in ALLOWED_DOCUMENT_FILES or relative.startswith("docs/")
    return is_documentation and url == ALLOWED_PAPER_URL


def scan_text(
    text: str,
    relative: str,
    denylist: list[str],
    audit: Audit,
    location: str,
    *,
    entry_name: bool,
) -> None:
    folded = text.casefold()
    subject = "entry name" if entry_name else "file content"
    if PROHIBITED_PUBLIC_STEM.casefold() in folded:
        audit.add(location, f"prohibited public terminology appears in {subject}")
    if PROHIBITED_BRAND.casefold() in folded:
        audit.add(location, f"prohibited branded phrase appears in {subject}")
    if any(entry in folded for entry in denylist):
        audit.add(location, "release scan matched a runtime private-denylist entry")
    if INTERNAL_PATH_PATTERN.search(text):
        audit.add(location, f"release scan detected an internal path in {subject}")
    if PRIVATE_NETWORK_PATTERN.search(text) or any(
        marker in folded for marker in INTERNAL_HOST_MARKERS
    ):
        audit.add(location, f"release scan detected an internal host in {subject}")
    if SECRET_PATTERN.search(text):
        audit.add(location, f"release scan detected an assigned secret in {subject}")
    if PRIVATE_KEY_PATTERN.search(text):
        audit.add(location, f"release scan detected private key material in {subject}")
    if SIGNED_TOKEN_PATTERN.search(text):
        audit.add(location, f"release scan detected a signed token in {subject}")
    if EMAIL_PATTERN.search(text):
        audit.add(location, f"release scan detected an email address in {subject}")
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:")
        if entry_name or not allowed_document_url(relative, url):
            audit.add(location, f"release scan detected an unapproved link in {subject}")
    if DOMAIN_PATTERN.search(URL_PATTERN.sub(" ", text)):
        audit.add(
            location,
            f"release scan detected an unapproved web domain in {subject}",
        )


def validate_no_prohibited_fields(
    value: Any,
    location: str,
    audit: Audit,
    path: tuple[str, ...] = (),
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).casefold().replace("-", "_")
            child_path = path + (str(key),)
            child_location = f"{location}:{'.'.join(child_path)}"
            if (
                normalized in PROHIBITED_FIELDS
                or normalized.startswith(("source_", "pointer_"))
                or normalized.endswith(("_url", "_uri", "_domain", "_file_path"))
            ):
                audit.add(child_location, "prohibited metadata field detected")
            validate_no_prohibited_fields(child, location, audit, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_prohibited_fields(child, location, audit, path + (str(index),))


def run_git(args: tuple[str, ...], audit: Audit, location: str) -> bytes | None:
    environment = os.environ.copy()
    for variable in (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_WORK_TREE",
    ):
        environment.pop(variable, None)
    try:
        result = subprocess.run(
            ["git", "-c", f"core.excludesFile={os.devnull}", *args],
            cwd=REPO_ROOT,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        audit.add(location, f"could not execute git: {error}")
        return None
    if result.returncode != 0:
        audit.add(location, f"git command failed with status {result.returncode}")
        return None
    return result.stdout


def parse_repository_path(raw_path: bytes, audit: Audit, location: str) -> str | None:
    relative = os.fsdecode(raw_path)
    parts = relative.split("/")
    if not relative or relative.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        audit.add(location, "git reported an invalid repository path")
        return None
    return relative


def scan_candidate(
    relative: str,
    data: bytes,
    denylist: list[str],
    audit: Audit,
    location: str,
) -> None:
    if relative != ".gitignore" and Path(relative).name == ".gitignore":
        audit.add(location, "nested ignore files are not allowed")
    scan_text(relative, relative, denylist, audit, location, entry_name=True)
    expected_template_digest = APPROVED_TEMPLATE_DIGESTS.get(relative)
    if expected_template_digest is not None:
        if hashlib.sha256(data).hexdigest() != expected_template_digest:
            audit.add(location, "Salesforce governance template differs from reviewed content")
        return
    expected_digest = ALLOWED_BINARY_DIGESTS.get(relative)
    if expected_digest is not None:
        if not data.startswith(PNG_SIGNATURE):
            audit.add(location, "approved image does not have a valid PNG signature")
        if hashlib.sha256(data).hexdigest() != expected_digest:
            audit.add(location, "approved image differs from its reviewed content")
        return
    lowered = data.lower()
    prohibited_encodings = (
        PROHIBITED_PUBLIC_STEM.encode("ascii"),
        PROHIBITED_PUBLIC_STEM.encode("utf-16-le"),
        PROHIBITED_PUBLIC_STEM.encode("utf-16-be"),
    )
    if any(encoded in lowered for encoded in prohibited_encodings):
        audit.add(location, "prohibited public terminology appears in file content")
    if b"\0" in data:
        audit.add(location, "unexpected binary file is not allowed")
        return
    text = data.decode("utf-8", errors="ignore")
    scan_text(text, relative, denylist, audit, location, entry_name=False)
    if relative.casefold().endswith(".json"):
        try:
            document = json.loads(text)
        except json.JSONDecodeError:
            return
        validate_no_prohibited_fields(document, location, audit)


def read_worktree_entry(
    relative: str,
    index_mode: str,
    audit: Audit,
    location: str,
) -> bytes | None:
    parts = relative.split("/")
    parent = REPO_ROOT
    for part in parts[:-1]:
        parent /= part
        try:
            status = parent.lstat()
        except OSError as error:
            audit.add(location, f"could not inspect tracked parent: {error}")
            return None
        if not stat.S_ISDIR(status.st_mode) or stat.S_ISLNK(status.st_mode):
            audit.add(location, "tracked worktree path type differs from index")
            return None
    path = REPO_ROOT.joinpath(*parts)
    try:
        status = path.lstat()
    except OSError as error:
        audit.add(location, f"could not inspect tracked entry: {error}")
        return None
    if index_mode == "120000":
        if not stat.S_ISLNK(status.st_mode):
            audit.add(location, "tracked worktree path type differs from index")
            return None
        return os.fsencode(os.readlink(path))
    if not index_mode.startswith("100"):
        audit.add(location, f"unsupported indexed file mode {index_mode}")
        return None
    if not stat.S_ISREG(status.st_mode):
        audit.add(location, "tracked worktree path type differs from index")
        return None
    try:
        return path.read_bytes()
    except OSError as error:
        audit.add(location, f"could not read tracked file: {error}")
        return None


def scan_repository(denylist: list[str], audit: Audit) -> CandidateSurface:
    files: dict[str, bytes] = {}
    scanned_files = 0
    entry_index = 0
    ignored_top_level = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "ENV",
        "build",
        "dist",
        "env",
        "venv",
    }
    for ignore_path in REPO_ROOT.rglob(".gitignore"):
        relative_parts = ignore_path.relative_to(REPO_ROOT).parts
        if relative_parts == (".gitignore",):
            continue
        if relative_parts[0] in ignored_top_level:
            continue
        if any(part == "__pycache__" or part.endswith(".egg-info") for part in relative_parts):
            continue
        audit.add("repository ignore policy", "nested ignore files are not allowed")

    index_output = run_git(("ls-files", "--stage", "-z"), audit, "git index")
    if index_output is not None:
        for raw_entry in index_output.split(b"\0"):
            if not raw_entry:
                continue
            entry_index += 1
            location = f"repository entry {entry_index}"
            header, separator, raw_path = raw_entry.partition(b"\t")
            fields = header.split()
            if not separator or len(fields) != 3:
                audit.add(location, "could not parse indexed entry")
                continue
            try:
                index_mode = fields[0].decode("ascii")
                object_id = fields[1].decode("ascii")
                stage = int(fields[2])
            except (UnicodeDecodeError, ValueError):
                audit.add(location, "could not parse indexed entry metadata")
                continue
            relative = parse_repository_path(raw_path, audit, location)
            if relative is None:
                continue
            if stage != 0:
                audit.add(location, "unmerged index stages are not releasable")
            blob = run_git(("cat-file", "blob", object_id), audit, location)
            if blob is None:
                continue
            scanned_files += 1
            scan_candidate(relative, blob, denylist, audit, location)
            if index_mode == "120000":
                audit.add(location, "symbolic links are not allowed")
            if stage != 0:
                continue
            if relative in files:
                audit.add(location, "duplicate path appears in candidate surface")
            else:
                files[relative] = blob
            worktree_data = read_worktree_entry(relative, index_mode, audit, location)
            if worktree_data is not None and worktree_data != blob:
                audit.add(location, "worktree content differs from index")

    untracked_output = run_git(
        ("ls-files", "--others", "--exclude-per-directory=.gitignore", "-z"),
        audit,
        "untracked files",
    )
    if untracked_output is not None:
        for raw_path in untracked_output.split(b"\0"):
            if not raw_path:
                continue
            entry_index += 1
            location = f"repository entry {entry_index}"
            relative = parse_repository_path(raw_path, audit, location)
            if relative is None:
                continue
            if Path(relative).name == ".gitignore":
                audit.add(location, "untracked nested ignore files are not allowed")
            path = REPO_ROOT.joinpath(*relative.split("/"))
            try:
                status = path.lstat()
            except OSError as error:
                audit.add(location, f"could not inspect untracked entry: {error}")
                continue
            if stat.S_ISLNK(status.st_mode):
                audit.add(location, "symbolic links are not allowed")
                data = os.fsencode(os.readlink(path))
            elif stat.S_ISREG(status.st_mode):
                data = path.read_bytes()
            else:
                audit.add(location, "untracked entry is not a regular file")
                continue
            scanned_files += 1
            scan_candidate(relative, data, denylist, audit, location)
            if relative in files:
                audit.add(location, "duplicate path appears in candidate surface")
            else:
                files[relative] = data
    return CandidateSurface(files=files, scanned_files=scanned_files)


def load_json(path: Path, audit: Audit, surface: CandidateSurface) -> Any | None:
    relative = path.relative_to(REPO_ROOT).as_posix()
    data = surface.files.get(relative)
    if data is None:
        audit.add(relative, "required file is missing from candidate surface")
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        audit.add(relative, f"could not load valid utf-8 json: {error}")
        return None


def iter_strings(
    value: Any,
    path: tuple[str, ...] = (),
    field_name: str | None = None,
) -> Iterable[tuple[str, str | None, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_strings(child, path + (str(key),), str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_strings(child, path + (str(index),), field_name)
    elif isinstance(value, str):
        yield ".".join(path), field_name, value


def validate_fixture_text(
    document: Any,
    location: str,
    audit: Audit,
) -> None:
    for json_path, field_name, text in iter_strings(document):
        if field_name not in FREE_TEXT_FIELDS:
            continue
        item_location = f"{location}:{json_path}"
        if STRUCTURAL_ID_PATTERN.search(text):
            audit.add(item_location, "structural identifier appears in free text")
        if EXACT_DATE_PATTERN.search(text) or MONTH_DATE_PATTERN.search(text):
            audit.add(item_location, "exact calendar date appears in free text")
        if ALL_CAPS_PATTERN.search(text):
            audit.add(item_location, "proper-noun-like capital token appears in free text")
        for match in CAPITALIZED_PATTERN.finditer(text):
            prefix = text[: match.start()].rstrip()
            sentence_start = not prefix or prefix[-1] in ".?!"
            if match.group(0) != "I" and not sentence_start:
                audit.add(
                    item_location,
                    "proper-noun-like named entity appears in free text",
                )
                break


def validate_canonical_contract(
    document: Any,
    ordinal: int,
    allowed_tags: set[str],
    audit: Audit,
) -> None:
    location = f"PERSONALITY_{ordinal:03d}/prepared_input.json"
    if not isinstance(document, dict):
        audit.add(location, "canonical input must be an object")
        return
    audit.require(
        list(document) == ["schema_version", "personality_id", "personality", "interviews"],
        location,
        "canonical top-level contract is invalid",
    )
    interviews = document.get("interviews")
    if not isinstance(interviews, list):
        audit.add(location, "interviews must be an array")
        return
    audit.require(
        len(interviews) == fixture_generator.INTERVIEW_COUNT,
        location,
        "interview count is invalid",
    )
    for interview_position, interview in enumerate(interviews, start=1):
        item_location = f"{location}:interviews[{interview_position - 1}]"
        if not isinstance(interview, dict):
            audit.add(item_location, "interview must be an object")
            continue
        audit.require(
            list(interview) == ["interview_id", "sequence", "qa_pairs"],
            item_location,
            "interview contract is invalid",
        )
        audit.require(
            interview.get("sequence") == interview_position,
            item_location,
            "interview sequence is invalid",
        )
        pairs = interview.get("qa_pairs")
        if not isinstance(pairs, list):
            audit.add(item_location, "qa_pairs must be an array")
            continue
        audit.require(
            len(pairs) == fixture_generator.QA_PER_INTERVIEW,
            item_location,
            "q&a count is invalid",
        )
        for pair_position, pair in enumerate(pairs):
            pair_location = f"{item_location}:qa_pairs[{pair_position}]"
            if not isinstance(pair, dict):
                audit.add(pair_location, "q&a pair must be an object")
                continue
            audit.require(
                list(pair) == ["qa_id", "question", "response", "tags"],
                pair_location,
                "q&a contract is invalid",
            )
            question = pair.get("question")
            response = pair.get("response")
            sentence_count = (
                len(re.findall(r"[.!?](?:\s|$)", response)) if isinstance(response, str) else 0
            )
            audit.require(
                isinstance(question, str)
                and isinstance(response, str)
                and question.strip().endswith(("?", "."))
                and len(question.split()) >= 3
                and len(response.split()) >= 8
                and 2 <= sentence_count <= 4,
                pair_location,
                "q&a text is not plausible interview prose",
            )
            tags = pair.get("tags")
            audit.require(
                isinstance(tags, list)
                and len(tags) == 2
                and len(set(tags)) == 2
                and all(
                    isinstance(tag, str) and tag in allowed_tags and re.fullmatch(r"[a-z]+", tag)
                    for tag in tags
                ),
                pair_location,
                "q&a tags are not registered generic terms",
            )


def validate_release_files(audit: Audit, surface: CandidateSurface) -> None:
    for relative in sorted(REQUIRED_RELEASE_FILES):
        audit.require(
            relative in surface.files,
            relative,
            "required Salesforce open-source governance file is missing",
        )
    audit.require(
        "how_to_license.md" not in surface.files,
        "how_to_license.md",
        "template instruction file must not be included in the project release",
    )


def validate_fixture(audit: Audit, surface: CandidateSurface) -> dict[str, int]:
    expected_documents = fixture_generator.build_fixture_documents()
    fixture_prefix = FIXTURE_ROOT.relative_to(REPO_ROOT).as_posix() + "/"
    actual_relative = {
        relative[len(fixture_prefix) :]
        for relative in surface.files
        if relative.startswith(fixture_prefix)
    }
    audit.require(
        actual_relative == set(expected_documents),
        "fixture",
        "fixture files differ from deterministic generator output",
    )
    registry = expected_documents["manifest.json"]["profile_registry"]
    allowed_tags_by_personality = {
        item["personality_id"]: set(item["allowed_tags"]) for item in registry
    }
    for relative, expected in expected_documents.items():
        path = FIXTURE_ROOT.joinpath(*relative.split("/"))
        candidate_relative = fixture_prefix + relative
        expected_bytes = fixture_generator.serialize(expected).encode("utf-8")
        audit.require(
            surface.files.get(candidate_relative) == expected_bytes,
            relative,
            "serialized bytes differ from deterministic generator output",
        )
        actual = load_json(path, audit, surface)
        if actual is None:
            continue
        audit.require(
            actual == expected,
            relative,
            "serialized content differs from deterministic generator output",
        )
        validate_fixture_text(actual, relative, audit)
        if relative.endswith("/prepared_input.json"):
            pid = expected["personality_id"]
            ordinal = int(pid.rsplit("_", 1)[1])
            validate_canonical_contract(
                actual,
                ordinal,
                allowed_tags_by_personality[pid],
                audit,
            )
    return fixture_generator.summary_counts()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="audit the release candidate and fictional examples"
    )
    parser.add_argument(
        "--private-denylist",
        type=Path,
        default=None,
        help="optional runtime-only text file or json string array",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = Audit()
    denylist = load_private_denylist(args.private_denylist, audit)
    surface = scan_repository(denylist, audit)
    validate_release_files(audit, surface)
    totals = validate_fixture(audit, surface)
    print(
        json.dumps(
            {
                "valid": not audit.errors,
                "repository_files_scanned": surface.scanned_files,
                "private_denylist_entries": len(denylist),
                **totals,
            },
            sort_keys=True,
        )
    )
    if audit.errors:
        for error in audit.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
