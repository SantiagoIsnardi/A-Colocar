from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.logging import logger
from app.db.models.match import Match, MatchStatus
from app.db.models.statistic import Statistic
from app.db.repositories.match_repository import MatchRepository
from app.db.repositories.statistics_repository import StatisticsRepository
from app.db.repositories.team_repository import TeamRepository
from app.services.sports_api.client import APIFootballClient
from app.services.sports_api.mapper import APIFootballMapper


class IngestionService:

    def __init__(self, session: AsyncSession, client: APIFootballClient) -> None:
        self.session = session
        self.client = client
        self.team_repo = TeamRepository(session)
        self.match_repo = MatchRepository(session)
        self.stats_repo = StatisticsRepository(session)
        self.mapper = APIFootballMapper()

    async def _get_or_create_team(self, api_team_data: dict) -> object:
        external_id = str(api_team_data["id"])
        team = await self.team_repo.get_by_external_id(external_id, "api_football")
        if not team:
            team = self.mapper.team_from_api({"team": api_team_data})
            team = await self.team_repo.create(team)
            logger.info("Equipo creado: {} (id={})", team.name, team.id)
        return team

    async def ingest_team_fixtures(
        self,
        team_name: str,
        season: int,
        last_n: int = 20,
    ) -> dict:
        cache_key = f"search:{team_name.lower()}"
        result = cache.get(cache_key)
        if not result:
            result = await self.client.search_teams(team_name)
            cache.set(cache_key, result, ttl=3600)

        teams_data = result.get("response", [])
        if not teams_data:
            raise ValueError(f"Equipo no encontrado: {team_name!r}")

        api_team = teams_data[0]["team"]
        main_team = await self._get_or_create_team(api_team)

        fixtures_result = await self.client.get_fixtures_by_team(
            team_id=int(api_team["id"]),
            season=season,
            last=last_n,
        )

        fixtures = fixtures_result.get("response", [])
        created = 0
        skipped = 0

        for fixture in fixtures:
            ext_id = str(fixture["fixture"]["id"])
            existing = await self.match_repo.get_by_external_id(ext_id, "api_football")
            if existing:
                skipped += 1
                continue

            home_data = fixture["teams"]["home"]
            away_data = fixture["teams"]["away"]

            home_team = await self._get_or_create_team(home_data)
            away_team = await self._get_or_create_team(away_data)

            match = self.mapper.match_from_fixture(
                fixture=fixture,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
            )
            await self.match_repo.create(match)
            created += 1

        await self.session.commit()

        logger.info(
            "Ingesta completa | equipo={} | creados={} | omitidos={}",
            main_team.name, created, skipped,
        )

        return {
            "team": main_team.name,
            "team_id": main_team.id,
            "season": season,
            "fixtures_created": created,
            "fixtures_skipped": skipped,
        }

    async def ingest_upcoming_fixtures(self, team_name: str, next_n: int = 5) -> dict:
        """
        Ingiere próximos partidos programados (status=NS) para un equipo,
        necesarios para poder consultar cuotas pre-partido — las cuotas
        de partidos ya finalizados no tienen cobertura ni utilidad real.
        """
        cache_key = f"search:{team_name.lower()}"
        result = cache.get(cache_key)
        if not result:
            result = await self.client.search_teams(team_name)
            cache.set(cache_key, result, ttl=3600)

        teams_data = result.get("response", [])
        if not teams_data:
            raise ValueError(f"Equipo no encontrado: {team_name!r}")

        api_team = teams_data[0]["team"]
        main_team = await self._get_or_create_team(api_team)

        fixtures_result = await self.client.get_upcoming_fixtures(
            team_id=int(api_team["id"]),
            next_n=next_n,
        )

        fixtures = fixtures_result.get("response", [])
        created = 0
        skipped = 0
        match_ids: list[int] = []

        for fixture in fixtures:
            ext_id = str(fixture["fixture"]["id"])
            existing = await self.match_repo.get_by_external_id(ext_id, "api_football")
            if existing:
                skipped += 1
                match_ids.append(existing.id)
                continue

            home_data = fixture["teams"]["home"]
            away_data = fixture["teams"]["away"]

            home_team = await self._get_or_create_team(home_data)
            away_team = await self._get_or_create_team(away_data)

            match = self.mapper.match_from_fixture(
                fixture=fixture,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
            )
            match = await self.match_repo.create(match)
            match_ids.append(match.id)
            created += 1

        await self.session.commit()

        logger.info(
            "Ingesta de próximos partidos | equipo={} | creados={} | omitidos={}",
            main_team.name, created, skipped,
        )

        return {
            "team": main_team.name,
            "team_id": main_team.id,
            "fixtures_created": created,
            "fixtures_skipped": skipped,
            "match_ids": match_ids,
        }

    async def ingest_statistics_for_football_data_match(self, match_id: int) -> dict:
        """
        NO USAR EN PRODUCCIÓN — método experimental del Sprint 10, descartado
        tras validación real. Dos problemas confirmados:
        (1) el matcheo de equipos por nombre entre football_data y
            api_football no es confiable — "mejor esfuerzo" devuelve falsos
            negativos con frecuencia;
        (2) el costo en requests (2-3 por partido solo para el cruce) agota
            el rate limit de API-Football rápidamente sin garantía de éxito.

        Decisión de arquitectura: los mercados corners/yellow_cards/fouls/
        shots solo están disponibles de forma confiable para partidos
        ingeridos directamente vía API-Football (ver seed_statistics.py).
        Los partidos de football_data.org quedan limitados al mercado
        'goals', que no depende de la tabla Statistic.

        Se conserva el código por si en el futuro cambia el plan de
        API-Football o aparece un proveedor con IDs compartidos.
        """
        from datetime import timedelta

        from sqlalchemy import select

        from app.db.models.match import Match, MatchStatus
        from app.db.repositories.statistics_repository import StatisticsRepository
        from app.services.sports_api.team_matcher import TeamMatcher

        result = await self.session.execute(select(Match).where(Match.id == match_id))
        match = result.scalar_one_or_none()

        if not match or match.status != MatchStatus.finished:
            return {"error": f"Partido {match_id} no encontrado o no finalizado"}
        if match.source != "football_data":
            return {"error": f"Partido {match_id} no proviene de football_data — usar ingest_match_statistics"}

        home_team = await self.team_repo.get_by_id(match.home_team_id)
        away_team = await self.team_repo.get_by_id(match.away_team_id)
        if not home_team or not away_team:
            return {"error": "Equipos no encontrados"}

        matcher = TeamMatcher(self.client)
        af_home_id = await matcher.find_api_football_id(home_team.name)
        af_away_id = await matcher.find_api_football_id(away_team.name)

        if not af_home_id or not af_away_id:
            return {"error": "No se pudo mapear los equipos a API-Football"}

        season_year = int(match.season) if match.season.isdigit() else match.match_date.year
        fixtures_result = await self.client.get_fixtures_by_team(
            team_id=af_home_id, season=season_year, last=40
        )
        fixtures = fixtures_result.get("response", [])

        target_fixture = None
        for fixture in fixtures:
            fixture_date_raw = fixture["fixture"]["date"]
            fixture_date = __import__("datetime").datetime.fromisoformat(fixture_date_raw.replace("Z", "+00:00"))
            away_id_in_fixture = fixture["teams"]["away"]["id"]

            if away_id_in_fixture == af_away_id and abs((fixture_date - match.match_date).days) <= 2:
                target_fixture = fixture
                break

        if not target_fixture:
            return {"error": "No se encontró el fixture correspondiente en API-Football"}

        stats_repo = StatisticsRepository(self.session)
        existing = await stats_repo.get_by_match(match_id)
        if existing:
            return {"match_id": match_id, "statistics_created": 0, "reason": "Ya existen estadísticas para este partido"}

        stats_data = await self.client.get_fixture_statistics(target_fixture["fixture"]["id"])
        team_stats_list = stats_data.get("response", [])

        if not team_stats_list:
            return {"match_id": match_id, "statistics_created": 0, "reason": "API-Football sin estadísticas para este fixture"}

        created = 0
        for team_stats in team_stats_list:
            api_team_id = team_stats["team"]["id"]

            if api_team_id == af_home_id:
                is_home = True
                db_team_id = home_team.id
                goals = match.home_score or 0
                goals_conceded = match.away_score or 0
            elif api_team_id == af_away_id:
                is_home = False
                db_team_id = away_team.id
                goals = match.away_score or 0
                goals_conceded = match.home_score or 0
            else:
                continue

            stat = self.mapper.statistic_from_fixture_stats(
                team_stats=team_stats,
                match_id=match_id,
                team_id=db_team_id,
                is_home=is_home,
                goals=goals,
                goals_conceded=goals_conceded,
            )
            self.session.add(stat)
            created += 1

        await self.session.commit()
        return {"match_id": match_id, "statistics_created": created}
    
    from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.logging import logger
from app.db.models.match import Match, MatchStatus
from app.db.models.statistic import Statistic
from app.db.repositories.match_repository import MatchRepository
from app.db.repositories.statistics_repository import StatisticsRepository
from app.db.repositories.team_repository import TeamRepository
from app.services.sports_api.client import APIFootballClient
from app.services.sports_api.mapper import APIFootballMapper


class IngestionService:

    def __init__(self, session: AsyncSession, client: APIFootballClient) -> None:
        self.session = session
        self.client = client
        self.team_repo = TeamRepository(session)
        self.match_repo = MatchRepository(session)
        self.stats_repo = StatisticsRepository(session)
        self.mapper = APIFootballMapper()

    async def _get_or_create_team(self, api_team_data: dict) -> object:
        external_id = str(api_team_data["id"])
        team = await self.team_repo.get_by_external_id(external_id, "api_football")
        if not team:
            team = self.mapper.team_from_api({"team": api_team_data})
            team = await self.team_repo.create(team)
            logger.info("Equipo creado: {} (id={})", team.name, team.id)
        return team

    async def ingest_team_fixtures(
        self,
        team_name: str,
        season: int,
        last_n: int = 20,
    ) -> dict:
        cache_key = f"search:{team_name.lower()}"
        result = cache.get(cache_key)
        if not result:
            result = await self.client.search_teams(team_name)
            cache.set(cache_key, result, ttl=3600)

        teams_data = result.get("response", [])
        if not teams_data:
            raise ValueError(f"Equipo no encontrado: {team_name!r}")

        api_team = teams_data[0]["team"]
        main_team = await self._get_or_create_team(api_team)

        fixtures_result = await self.client.get_fixtures_by_team(
            team_id=int(api_team["id"]),
            season=season,
            last=last_n,
        )

        fixtures = fixtures_result.get("response", [])
        created = 0
        skipped = 0

        for fixture in fixtures:
            ext_id = str(fixture["fixture"]["id"])
            existing = await self.match_repo.get_by_external_id(ext_id, "api_football")
            if existing:
                skipped += 1
                continue

            home_data = fixture["teams"]["home"]
            away_data = fixture["teams"]["away"]

            home_team = await self._get_or_create_team(home_data)
            away_team = await self._get_or_create_team(away_data)

            match = self.mapper.match_from_fixture(
                fixture=fixture,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
            )
            await self.match_repo.create(match)
            created += 1

        await self.session.commit()

        logger.info(
            "Ingesta completa | equipo={} | creados={} | omitidos={}",
            main_team.name, created, skipped,
        )

        return {
            "team": main_team.name,
            "team_id": main_team.id,
            "season": season,
            "fixtures_created": created,
            "fixtures_skipped": skipped,
        }

    async def ingest_upcoming_fixtures(self, team_name: str, next_n: int = 5) -> dict:
        """
        Ingiere próximos partidos programados (status=NS) para un equipo,
        necesarios para poder consultar cuotas pre-partido — las cuotas
        de partidos ya finalizados no tienen cobertura ni utilidad real.
        """
        cache_key = f"search:{team_name.lower()}"
        result = cache.get(cache_key)
        if not result:
            result = await self.client.search_teams(team_name)
            cache.set(cache_key, result, ttl=3600)

        teams_data = result.get("response", [])
        if not teams_data:
            raise ValueError(f"Equipo no encontrado: {team_name!r}")

        api_team = teams_data[0]["team"]
        main_team = await self._get_or_create_team(api_team)

        fixtures_result = await self.client.get_upcoming_fixtures(
            team_id=int(api_team["id"]),
            next_n=next_n,
        )

        fixtures = fixtures_result.get("response", [])
        created = 0
        skipped = 0
        match_ids: list[int] = []

        for fixture in fixtures:
            ext_id = str(fixture["fixture"]["id"])
            existing = await self.match_repo.get_by_external_id(ext_id, "api_football")
            if existing:
                skipped += 1
                match_ids.append(existing.id)
                continue

            home_data = fixture["teams"]["home"]
            away_data = fixture["teams"]["away"]

            home_team = await self._get_or_create_team(home_data)
            away_team = await self._get_or_create_team(away_data)

            match = self.mapper.match_from_fixture(
                fixture=fixture,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
            )
            match = await self.match_repo.create(match)
            match_ids.append(match.id)
            created += 1

        await self.session.commit()

        logger.info(
            "Ingesta de próximos partidos | equipo={} | creados={} | omitidos={}",
            main_team.name, created, skipped,
        )

        return {
            "team": main_team.name,
            "team_id": main_team.id,
            "fixtures_created": created,
            "fixtures_skipped": skipped,
            "match_ids": match_ids,
        }

    async def ingest_statistics_for_football_data_match(self, match_id: int) -> dict:
        """
        NO USAR EN PRODUCCIÓN — método experimental del Sprint 10, descartado
        tras validación real. Dos problemas confirmados:
        (1) el matcheo de equipos por nombre entre football_data y
            api_football no es confiable — "mejor esfuerzo" devuelve falsos
            negativos con frecuencia;
        (2) el costo en requests (2-3 por partido solo para el cruce) agota
            el rate limit de API-Football rápidamente sin garantía de éxito.

        Decisión de arquitectura: los mercados corners/yellow_cards/fouls/
        shots solo están disponibles de forma confiable para partidos
        ingeridos directamente vía API-Football (ver seed_statistics.py).
        Los partidos de football_data.org quedan limitados al mercado
        'goals', que no depende de la tabla Statistic.

        Se conserva el código por si en el futuro cambia el plan de
        API-Football o aparece un proveedor con IDs compartidos.
        """
        from datetime import timedelta

        from sqlalchemy import select

        from app.db.models.match import Match, MatchStatus
        from app.db.repositories.statistics_repository import StatisticsRepository
        from app.services.sports_api.team_matcher import TeamMatcher

        result = await self.session.execute(select(Match).where(Match.id == match_id))
        match = result.scalar_one_or_none()

        if not match or match.status != MatchStatus.finished:
            return {"error": f"Partido {match_id} no encontrado o no finalizado"}
        if match.source != "football_data":
            return {"error": f"Partido {match_id} no proviene de football_data — usar ingest_match_statistics"}

        home_team = await self.team_repo.get_by_id(match.home_team_id)
        away_team = await self.team_repo.get_by_id(match.away_team_id)
        if not home_team or not away_team:
            return {"error": "Equipos no encontrados"}

        matcher = TeamMatcher(self.client)
        af_home_id = await matcher.find_api_football_id(home_team.name)
        af_away_id = await matcher.find_api_football_id(away_team.name)

        if not af_home_id or not af_away_id:
            return {"error": "No se pudo mapear los equipos a API-Football"}

        season_year = int(match.season) if match.season.isdigit() else match.match_date.year
        fixtures_result = await self.client.get_fixtures_by_team(
            team_id=af_home_id, season=season_year, last=40
        )
        fixtures = fixtures_result.get("response", [])

        target_fixture = None
        for fixture in fixtures:
            fixture_date_raw = fixture["fixture"]["date"]
            fixture_date = __import__("datetime").datetime.fromisoformat(fixture_date_raw.replace("Z", "+00:00"))
            away_id_in_fixture = fixture["teams"]["away"]["id"]

            if away_id_in_fixture == af_away_id and abs((fixture_date - match.match_date).days) <= 2:
                target_fixture = fixture
                break

        if not target_fixture:
            return {"error": "No se encontró el fixture correspondiente en API-Football"}

        stats_repo = StatisticsRepository(self.session)
        existing = await stats_repo.get_by_match(match_id)
        if existing:
            return {"match_id": match_id, "statistics_created": 0, "reason": "Ya existen estadísticas para este partido"}

        stats_data = await self.client.get_fixture_statistics(target_fixture["fixture"]["id"])
        team_stats_list = stats_data.get("response", [])

        if not team_stats_list:
            return {"match_id": match_id, "statistics_created": 0, "reason": "API-Football sin estadísticas para este fixture"}

        created = 0
        for team_stats in team_stats_list:
            api_team_id = team_stats["team"]["id"]

            if api_team_id == af_home_id:
                is_home = True
                db_team_id = home_team.id
                goals = match.home_score or 0
                goals_conceded = match.away_score or 0
            elif api_team_id == af_away_id:
                is_home = False
                db_team_id = away_team.id
                goals = match.away_score or 0
                goals_conceded = match.home_score or 0
            else:
                continue

            stat = self.mapper.statistic_from_fixture_stats(
                team_stats=team_stats,
                match_id=match_id,
                team_id=db_team_id,
                is_home=is_home,
                goals=goals,
                goals_conceded=goals_conceded,
            )
            self.session.add(stat)
            created += 1

        await self.session.commit()
        return {"match_id": match_id, "statistics_created": created}
    
    async def ingest_match_statistics(self, limit: int = 10, delay_seconds: float = 3.0) -> dict:
        import asyncio
        from sqlalchemy.exc import SQLAlchemyError
        from app.core.bad_fixtures import load_bad_fixtures, mark_bad_fixture

        RATE_LIMIT_COOLDOWN = 15.0
        bad_fixtures = load_bad_fixtures()

        matches_with_stats = await self.stats_repo.matches_with_statistics()
        result = await self.session.execute(
            select(Match)
            .where(
                Match.status == MatchStatus.finished,
                Match.source == "api_football",
            )
            .order_by(Match.match_date.desc())
            .limit(limit * 4)
        )

        all_matches = result.scalars().all()
        pending = [
            m for m in all_matches
            if m.id not in matches_with_stats and m.external_id not in bad_fixtures
        ][:limit]

        created = 0
        failed = 0
        rate_limited = 0
        marked_bad = 0
        db_errors = 0

        async def _try_ingest(match: Match) -> str:
            home_team = await self.team_repo.get_by_id(match.home_team_id)
            away_team = await self.team_repo.get_by_id(match.away_team_id)

            if not home_team or not away_team:
                logger.warning("Equipos no encontrados para match {}", match.id)
                return "sin_equipos"

            stats_data = await self.client.get_fixture_statistics(int(match.external_id))
            team_stats_list = stats_data.get("response", [])

            if not team_stats_list:
                logger.warning("Sin estadísticas disponibles para fixture {}", match.external_id)
                return "sin_datos"

            any_created = False
            for team_stats in team_stats_list:
                api_team_id = str(team_stats["team"]["id"])

                if api_team_id == home_team.external_id:
                    is_home, db_team_id = True, home_team.id
                    goals, goals_conceded = match.home_score or 0, match.away_score or 0
                elif api_team_id == away_team.external_id:
                    is_home, db_team_id = False, away_team.id
                    goals, goals_conceded = match.away_score or 0, match.home_score or 0
                else:
                    logger.warning(
                        "Equipo desconocido {} en fixture {} (esperados: home={} away={})",
                        api_team_id, match.external_id, home_team.external_id, away_team.external_id,
                    )
                    continue

                stat = self.mapper.statistic_from_fixture_stats(
                    team_stats=team_stats, match_id=match.id, team_id=db_team_id,
                    is_home=is_home, goals=goals, goals_conceded=goals_conceded,
                )
                self.session.add(stat)
                any_created = True

            return "ok" if any_created else "equipo_desconocido"

        for i, match in enumerate(pending):
            if i > 0:
                await asyncio.sleep(delay_seconds)

            try:
                outcome = await _try_ingest(match)
            except SQLAlchemyError as db_exc:
                # La sesión quedó en estado inválido (ej: conexión cortada por
                # timeout de red). Sin rollback, TODO intento posterior en esta
                # misma sesión fallaría en cadena con PendingRollbackError.
                logger.error(
                    "Error de base de datos en fixture {} — sesión revertida: {}",
                    match.external_id, db_exc,
                )
                try:
                    await self.session.rollback()
                except Exception as rb_exc:
                    logger.error("Fallo también el rollback: {}", rb_exc)
                db_errors += 1
                failed += 1
                continue
            except Exception as e:
                if "límite de requests" in str(e).lower():
                    logger.warning("Rate limit en fixture {} — cooldown {}s y reintento", match.external_id, RATE_LIMIT_COOLDOWN)
                    await asyncio.sleep(RATE_LIMIT_COOLDOWN)
                    try:
                        outcome = await _try_ingest(match)
                    except SQLAlchemyError as db_exc:
                        logger.error("Error de base de datos en reintento de {}: {}", match.external_id, db_exc)
                        try:
                            await self.session.rollback()
                        except Exception:
                            pass
                        db_errors += 1
                        failed += 1
                        continue
                    except Exception as retry_e:
                        logger.error("Fallo también en reintento de {}: {}", match.external_id, retry_e)
                        rate_limited += 1
                        failed += 1
                        continue
                else:
                    logger.error("Error en fixture {}: {}", match.external_id, e)
                    failed += 1
                    continue

            if outcome == "ok":
                created += 1
            elif outcome == "equipo_desconocido":
                mark_bad_fixture(match.external_id)
                marked_bad += 1
                failed += 1
                logger.warning("Fixture {} marcado como permanentemente inválido", match.external_id)
            else:
                failed += 1

        try:
            await self.session.commit()
        except SQLAlchemyError as final_exc:
            logger.error("Error al hacer commit final: {}", final_exc)
            await self.session.rollback()

        logger.info(
            "Estadísticas: creadas={} | fallidas={} | por_rate_limit={} | marcados_bad={} | errores_db={}",
            created, failed, rate_limited, marked_bad, db_errors,
        )
        return {
            "statistics_created": created,
            "matches_processed": len(pending),
            "matches_failed": failed,
            "matches_failed_by_rate_limit": rate_limited,
            "matches_marked_permanently_bad": marked_bad,
            "matches_failed_by_db_error": db_errors,
        }