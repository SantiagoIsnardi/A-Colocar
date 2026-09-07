"""
Declarative base de SQLAlchemy de la que heredan todos los modelos ORM.
Define una convención de nombres para constraints e índices, necesaria
para que Alembic genere migraciones consistentes y reproducibles.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos del dominio."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)