import joblib
import pandas as pd
from sqlalchemy import func
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal
from database import engine

from models import Base
from models import Prediction

# =====================================================

# CREATE DATABASE TABLES

# =====================================================

Base.metadata.create_all(bind=engine)

# =====================================================

# FASTAPI APP

# =====================================================

app = FastAPI(
    title="Airline Delay Intelligence System",
    description="Predict flight delays and delay duration",
    version="1.0"
)
import os

origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================

# LOAD MODELS

# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLASSIFIER_PATH = os.getenv("CLASSIFIER_MODEL_PATH", os.path.join(BASE_DIR, "..", "models", "delay_classifier.pkl"))
REGRESSOR_PATH = os.getenv("REGRESSOR_MODEL_PATH", os.path.join(BASE_DIR, "..", "models", "delay_regressor.pkl"))

classifier = joblib.load(CLASSIFIER_PATH)
regressor = joblib.load(REGRESSOR_PATH)

# =====================================================

# HOME ENDPOINT

# =====================================================

@app.get("/")
def home():
    return {
        "message": "Airline Delay Intelligence API Running"
    }

# =====================================================

# HEALTH CHECK

# =====================================================

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

# =====================================================

# INPUT SCHEMA

# =====================================================

class FlightInput(BaseModel):
    Airline: str
    Origin_Airport: str
    Destination_Airport: str
    Month: int
    Day_of_Week: int
    Scheduled_Departure_Hour: int
    Scheduled_Departure_Minute: int
    Distance_KM: float
    Scheduled_Air_Time_Mins: float
    Weather_Condition: str

# =====================================================

# PREDICTION ENDPOINT

# =====================================================

@app.post("/predict")
def predict(flight: FlightInput):
    db = SessionLocal()

    try:
        data = pd.DataFrame(
            [flight.dict()]
        )

        delay_status = classifier.predict(
            data
        )[0]

        delay_probability = classifier.predict_proba(
            data
        )[0][1]

        probability_percent = round(
            delay_probability * 100,
            2
        )

        # -----------------------------------------
        # ON TIME
        # -----------------------------------------

        if delay_status == 0:
            prediction = Prediction(
                airline=flight.Airline,
                source=flight.Origin_Airport,
                destination=flight.Destination_Airport,
                status="On Time",
                probability=probability_percent,
                predicted_delay_minutes=0
            )

            db.add(prediction)
            db.commit()

            return {
                "status": "On Time",
                "delay_probability_percent":
                    probability_percent,
                "predicted_delay_minutes":
                    0
            }

        # -----------------------------------------
        # DELAYED
        # -----------------------------------------

        delay_minutes = int(
            regressor.predict(data)[0]
        )

        prediction = Prediction(
            airline=flight.Airline,
            source=flight.Origin_Airport,
            destination=flight.Destination_Airport,
            status="Delayed",
            probability=probability_percent,
            predicted_delay_minutes=delay_minutes
        )

        db.add(prediction)
        db.commit()

        return {
            "status": "Delayed",
            "delay_probability_percent":
                probability_percent,
            "predicted_delay_minutes":
                delay_minutes
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()

# =====================================================

# ANALYTICS ENDPOINT

# =====================================================

@app.get("/stats/total")
def total_predictions():
    db = SessionLocal()

    total = db.query(
        Prediction
    ).count()

    db.close()

    return {
        "total_predictions": total
    }
@app.get("/stats/average-delay")
def average_delay():

    db = SessionLocal()

    try:

        avg_delay = db.query(
            func.avg(
                Prediction.predicted_delay_minutes
            )
        ).scalar()

        if avg_delay is None:

            avg_delay = 0

        return {
            "average_delay": round(
                avg_delay,
                2
            )
        }

    finally:

        db.close()

@app.get("/stats/top-airline")
def top_airline():

    db = SessionLocal()

    try:

        result = (
            db.query(
                Prediction.airline,
                func.count(Prediction.id)
            )
            .group_by(
                Prediction.airline
            )
            .order_by(
                func.count(
                    Prediction.id
                ).desc()
            )
            .first()
        )

        if result is None:

            return {
                "airline": None,
                "count": 0
            }

        return {
            "airline": result[0],
            "count": result[1]
        }

    finally:

        db.close()

@app.get("/predictions")
def get_predictions():

    db = SessionLocal()

    try:

        rows = db.query(
            Prediction
        ).all()

        result = []

        for row in rows:

            result.append({

                "id":
                    row.id,

                "airline":
                    row.airline,

                "source":
                    row.source,

                "destination":
                    row.destination,

                "status":
                    row.status,

                "probability":
                    row.probability,

                "delay_minutes":
                    row.predicted_delay_minutes
            })

        return result

    finally:

        db.close()