from pydantic import BaseModel


class AnalysisConfig(BaseModel):
    include_vibration:   bool = True
    include_force:       bool = True
    include_orientation: bool = True  # Phase 3; False = "Not analysed" in Excel
