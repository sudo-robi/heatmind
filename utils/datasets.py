import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CDC_HEAT_VULNERABILITY = {
    "high": {
        "elderly_pct_above_20": True,
        "ac_penetration_below_50": True,
        "heat_death_rate_high": True,
    },
    "medium": {
        "elderly_pct_above_15": True,
        "ac_penetration_below_70": True,
    },
    "low": {},
}

US_CENSUS_TRACTS = {
    (40.71, -74.01): {"tract": "36061000100", "pop_density": 72033, "median_income": 82459, "elderly_pct": 12.3},
    (40.76, -73.98): {"tract": "36061013800", "pop_density": 45127, "median_income": 135000, "elderly_pct": 14.1},
    (34.05, -118.24): {"tract": "06037206000", "pop_density": 13098, "median_income": 62480, "elderly_pct": 11.8},
    (41.88, -87.63): {"tract": "17031080300", "pop_density": 15234, "median_income": 85000, "elderly_pct": 13.5},
    (29.76, -95.37): {"tract": "48201100000", "pop_density": 8567, "median_income": 52300, "elderly_pct": 10.2},
    (33.45, -112.07): {"tract": "04013107600", "pop_density": 6789, "median_income": 48200, "elderly_pct": 15.7},
    (25.76, -80.19): {"tract": "12086000100", "pop_density": 10234, "median_income": 42100, "elderly_pct": 16.8},
    (47.61, -122.33): {"tract": "53033000100", "pop_density": 8901, "median_income": 95000, "elderly_pct": 11.2},
    (38.91, -77.04): {"tract": "11001000100", "pop_density": 10546, "median_income": 88000, "elderly_pct": 12.8},
    (42.36, -71.06): {"tract": "25025000100", "pop_density": 13456, "median_income": 76000, "elderly_pct": 11.9},
}

HEAT_RISK_FACTORS = {
    "elderly_population": {"weight": 0.25, "threshold": 0.15},
    "low_income": {"weight": 0.20, "threshold": 40000},
    "high_density": {"weight": 0.15, "threshold": 10000},
    "low_ac": {"weight": 0.20, "threshold": 0.6},
    "outdoor_workers": {"weight": 0.10, "threshold": 0.05},
    "pre_existing_conditions": {"weight": 0.10, "threshold": 0.3},
}


@dataclass
class LocationContext:
    latitude: float
    longitude: float
    city: str = "Unknown"
    state: str = "Unknown"
    census_tract: str | None = None
    population_density: int | None = None
    median_income: int | None = None
    elderly_pct: float | None = None
    heat_vulnerability: str = "unknown"
    risk_score: float = 0.0
    risk_factors: list = None
    data_sources: list = None

    def __post_init__(self):
        if self.risk_factors is None:
            self.risk_factors = []
        if self.data_sources is None:
            self.data_sources = []

    def to_dict(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city": self.city,
            "state": self.state,
            "census_tract": self.census_tract,
            "population_density": self.population_density,
            "median_income": self.median_income,
            "elderly_pct": self.elderly_pct,
            "heat_vulnerability": self.heat_vulnerability,
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "data_sources": self.data_sources,
        }


def _find_closest_tract(lat: float, lon: float) -> dict | None:
    min_dist = float("inf")
    closest = None
    for (tlat, tlon), data in US_CENSUS_TRACTS.items():
        dist = ((lat - tlat) ** 2 + (lon - tlon) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            closest = data
    if min_dist < 1.0:
        return closest
    return None


def _calculate_risk_score(context: LocationContext) -> float:
    score = 0.0
    factors = []

    if context.elderly_pct and context.elderly_pct > HEAT_RISK_FACTORS["elderly_population"]["threshold"]:
        score += HEAT_RISK_FACTORS["elderly_population"]["weight"]
        factors.append(f"Elderly population {context.elderly_pct}% exceeds 15% threshold")

    if context.median_income and context.median_income < HEAT_RISK_FACTORS["low_income"]["threshold"]:
        score += HEAT_RISK_FACTORS["low_income"]["weight"]
        factors.append(f"Median income ${context.median_income:,} below $40k threshold")

    if context.population_density and context.population_density > HEAT_RISK_FACTORS["high_density"]["threshold"]:
        score += HEAT_RISK_FACTORS["high_density"]["weight"]
        factors.append(f"Population density {context.population_density:,}/mi² exceeds 10k threshold")

    return min(score, 1.0), factors


def get_location_context(latitude: float, longitude: float) -> LocationContext:
    context = LocationContext(latitude=latitude, longitude=longitude)

    tract_data = _find_closest_tract(latitude, longitude)
    if tract_data:
        context.census_tract = tract_data["tract"]
        context.population_density = tract_data["pop_density"]
        context.median_income = tract_data["median_income"]
        context.elderly_pct = tract_data["elderly_pct"]
        context.data_sources.append("US Census Bureau (simulated)")

    risk_score, risk_factors = _calculate_risk_score(context)
    context.risk_score = risk_score
    context.risk_factors = risk_factors

    if risk_score >= 0.6:
        context.heat_vulnerability = "high"
    elif risk_score >= 0.3:
        context.heat_vulnerability = "medium"
    else:
        context.heat_vulnerability = "low"

    if context.data_sources:
        context.data_sources.append("CDC Heat Vulnerability Index (simulated)")

    return context


def format_location_context(context: LocationContext) -> str:
    lines = [f"**Location Context ({context.latitude:.4f}, {context.longitude:.4f}):**"]
    lines.append(f"  - Census Tract: {context.census_tract or 'N/A'}")
    lines.append(
        f"  - Population Density: {context.population_density:,}/mi²"
        if context.population_density
        else "  - Population Density: N/A"
    )
    lines.append(
        f"  - Median Income: ${context.median_income:,}" if context.median_income else "  - Median Income: N/A"
    )
    lines.append(
        f"  - Elderly Population: {context.elderly_pct}%" if context.elderly_pct else "  - Elderly Population: N/A"
    )
    lines.append(f"  - Heat Vulnerability: {context.heat_vulnerability.upper()}")
    lines.append(f"  - Risk Score: {context.risk_score:.2f}/1.00")
    if context.risk_factors:
        lines.append("  - Risk Factors:")
        for factor in context.risk_factors:
            lines.append(f"    • {factor}")
    return "\n".join(lines)
