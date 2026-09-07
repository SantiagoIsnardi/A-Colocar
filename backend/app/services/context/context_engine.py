"""
Combina forma reciente, H2H por sede, perfil de árbitro y proxy de
motivación en un multiplicador de ajuste sobre los lambda base del
Prediction Engine.

Cada factor está limitado individualmente para que uno solo no pueda
distorsionar el resultado completo — evita amplificar ruido cuando se
combinan varios ajustes sobre muestras ya chicas.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.services.context.form_calculator import FormCalculator
from app.services.context.head_to_head import HeadToHeadService
from app.services.context.motivation_score import MotivationScore
from app.services.context.referee_analyzer import RefereeAnalyzer

MAX_FACTOR_ADJUSTMENT = 0.15  # ningún factor individual puede mover el lambda más de ±15%


class ContextEngine:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.form_calculator = FormCalculator(session)
        self.h2h_service = HeadToHeadService(session)
        self.referee_analyzer = RefereeAnalyzer(session)
        self.motivation_score = MotivationScore(session)

    @staticmethod
    def _clamp_adjustment(raw_adjustment: float) -> float:
        return max(-MAX_FACTOR_ADJUSTMENT, min(MAX_FACTOR_ADJUSTMENT, raw_adjustment))

    async def get_match_context(
        self,
        home_team_id: int,
        away_team_id: int,
        referee_name: str | None = None,
    ) -> dict:
        home_form = await self.form_calculator.get_form_score(home_team_id)
        away_form = await self.form_calculator.get_form_score(away_team_id)

        h2h = await self.h2h_service.get_home_vs_away_history(home_team_id, away_team_id)

        referee_profile = await self.referee_analyzer.get_referee_profile(referee_name)

        home_motivation = await self.motivation_score.get_trend_score(home_team_id)
        away_motivation = await self.motivation_score.get_trend_score(away_team_id)

        # Ajuste de forma: score 0.5 es neutro, por encima/debajo mueve el lambda
        home_form_adjustment = self._clamp_adjustment((home_form["form_score"] - 0.5) * 0.3)
        away_form_adjustment = self._clamp_adjustment((away_form["form_score"] - 0.5) * 0.3)

        home_motivation_adjustment = self._clamp_adjustment(
            (home_motivation["trend_score"] - 0.5) * 0.2
        )
        away_motivation_adjustment = self._clamp_adjustment(
            (away_motivation["trend_score"] - 0.5) * 0.2
        )

        home_multiplier = 1.0 + home_form_adjustment + home_motivation_adjustment
        away_multiplier = 1.0 + away_form_adjustment + away_motivation_adjustment

        logger.info(
            "Contexto calculado | home_mult={:.3f} away_mult={:.3f} | referee_disponible={}",
            home_multiplier, away_multiplier, referee_profile.get("available", False),
        )

        return {
            "home_attack_multiplier": round(home_multiplier, 4),
            "away_attack_multiplier": round(away_multiplier, 4),
            "home_form": home_form,
            "away_form": away_form,
            "head_to_head": h2h,
            "referee_profile": referee_profile,
            "home_motivation": home_motivation,
            "away_motivation": away_motivation,
        }