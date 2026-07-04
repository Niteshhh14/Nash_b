import os
import json
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables on startup
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# Import emergency notification coordinator
from app.services.notifications.notification_service import send_emergency_notifications

# 1. DATABASE CONFIGURATION
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nash.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Handle SQLite connection check thread issue
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. DATABASE MODELS
class PatientDB(Base):
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    condition = Column(String)
    riskScore = Column(Float, default=0.0)
    riskCategory = Column(String, default="low")
    
    # Active vitals
    heartRate = Column(Integer)
    systolic = Column(Integer)
    diastolic = Column(Integer)
    oxygenSat = Column(Integer)
    respiratoryRate = Column(Integer)
    temperature = Column(Float)
    
    # Status
    emergencyStatus = Column(String, default="stable")
    summary = Column(Text)
    recommendations = Column(Text)
    
    notes = relationship("ClinicalNoteDB", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("MedicationDB", back_populates="patient", cascade="all, delete-orphan")

class ClinicalNoteDB(Base):
    __tablename__ = "clinical_notes"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(String, ForeignKey("patients.id"))
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat())
    provider = Column(String)
    noteText = Column(Text)
    
    patient = relationship("PatientDB", back_populates="notes")

class MedicationDB(Base):
    __tablename__ = "medications"
    
    id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"))
    name = Column(String)
    dosage = Column(String)
    schedule = Column(String)
    compliedToday = Column(Boolean, default=False)
    history_json = Column(Text, default="[]") # JSON string containing log entries
    
    patient = relationship("PatientDB", back_populates="medications")

class AlertDB(Base):
    __tablename__ = "alerts"
    
    id = Column(String, primary_key=True, index=True)
    patientName = Column(String)
    type = Column(String)
    value = Column(String)
    baseline = Column(String)
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat())
    severity = Column(String)
    status = Column(String, default="active")
    notes = Column(Text)

# Initialize tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. FASTAPI APP INIT & CORS
app = FastAPI(title="Nash OS API Server", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed database on startup if empty
def seed_data(db: Session):
    if db.query(PatientDB).count() > 0:
        return
        
    # Mock patients seed
    patients_data = [
        {
            "id": "PAT-001",
            "name": "Sarah Jenkins",
            "age": 72,
            "gender": "Female",
            "condition": "Congestive Heart Failure",
            "riskScore": 18.0,
            "riskCategory": "low",
            "heartRate": 72,
            "systolic": 120,
            "diastolic": 80,
            "oxygenSat": 98,
            "respiratoryRate": 16,
            "temperature": 98.6,
            "emergencyStatus": "stable",
            "summary": "Patient is responding well to guideline-directed medical therapy. BP is stable at home, heart rate remains controlled. Daily weights show no fluid retention.",
            "recommendations": "Continue current dose of Sacubitril/Valsartan. Keep monitoring daily weights before breakfast."
        },
        {
            "id": "PAT-002",
            "name": "Ramesh Kumar",
            "age": 68,
            "gender": "Male",
            "condition": "Hypertension & T2D",
            "riskScore": 24.0,
            "riskCategory": "low",
            "heartRate": 68,
            "systolic": 118,
            "diastolic": 76,
            "oxygenSat": 97,
            "respiratoryRate": 14,
            "temperature": 98.4,
            "emergencyStatus": "stable",
            "summary": "Hypertension remains fully controlled under home telemetry monitoring. Blood sugars show moderate compliance post-prandial.",
            "recommendations": "Check glucose levels post-breakfast. Continue walking 30 minutes daily."
        },
        {
            "id": "PAT-003",
            "name": "Arjun Patel",
            "age": 65,
            "gender": "Male",
            "condition": "COPD",
            "riskScore": 48.0,
            "riskCategory": "medium",
            "heartRate": 88,
            "systolic": 132,
            "diastolic": 86,
            "oxygenSat": 95,
            "respiratoryRate": 20,
            "temperature": 99.1,
            "emergencyStatus": "stable",
            "summary": "COPD symptom severity remains stable, though mild exertional desaturations are noted. Lung sounds are clear bilaterally.",
            "recommendations": "Keep rescue inhaler nearby. Report any increased sputum production immediately."
        },
        {
            "id": "PAT-004",
            "name": "Mei Ling",
            "age": 79,
            "gender": "Female",
            "condition": "Chronic Kidney Disease",
            "riskScore": 82.0,
            "riskCategory": "high",
            "heartRate": 104,
            "systolic": 142,
            "diastolic": 92,
            "oxygenSat": 91,
            "respiratoryRate": 24,
            "temperature": 100.2,
            "emergencyStatus": "critical",
            "summary": "Vitals indicate active tachycardia and moderate hypoxia at rest. Potential fluid overload secondary to renal insufficiency.",
            "recommendations": "Requires immediate clinician telemetry review. Dispatched ambulance warnings."
        }
    ]

    for p in patients_data:
        patient = PatientDB(**p)
        db.add(patient)
    
    # Mock alerts seed
    alerts_data = [
        {
            "id": "ALT-001",
            "patientName": "Mei Ling",
            "type": "Oxygen Saturation",
            "value": "91%",
            "baseline": "95%",
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "critical",
            "status": "active",
            "notes": "Patient reports shortness of breath. SpO2 telemetry dropped below 92% threshold."
        },
        {
            "id": "ALT-002",
            "patientName": "Arjun Patel",
            "type": "Heart Rate",
            "value": "104 bpm",
            "baseline": "72-88 bpm",
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "warning",
            "status": "active",
            "notes": "Elevated resting heart rate mapped. Sent medication reminders."
        }
    ]
    
    for a in alerts_data:
        alert = AlertDB(**a)
        db.add(alert)
        
    db.commit()

# Run seed
db = SessionLocal()
seed_data(db)
db.close()

# 4. SCHEMAS
class LoginRequest(BaseModel):
    email: str
    role: str

class UserResponse(BaseModel):
    email: str
    role: str
    token: str

class ClinicalNoteCreate(BaseModel):
    clinicalNote: str
    provider: str

class ComplianceToggleRequest(BaseModel):
    complied: bool

class PatientInput(BaseModel):
    patient_id: str
    name: str
    age: Optional[int] = 65
    conditions: Optional[List[str]] = []
    baseline_heart_rate: Optional[int] = 70
    baseline_systolic_bp: Optional[int] = 120
    baseline_spo2: Optional[int] = 98

class VitalsInput(BaseModel):
    heart_rate: int
    systolic_bp: int
    diastolic_bp: int
    temperature_c: Optional[float] = 36.6
    spo2: int
    sleep_hours: Optional[float] = 7.5
    medication_adherence: Optional[float] = 1.0
    activity_minutes: Optional[int] = 30
    stress_level: Optional[int] = 3

class RiskRequest(BaseModel):
    patient: PatientInput
    vitals: VitalsInput
    symptoms: Optional[List[str]] = []

class SimulateEmergencyRequest(BaseModel):
    patient: PatientInput
    vitals: VitalsInput
    symptoms: Optional[List[str]] = []
    emergency_type: str

class PredictionRequest(BaseModel):
    patient: PatientInput
    vitals: VitalsInput
    symptoms: Optional[List[str]] = []
    scenario: str

# 5. REST API ROUTES

@app.get("/")
def read_root():
    return {"status": "healthy", "service": "Nash OS Backend Service", "version": "2.0.0"}

# AUTH LOGIN
@app.post("/api/auth/login", response_model=UserResponse)
def login_user(req: LoginRequest):
    # Mock authentication validation
    token_str = f"mock-jwt-token-for-{req.role}"
    return UserResponse(email=req.email, role=req.role, token=token_str)

# GET ALL PATIENTS
@app.get("/api/patients")
def get_patients(query: Optional[str] = None, riskCategory: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(PatientDB)
    if riskCategory:
        q = q.filter(PatientDB.riskCategory == riskCategory)
    
    patients = q.all()
    
    if query:
        query_lc = query.lower()
        patients = [p for p in patients if query_lc in p.name.lower() or query_lc in p.condition.lower()]
        
    return patients

# GET PATIENT BY ID
@app.get("/api/patients/{id}")
def get_patient_by_id(id: str, db: Session = Depends(get_db)):
    patient = db.query(PatientDB).filter(PatientDB.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    # Serialize relationships dynamically
    notes = db.query(ClinicalNoteDB).filter(ClinicalNoteDB.patient_id == id).order_by(ClinicalNoteDB.id.desc()).all()
    meds = db.query(MedicationDB).filter(MedicationDB.patient_id == id).all()
    
    # Format meds logs
    formatted_meds = []
    for m in meds:
        formatted_meds.append({
            "id": m.id,
            "name": m.name,
            "dosage": m.dosage,
            "schedule": m.schedule,
            "compliedToday": m.compliedToday,
            "history": json.loads(m.history_json)
        })
        
    return {
        "id": patient.id,
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "condition": patient.condition,
        "riskScore": patient.riskScore,
        "riskCategory": patient.riskCategory,
        "heartRate": patient.heartRate,
        "systolic": patient.systolic,
        "diastolic": patient.diastolic,
        "oxygenSat": patient.oxygenSat,
        "respiratoryRate": patient.respiratoryRate,
        "temperature": patient.temperature,
        "emergencyStatus": patient.emergencyStatus,
        "summary": patient.summary,
        "recommendations": patient.recommendations,
        "notes": notes,
        "medications": formatted_meds
    }

# ADD CLINICAL NOTE
@app.post("/api/patients/{id}/notes")
def add_note(id: str, note: ClinicalNoteCreate, db: Session = Depends(get_db)):
    patient = db.query(PatientDB).filter(PatientDB.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    new_note = ClinicalNoteDB(
        patient_id=id,
        provider=note.provider,
        noteText=note.clinicalNote,
        timestamp=datetime.utcnow().isoformat()
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

# TOGGLE MEDICATION COMPLIANCE
@app.post("/api/patients/{id}/medications/{med_id}/compliance")
def toggle_compliance(id: str, med_id: str, req: ComplianceToggleRequest, db: Session = Depends(get_db)):
    # Check patient
    patient = db.query(PatientDB).filter(PatientDB.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    # Get or create medication entry
    med = db.query(MedicationDB).filter(MedicationDB.patient_id == id, MedicationDB.id == med_id).first()
    if not med:
        # Default create
        name_map = {"med-1": "Carvedilol", "med-2": "Lisinopril", "med-3": "Spironolactone"}
        med = MedicationDB(
            id=med_id,
            patient_id=id,
            name=name_map.get(med_id, "Cardiovascular pill"),
            dosage="12.5mg" if med_id == "med-1" else "10mg",
            schedule="Twice daily" if med_id == "med-1" else "Once daily",
            compliedToday=req.complied,
            history_json="[]"
        )
        db.add(med)
        db.commit()
        db.refresh(med)
        
    med.compliedToday = req.complied
    
    # Append to logs history
    history = json.loads(med.history_json)
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Remove existing logs for today if exists
    history = [h for h in history if h.get("date") != today_str]
    history.append({"date": today_str, "complied": req.complied})
    med.history_json = json.dumps(history)
    
    db.commit()
    return {"status": "success", "complied": req.complied}

# GET ACTIVE ALERTS
@app.get("/api/alerts")
def get_alerts(db: Session = Depends(get_db)):
    return db.query(AlertDB).order_by(AlertDB.timestamp.desc()).all()

# UPDATE ALERT STATUS (RESOLVE ALERTS)
@app.put("/api/alerts/{alert_id}")
def update_alert(alert_id: str, body: dict, db: Session = Depends(get_db)):
    alert = db.query(AlertDB).filter(AlertDB.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if "status" in body:
        alert.status = body["status"]
    if "notes" in body:
        alert.notes = body["notes"]
        
    db.commit()
    db.refresh(alert)
    return alert

# GET REPORTS DATA
@app.get("/api/reports")
def get_reports():
    # Return structured reports aggregation logs
    return {
        "readmissionRate": 4.8,
        "activePatientsCount": 142,
        "criticalTriageCount": 2,
        "monthlyTrend": [
            {"month": "Jan", "admissions": 12},
            {"month": "Feb", "admissions": 10},
            {"month": "Mar", "admissions": 8},
            {"month": "Apr", "admissions": 5},
            {"month": "May", "admissions": 4}
        ]
    }

# --- AI COMPATIBILITY & TWILIO NOTIFICATION ROUTES ---

@app.post("/risk")
def calculate_risk(req: RiskRequest):
    # Calculate dynamic risk score based on vitals parameters
    score = 15.0
    reasons = []
    
    # Heart rate rules
    hr = req.vitals.heart_rate
    if hr > 110 or hr < 50:
        score += 25.0
        reasons.append("Heart rate variance (tachycardia/bradycardia)")
    elif hr > 95 or hr < 60:
        score += 10.0
        reasons.append("Mild elevated/depressed heart rate")
        
    # SpO2 rules
    spo2 = req.vitals.spo2
    if spo2 < 90:
        score += 45.0
        reasons.append("Severe hypoxia (SpO2 < 90%)")
    elif spo2 < 94:
        score += 20.0
        reasons.append("Mild oxygen desaturation")
        
    # Blood pressure rules
    systolic = req.vitals.systolic_bp
    if systolic > 160:
        score += 25.0
        reasons.append("Severe hypertensive crisis")
    elif systolic > 140:
        score += 12.0
        reasons.append("Stage 2 hypertension")

    # Bound risk score
    score = min(100.0, max(5.0, score))
    if not reasons:
        reasons = ["All tracked vitals within normal clinical limits"]

    # Trigger Condition 1: Risk Score >= 90
    if score >= 90.0:
        send_emergency_notifications(
            patient_name=req.patient.name,
            score=score,
            risk="critical",
            reason=f"Risk score evaluated at {score}%: " + ", ".join(reasons),
            heart_rate=hr,
            spo2=spo2,
            bp=f"{systolic}/{req.vitals.diastolic_bp}"
        )

    return {"score": score, "reasons": reasons}

@app.post("/simulate-emergency")
def simulate_emergency(req: SimulateEmergencyRequest):
    # Trigger Condition 2: Emergency Simulation starts
    emergency_desc = req.emergency_type.replace("_", " ").title()
    doctor_msg = f"Immediate code blue triggered. Patient is experiencing acute {emergency_desc}."
    
    # Always send emergency notifications
    send_emergency_notifications(
        patient_name=req.patient.name,
        score=95.0,
        risk="critical",
        reason=f"Emergency Simulation Triggered: {emergency_desc}",
        heart_rate=req.vitals.heart_rate,
        spo2=req.vitals.spo2,
        bp=f"{req.vitals.systolic_bp}/{req.vitals.diastolic_bp}"
    )

    return {
        "risk": {
            "score": 95.0,
            "risk_level": "critical"
        },
        "doctor_notification": doctor_msg,
        "timeline": [
            { "title": "Triage Alert", "description": f"Triage category set to critical. Patient experiencing active {emergency_desc}." },
            { "title": "Bedside Code", "description": f"Ward response team dispatched to patient." }
        ]
    }

@app.post("/prediction")
def get_prediction(req: PredictionRequest):
    # Trigger Condition 3: Cardiac Arrest scenario selected
    # Checked via scenario name
    is_cardiac = req.scenario in ["cardiac", "cardiac_arrest", "medication_skipped"]
    score = 88.0 if req.scenario == "medication_skipped" else 95.0 if is_cardiac else 22.0
    
    if is_cardiac:
        send_emergency_notifications(
            patient_name=req.patient.name,
            score=score,
            risk="critical",
            reason="Cardiac Arrest Scenario Selected / Medication Skipped Risk Surge",
            heart_rate=req.vitals.heart_rate,
            spo2=req.vitals.spo2,
            bp=f"{req.vitals.systolic_bp}/{req.vitals.diastolic_bp}"
        )

    return {
        "series": [
            { "day": "Today", "score": score, "drivers": ["Missed medications", "Stress factors"] }
        ]
    }

@app.post("/recommendations")
def get_recommendations(req: RiskRequest):
    return {
        "recommendations": [
            { "action": "Ensure daily compliance tracking is synced." },
            { "action": "Assess cardiorenal balance at bedside." }
        ],
        "confidence": "high"
    }

@app.post("/summary")
def get_summary(req: dict):
    return {
        "soap": {
            "subjective": "Patient sync completes normally.",
            "assessment": "No new acute changes flagged on stable baseline.",
            "plan": ["Continue telemetry monitoring daily."]
        },
        "generated_by": "Local Sandbox LLM (v2.0)"
    }

@app.post("/digital-twin")
def get_digital_twin(req: RiskRequest):
    score = req.vitals.heart_rate
    status = "critical" if score > 110 else "normal"
    return {
        "heart": status,
        "lungs": "normal",
        "kidneys": "normal",
        "brain": "normal",
        "liver": "normal",
        "reasons": {
            "heart": [f"Heart rate measured at {score} bpm"]
        }
    }

# Trigger Condition 4: Doctor manually presses "Trigger Emergency"
@app.post("/api/patients/{id}/trigger-emergency")
def trigger_manual_emergency(id: str, db: Session = Depends(get_db)):
    patient = db.query(PatientDB).filter(PatientDB.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    res = send_emergency_notifications(
        patient_name=patient.name,
        score=patient.riskScore or 90.0,
        risk=patient.riskCategory or "critical",
        reason="Manual Doctor Override: Emergency Trigger Action Clicked",
        heart_rate=patient.heartRate or 72,
        spo2=patient.oxygenSat or 98,
        bp=f"{patient.systolic or 120}/{patient.diastolic or 80}"
    )
    return res

# Bonus Endpoint: Test notifications directly
@app.post("/notifications/test")
def test_notifications():
    res = send_emergency_notifications(
        patient_name="Ramesh Kumar (Demo)",
        score=92.0,
        risk="critical",
        reason="Demo Testing Alert Protocol",
        heart_rate=105,
        spo2=89,
        bp="165/95"
    )
    return res
