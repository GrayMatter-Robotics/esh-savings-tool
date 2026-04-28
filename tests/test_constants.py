from esh_savings.constants.vibration import HAV_EAV, HAV_ELV, SHIFT_DURATION_S, HAVS_ONSET_COEFF
from esh_savings.constants.ergonomics import SNOOK_PUSH_LIMIT_N, STRAIN_INDEX_HAZARD
from esh_savings.constants.economics import (
    DIRECT_CLAIM_COST_USD, TOTAL_CLAIM_COST_USD, MANUAL_MSD_IR, ROBOT_MSD_IR,
    WAGE_INFLATION_RATE, ROBOT_LOAD_UNLOAD_FRACTION,
)
from esh_savings.constants.regulatory import OSHA_INSPECTION_PROB, OSHA_CITATION_PROB


def test_vibration_thresholds_are_iso_values():
    assert HAV_EAV == 2.5
    assert HAV_ELV == 5.0
    assert SHIFT_DURATION_S == 28_800


def test_total_claim_cost_consistent():
    # TOTAL_CLAIM_COST_USD is a published round figure; verify it is >= DIRECT
    assert TOTAL_CLAIM_COST_USD > DIRECT_CLAIM_COST_USD


def test_robot_ir_below_manual():
    assert ROBOT_MSD_IR < MANUAL_MSD_IR


def test_osha_probabilities_are_fractions():
    assert 0 < OSHA_INSPECTION_PROB < 1
    assert 0 < OSHA_CITATION_PROB < 1


def test_ergonomics_constants_are_positive():
    from esh_savings.constants.ergonomics import (
        ISO_INITIAL_PUSH_N, ISO_SUSTAINED_PUSH_N,
        OCRA_VIBRATION_MULTIPLIER, STRAIN_INDEX_HAZARD,
    )
    assert ISO_INITIAL_PUSH_N == 250.0
    assert ISO_SUSTAINED_PUSH_N == 150.0
    assert 0 < OCRA_VIBRATION_MULTIPLIER < 1
    assert STRAIN_INDEX_HAZARD == 7.0


def test_osha_penalty_schedule():
    from esh_savings.constants.regulatory import (
        OSHA_SERIOUS_MAX_USD, OSHA_WILLFUL_MAX_USD, OSHA_EXPECTED_PENALTY_USD,
    )
    assert OSHA_SERIOUS_MAX_USD == 16_550.0
    assert OSHA_WILLFUL_MAX_USD == 165_514.0
    assert OSHA_EXPECTED_PENALTY_USD < OSHA_SERIOUS_MAX_USD  # expected penalty is below max
