"""
Trackea el movimiento de una línea de mercado entre snapshots capturados
en distintos momentos. Un movimiento significativo hacia un lado suele
indicar dinero "sharp" moviendo el mercado — señal que ninguna estadística
histórica puede replicar por sí sola.
"""

from app.db.models.odds import Odds


class LineMovementTracker:

    @staticmethod
    def calculate_movement(history: list[Odds]) -> dict:
        """
        history debe venir ordenado cronológicamente (más antiguo primero).
        Devuelve el movimiento entre la primera y la última cuota observada.
        """
        if len(history) < 2:
            return {
                "sufficient_data": False,
                "snapshots_count": len(history),
            }

        first = history[0]
        last = history[-1]

        first_price = float(first.price)
        last_price = float(last.price)

        price_change = last_price - first_price
        price_change_pct = (price_change / first_price) * 100 if first_price else 0.0

        # Cuota que baja = probabilidad implícita sube = mercado "carga" ese lado
        direction = "shortening" if price_change < 0 else "drifting" if price_change > 0 else "stable"

        return {
            "sufficient_data": True,
            "snapshots_count": len(history),
            "first_price": first_price,
            "last_price": last_price,
            "price_change": round(price_change, 3),
            "price_change_percentage": round(price_change_pct, 2),
            "direction": direction,
            "first_captured_at": first.captured_at.isoformat(),
            "last_captured_at": last.captured_at.isoformat(),
        }