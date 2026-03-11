# Environment Template for Behave Tests
# Place this in: features/environment.py

"""
Behave hooks for test lifecycle management.

Hook execution order:
    before_all
      before_feature
        before_scenario
          before_step
            [step execution]
          after_step
        after_scenario
      after_feature
    after_all
"""

import os
import tempfile
from pathlib import Path

# Import your application components
from app.core.application.diagram_service import DiagramService
from app.adapter.driven.persistence.in_memory_repository import InMemoryDiagramRepository
from app.adapter.driven.analyzer.test_analyzer import TestDiagramAnalyzer


# ============================================================================
# ALL FEATURES
# ============================================================================

def before_all(context):
    """
    Run once before all features.
    
    Use for:
        - Loading global configuration
        - Setting up test database connections (if needed)
        - Initializing test clients
        - Setting global test constants
    """
    # Load test configuration
    context.test_config = {
        'base_url': 'http://localhost:8000',
        'timeout': 30,
        'max_file_size': 10 * 1024 * 1024,  # 10MB
    }
    
    # Create temp directory for test files
    context.temp_dir = tempfile.mkdtemp(prefix='behave_tests_')
    
    # Set up test data directory
    context.fixtures_dir = Path(__file__).parent.parent / 'tests' / 'fixtures'
    
    print("\n=== Test Environment Initialized ===")
    print(f"Temp directory: {context.temp_dir}")
    print(f"Fixtures directory: {context.fixtures_dir}")


def after_all(context):
    """
    Run once after all features.
    
    Use for:
        - Cleaning up global resources
        - Closing database connections
        - Removing temporary directories
        - Generating test reports
    """
    # Clean up temp directory
    import shutil
    if hasattr(context, 'temp_dir') and os.path.exists(context.temp_dir):
        shutil.rmtree(context.temp_dir)
        print(f"\nCleaned up temp directory: {context.temp_dir}")


# ============================================================================
# PER FEATURE
# ============================================================================

def before_feature(context, feature):
    """
    Run before each feature file.
    
    Use for:
        - Feature-specific setup
        - Loading feature-specific fixtures
        - Setting feature-level configuration
    """
    print(f"\n--- Starting Feature: {feature.name} ---")
    
    # Feature-specific initialization based on tags
    if 'database' in feature.tags:
        # Set up in-memory database for this feature
        context.database = setup_test_database()
    
    if 'api' in feature.tags:
        # Initialize test HTTP client
        from app.main import create_app
        app = create_app(test_mode=True)
        context.test_client = app.test_client()


def after_feature(context, feature):
    """
    Run after each feature file.
    
    Use for:
        - Feature-specific cleanup
        - Collecting feature-level metrics
    """
    print(f"--- Completed Feature: {feature.name} ---")
    
    # Clean up feature-specific resources
    if hasattr(context, 'database'):
        context.database.close()


# ============================================================================
# PER SCENARIO
# ============================================================================

def before_scenario(context, scenario):
    """
    Run before each scenario.
    
    Use for:
        - Creating fresh test dependencies (most common)
        - Initializing scenario-specific state
        - Setting up test doubles
        - Resetting test data
    
    IMPORTANT: Create fresh instances here to ensure test isolation.
    """
    # Initialize empty lists for tracking resources
    context.temp_files = []
    context.created_diagrams = []
    
    # Create fresh test doubles for hexagonal architecture
    # Driven adapters (infrastructure)
    context.repository = InMemoryDiagramRepository()
    context.analyzer = TestDiagramAnalyzer()
    
    # Application service (orchestrator)
    context.service = DiagramService(
        repository=context.repository,
        analyzer=context.analyzer
    )
    
    # Tag-based conditional setup
    if 'slow' in scenario.effective_tags:
        context.timeout = 60  # Longer timeout for slow tests
    else:
        context.timeout = 10
    
    if 'mock-external' in scenario.effective_tags:
        # Mock external API calls
        setup_external_mocks(context)
    
    # Print scenario info for debugging
    if context.config.userdata.get('verbose'):
        print(f"\n>>> Scenario: {scenario.name}")
        print(f"    Tags: {scenario.effective_tags}")


def after_scenario(context, scenario):
    """
    Run after each scenario.
    
    Use for:
        - Cleaning up temporary resources
        - Clearing test data
        - Resetting mocks
        - Capturing screenshots on failure (for UI tests)
    
    CRITICAL: Always clean up resources created during the scenario.
    """
    # Clean up temporary files
    for temp_file in getattr(context, 'temp_files', []):
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    # Clear repository data
    if hasattr(context, 'repository'):
        context.repository.clear()
    
    # Remove test diagrams
    for diagram_id in getattr(context, 'created_diagrams', []):
        try:
            context.repository.delete(diagram_id)
        except Exception:
            pass  # Already deleted
    
    # Capture failure info for debugging
    if scenario.status == 'failed':
        print(f"\n!!! Scenario Failed: {scenario.name}")
        
        # Print error details if available
        if hasattr(context, 'error') and context.error:
            print(f"    Error: {context.error}")
        
        # Could save logs, screenshots, or state dumps here
        save_failure_context(context, scenario)


# ============================================================================
# PER STEP (Usually not needed, but available)
# ============================================================================

def before_step(context, step):
    """
    Run before each step.
    
    Use sparingly - usually not needed.
    Can slow down tests significantly.
    """
    pass


def after_step(context, step):
    """
    Run after each step.
    
    Useful for:
        - Detailed logging during debugging
        - Step-level timing/profiling
    """
    # Only run in verbose mode
    if context.config.userdata.get('debug'):
        print(f"  Step: {step.keyword} {step.name} ({step.status})")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def setup_test_database():
    """Set up in-memory test database."""
    # Example: SQLite in-memory
    from sqlalchemy import create_engine
    from app.adapter.driven.persistence.database import Base
    
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine


def setup_external_mocks(context):
    """Mock external API calls."""
    from unittest.mock import Mock, patch
    
    # Example: Mock AWS S3
    context.s3_mock = Mock()
    context.s3_patcher = patch('boto3.client', return_value=context.s3_mock)
    context.s3_patcher.start()
    
    # Remember to stop in after_scenario:
    # context.s3_patcher.stop()


def save_failure_context(context, scenario):
    """Save context state when scenario fails for debugging."""
    failure_dir = Path(context.temp_dir) / 'failures'
    failure_dir.mkdir(exist_ok=True)
    
    failure_file = failure_dir / f"{scenario.name.replace(' ', '_')}.txt"
    
    with open(failure_file, 'w') as f:
        f.write(f"Scenario: {scenario.name}\n")
        f.write(f"Status: {scenario.status}\n\n")
        
        # Dump relevant context
        f.write("Context State:\n")
        for key, value in context.__dict__.items():
            if not key.startswith('_') and not callable(value):
                f.write(f"  {key}: {value}\n")
    
    print(f"    Debug info saved to: {failure_file}")


# ============================================================================
# TAG-BASED BEHAVIOR
# ============================================================================

def before_tag(context, tag):
    """
    Run when entering a tagged section.
    
    Useful for:
        - Setting up resources only for tagged scenarios
        - Skipping scenarios based on environment
    """
    if tag == 'skip':
        context.scenario.skip("Marked with @skip tag")
    
    if tag == 'wip':
        print("\n*** Work in Progress - Test under development ***")
    
    if tag == 'requires-aws':
        if not os.getenv('AWS_CREDENTIALS_CONFIGURED'):
            context.scenario.skip("AWS credentials not configured")


def after_tag(context, tag):
    """Run when exiting a tagged section."""
    pass


# ============================================================================
# CUSTOM INITIALIZATION
# ============================================================================

def pytest_configure(config):
    """
    Optional: If using pytest-bdd instead of pure behave.
    """
    pass
