from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Float

from database import Base


class Prediction(Base):

    __tablename__ = "predictions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    airline = Column(String)

    source = Column(String)

    destination = Column(String)

    status = Column(String)

    probability = Column(Float)

    predicted_delay_minutes = Column(Integer)