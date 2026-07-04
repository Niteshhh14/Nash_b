import os
import json
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

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
