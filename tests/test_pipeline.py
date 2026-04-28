from esh_savings.pipeline.ingestion import load_session
from esh_savings.pipeline import Pipeline
from esh_savings.models.config import AnalysisConfig
from esh_savings.models.se_inputs import SEProvidedInputs
from esh_savings.models.result import ESHResult
from esh_savings.pipeline.standards.jurisdictions.us import USAdapter


def test_pipeline_run_returns_esh_result(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    pipeline = Pipeline(
        config=AnalysisConfig(),
        se_inputs=SEProvidedInputs(operator_count=5),
        adapter=USAdapter(),
    )
    result = pipeline.run(session)
    assert isinstance(result, ESHResult)


def test_pipeline_risk_scores_in_range(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    pipeline = Pipeline(
        config=AnalysisConfig(),
        se_inputs=SEProvidedInputs(operator_count=5),
        adapter=USAdapter(),
    )
    result = pipeline.run(session)
    assert 0.0 <= result.esh_risk_score_manual <= 100.0
    assert 0.0 <= result.esh_risk_score_robot  <= 100.0


def test_pipeline_savings_positive(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    pipeline = Pipeline(
        config=AnalysisConfig(),
        se_inputs=SEProvidedInputs(operator_count=5),
        adapter=USAdapter(),
    )
    result = pipeline.run(session)
    assert result.annual_esh_savings_usd > 0


def test_pipeline_respects_analysis_config(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    pipeline = Pipeline(
        config=AnalysisConfig(include_vibration=False, include_force=True, include_orientation=False),
        se_inputs=SEProvidedInputs(operator_count=1),
        adapter=USAdapter(),
    )
    result = pipeline.run(session)
    # With only force enabled, HAVS onset should not be computed
    assert result.havs_onset_estimate is None


def test_pipeline_public_import():
    from esh_savings.pipeline import Pipeline
    from esh_savings.pipeline.ingestion import load_session
    from esh_savings.pipeline.standards.jurisdictions.us import USAdapter
    assert Pipeline
    assert load_session
    assert USAdapter
