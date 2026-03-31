"""Tests for the generator module."""

from pathlib import Path

import pytest

from dotsync.analyzer import DotfileAnalyzer
from dotsync.compatibility import CompatibilityChecker
from dotsync.conflict_detector import ConflictDetector
from dotsync.generator import MigrationGenerator
from dotsync.models import MigrationPlan


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def analyses(fixtures_dir: Path) -> list:
    analyzer = DotfileAnalyzer(fixtures_dir)
    return analyzer.analyze_all()


@pytest.fixture
def generator() -> MigrationGenerator:
    return MigrationGenerator()


@pytest.fixture
def checker() -> CompatibilityChecker:
    return CompatibilityChecker()


@pytest.fixture
def conflict_detector() -> ConflictDetector:
    return ConflictDetector()


class TestMigrationGenerator:
    """Tests for MigrationGenerator."""

    def test_generate_migration_script(
        self,
        generator: MigrationGenerator,
        analyses: list,
        checker: CompatibilityChecker,
        conflict_detector: ConflictDetector,
    ) -> None:
        plan = generator.generate_migration_script(
            analyses=analyses,
            target_platform="linux-ubuntu",
            source_platform="macos",
            compatibility_checker=checker,
            conflict_detector=conflict_detector,
        )
        assert isinstance(plan, MigrationPlan)
        assert plan.target_platform == "linux-ubuntu"
        assert len(plan.steps) > 0

    def test_render_install_script(
        self,
        generator: MigrationGenerator,
        analyses: list,
        checker: CompatibilityChecker,
        conflict_detector: ConflictDetector,
    ) -> None:
        plan = generator.generate_migration_script(
            analyses=analyses,
            target_platform="linux-ubuntu",
            source_platform="macos",
            compatibility_checker=checker,
            conflict_detector=conflict_detector,
        )
        script = generator.render_install_script(plan)
        assert "#!/usr/bin/env bash" in script
        assert "linux-ubuntu" in script

    def test_render_rollback_script(self, generator: MigrationGenerator) -> None:
        plan = MigrationPlan(
            source_platform="macos",
            target_platform="linux-ubuntu",
            steps=[],
        )
        script = generator.render_rollback_script(plan)
        assert "#!/usr/bin/env bash" in script
        assert "Rollback" in script

    def test_save_script(self, generator: MigrationGenerator, tmp_path: Path) -> None:
        content = "#!/usr/bin/env bash\necho test"
        output_path = tmp_path / "test.sh"
        generator.save_script(content, output_path)
        assert output_path.exists()
        assert output_path.read_text() == content

    def test_estimate_time(self, generator: MigrationGenerator) -> None:
        from dotsync.models import MigrationStep

        steps = [
            MigrationStep(order=1, action="install", description="Install pkg", command="brew install pkg"),
            MigrationStep(order=2, action="install", description="Install pkg2", command="brew install pkg2"),
            MigrationStep(order=3, action="copy", description="Copy file", command="cp file1 file2"),
        ]
        time = generator._estimate_time(steps)
        assert isinstance(time, str)
