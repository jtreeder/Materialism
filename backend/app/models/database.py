"""Database setup and SQLAlchemy models for chemical HSP data."""

from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Chemical(Base):
    """A chemical substance with Hansen Solubility Parameters."""

    __tablename__ = "chemicals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False, index=True)
    cas_number = Column(String(20), index=True)
    smiles = Column(String(500))
    molecular_formula = Column(String(100))
    molecular_weight = Column(Float)
    density = Column(Float)
    boiling_point = Column(Float)  # °C
    molar_volume = Column(Float)  # cm³/mol

    # Hansen Solubility Parameters (MPa½)
    delta_d = Column(Float)  # Dispersion
    delta_p = Column(Float)  # Polar
    delta_h = Column(Float)  # Hydrogen bonding

    # Metadata
    data_source = Column(String(100))  # measured, estimated, user, literature
    category = Column(String(100))  # solvent, polymer, plasticizer, etc.
    subcategory = Column(String(100))
    notes = Column(Text)

    # Safety / regulatory
    ghs_hazard = Column(String(200))

    def __repr__(self):
        return (
            f"<Chemical(name='{self.name}', "
            f"δD={self.delta_d}, δP={self.delta_p}, δH={self.delta_h})>"
        )

    @property
    def hsp(self):
        """Return HSP as a tuple (δD, δP, δH)."""
        return (self.delta_d, self.delta_p, self.delta_h)

    @property
    def has_hsp(self):
        return (
            self.delta_d is not None
            and self.delta_p is not None
            and self.delta_h is not None
        )


class Polymer(Base):
    """A polymer or material with HSP and solubility sphere radius."""

    __tablename__ = "polymers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False, index=True)
    trade_name = Column(String(500))
    type = Column(String(100))  # thermoplastic, thermoset, elastomer, etc.

    delta_d = Column(Float)
    delta_p = Column(Float)
    delta_h = Column(Float)
    radius = Column(Float)  # Solubility sphere radius R₀

    data_source = Column(String(100))
    notes = Column(Text)

    solubility_tests = relationship("SolubilityTest", back_populates="polymer")

    def __repr__(self):
        return (
            f"<Polymer(name='{self.name}', "
            f"δD={self.delta_d}, δP={self.delta_p}, δH={self.delta_h}, R₀={self.radius})>"
        )

    @property
    def hsp(self):
        return (self.delta_d, self.delta_p, self.delta_h)


class SolubilityTest(Base):
    """An experimental test of solvent-material compatibility."""

    __tablename__ = "solubility_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chemical_id = Column(Integer, ForeignKey("chemicals.id"), nullable=False)
    polymer_id = Column(Integer, ForeignKey("polymers.id"), nullable=False)

    # Score: 1 = dissolved, 0 = did not dissolve
    # Or use 1-6 scale (1=fully dissolved ... 6=no effect)
    score = Column(Float, nullable=False)
    is_good = Column(Boolean)  # True = inside sphere, False = outside

    temperature = Column(Float)  # °C
    notes = Column(Text)

    chemical = relationship("Chemical")
    polymer = relationship("Polymer", back_populates="solubility_tests")


class Mixture(Base):
    """A mixture/blend of chemicals."""

    __tablename__ = "mixtures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)

    # Calculated HSP of the mixture
    delta_d = Column(Float)
    delta_p = Column(Float)
    delta_h = Column(Float)

    notes = Column(Text)

    components = relationship("MixtureComponent", back_populates="mixture")


class MixtureComponent(Base):
    """A component of a mixture with its volume fraction."""

    __tablename__ = "mixture_components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mixture_id = Column(Integer, ForeignKey("mixtures.id"), nullable=False)
    chemical_id = Column(Integer, ForeignKey("chemicals.id"), nullable=False)
    volume_fraction = Column(Float, nullable=False)

    mixture = relationship("Mixture", back_populates="components")
    chemical = relationship("Chemical")


# --- Database initialization ---

DB_PATH = "materialism.db"


def get_engine(db_path=None):
    path = db_path or DB_PATH
    return create_engine(f"sqlite:///{path}", echo=False)


def get_session(engine=None):
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db(engine=None):
    """Create all tables."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine
