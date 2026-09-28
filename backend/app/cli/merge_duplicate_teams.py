"""
Uso:
    python -m app.cli.merge_duplicate_teams

Fusiona pares de equipos duplicados (curados a mano tras revisar la
base). Por cada par, reasigna matches/statistic al id que se conserva
y borra la fila duplicada.
"""

import asyncio

from sqlalchemy import update

from app.db.session import AsyncSessionLocal
from app.db.models.match import Match
from app.db.models.statistic import Statistic
from app.db.models.team import Team

# (id_que_se_conserva, id_que_se_borra)
DUPLICATES = [
    (75, 2), (74, 13), (67, 19), (69, 17), (70, 14), (59, 12), (72, 3),
    (62, 8), (76, 10), (60, 5), (58, 9), (61, 210), (109, 25), (46, 22),
    (37, 139), (144, 198), (27, 226), (116, 229), (115, 231), (85, 211),
    (81, 192), (84, 183), (78, 188), (77, 184), (93, 194), (94, 185),
    (96, 191), (104, 236), (97, 233), (56, 180), (92, 138), (4, 71),
    (28, 99),
]


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for keep_id, remove_id in DUPLICATES:
            await session.execute(
                update(Match).where(Match.home_team_id == remove_id).values(home_team_id=keep_id)
            )
            await session.execute(
                update(Match).where(Match.away_team_id == remove_id).values(away_team_id=keep_id)
            )
            await session.execute(
                update(Statistic).where(Statistic.team_id == remove_id).values(team_id=keep_id)
            )
            team = await session.get(Team, remove_id)
            if team:
                await session.delete(team)
            print(f"Fusionado: {remove_id} -> {keep_id}")

        await session.commit()
    print("Listo.")


if __name__ == "__main__":
    asyncio.run(main())