"""ESH savings analysis pipeline: stages 2 (features) → 3 (standards) → 5 (savings)."""
from esh_savings.models.session import SandingSession
from esh_savings.models.config import AnalysisConfig
from esh_savings.models.se_inputs import SEProvidedInputs
from esh_savings.models.result import ESHResult
from esh_savings.pipeline.features import extract_features
from esh_savings.pipeline.standards.evaluator import evaluate
from esh_savings.pipeline.savings import compute_savings


class Pipeline:
    def __init__(
        self,
        config: AnalysisConfig,
        se_inputs: SEProvidedInputs,
        adapter,
    ) -> None:
        self.config = config
        self.se_inputs = se_inputs
        self.adapter = adapter

    def run(self, session: SandingSession) -> ESHResult:
        features = self._stage2_features(session)
        scores   = self._stage3_standards(features)
        # Stage 4 (cost calibration) — Phase 2
        result   = self._stage5_savings(scores)
        return result

    def _stage2_features(self, session: SandingSession):
        return extract_features(session, self.config, self.se_inputs.shift_duration_s)

    def _stage3_standards(self, features):
        return evaluate(features, self.adapter)

    def _stage5_savings(self, scores):
        return compute_savings(scores, self.se_inputs, self.config)
