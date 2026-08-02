from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.export_event_class_package import (
    build_manifest_entries,
    copy_supporting_docs,
)
from scripts.validate_event_class_package import verify_manifest


class EventClassPackageToolTests(unittest.TestCase):
    def write_manifest(self, package_dir: Path) -> Path:
        manifest = package_dir / "MANIFEST.sha256"
        manifest.write_text(
            "".join(
                f"{digest}  {relative_path}\n"
                for digest, relative_path in build_manifest_entries(package_dir)
            ),
            encoding="utf-8",
        )
        return manifest

    def make_minimal_package(self, root: Path) -> Path:
        package = root / "event_class_records_test"
        records = package / "records"
        records.mkdir(parents=True)
        (package / "VALIDATION.md").write_text("validation\n", encoding="utf-8")
        (package / "expected_stats.json").write_text("{}\n", encoding="utf-8")
        (records / "evt_test.json").write_text("{}\n", encoding="utf-8")
        return package

    def test_supporting_docs_are_copied_and_manifest_attested(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            package = self.make_minimal_package(root)
            source = root / "ERRATA.md"
            source.write_text("erratum\n", encoding="utf-8")

            copied = copy_supporting_docs(package, [source])
            self.assertEqual(copied, ["docs/ERRATA.md"])
            manifest = self.write_manifest(package)

            verify_manifest(package, manifest)
            manifest_text = manifest.read_text(encoding="utf-8")
            expected_hash = hashlib.sha256(b"erratum\n").hexdigest()
            self.assertIn(f"{expected_hash}  docs/ERRATA.md", manifest_text)

    def test_validator_rejects_unlisted_package_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            package = self.make_minimal_package(root)
            manifest = self.write_manifest(package)
            docs = package / "docs"
            docs.mkdir()
            (docs / "UNLISTED.md").write_text("not attested\n", encoding="utf-8")

            with self.assertRaisesRegex(SystemExit, "unlisted=.*docs/UNLISTED.md"):
                verify_manifest(package, manifest)

    def test_duplicate_supporting_doc_names_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            package = self.make_minimal_package(root)
            first = root / "first" / "NOTE.md"
            second = root / "second" / "NOTE.md"
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_text("first\n", encoding="utf-8")
            second.write_text("second\n", encoding="utf-8")

            with self.assertRaisesRegex(SystemExit, "duplicate supporting-document filename"):
                copy_supporting_docs(package, [first, second])


if __name__ == "__main__":
    unittest.main()
