import numpy as np
import pytest
from esh_savings.pipeline.ingestion import load_session
from esh_savings.pipeline.features import extract_features
from esh_savings.models.config import AnalysisConfig
from esh_savings.models.features import ExposureFeatures


def test_vibration_features_populated(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    cfg = AnalysisConfig(include_vibration=True, include_force=False, include_orientation=False)
    features = extract_features(session, cfg)

    assert features.ahv is not None
    assert features.a8 is not None
    assert features.a8 > 0
    assert features.hal is None   # force disabled


def test_force_features_populated(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    cfg = AnalysisConfig(include_vibration=False, include_force=True, include_orientation=False)
    features = extract_features(session, cfg)

    assert features.fz_p50 is not None
    assert features.fz_p90 >= features.fz_p50
    assert features.duty_cycle is not None
    assert 0.0 <= features.duty_cycle <= 1.0
    assert features.si_factors is not None
    assert features.ahv is None   # vibration disabled


def test_disabled_channels_produce_none(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    cfg = AnalysisConfig(include_vibration=False, include_force=False, include_orientation=False)
    features = extract_features(session, cfg)

    assert features.ahv is None
    assert features.a8 is None
    assert features.fz_p50 is None
    assert features.si_factors is None
    assert features.arm_elevation_deg is None
    assert features.wrist_pronation_deg is None


def test_a8_normalizes_to_shift(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    cfg = AnalysisConfig(include_vibration=True, include_force=False, include_orientation=False)
    features_8h = extract_features(session, cfg, shift_duration_s=28_800.0)
    features_10h = extract_features(session, cfg, shift_duration_s=36_000.0)

    # Longer shift → lower A(8) for same exposure time
    assert features_10h.a8 < features_8h.a8


def test_si_factors_product_is_positive(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    cfg = AnalysisConfig(include_vibration=False, include_force=True, include_orientation=False)
    features = extract_features(session, cfg)

    f = features.si_factors
    si = f.im * f.du * f.em * f.hwp * f.sw * f.dd
    assert si > 0
