Lever 🎓

Lever is an AI-powered student performance prediction and intervention platform.

It uses academic data to predict student performance, identify academic risk, explain the factors behind predictions, and suggest targeted interventions.

Features

- 📊 Student performance prediction
- ⚠️ Low / Medium / High risk classification
- 🔍 SHAP-based prediction explanations
- 🎯 Targeted intervention recommendations
- 📚 Multiple academic snapshots per student
- 🔮 What-if performance simulation
- 👨‍🏫 Faculty dashboard
- 🎓 Student dashboard
- 🔐 Faculty and Student authentication

Tech Stack

- Frontend: React + Vite
- Backend: Python + Flask
- Database: SQLite
- ML: Random Forest Regressor
- Explainability: SHAP
- Dataset: UCI Student Performance Dataset

Model

The current model predicts G3 (final grade) using:

"G1" · "G2" · "Absences" · "Study Time" · "Previous Failures"

Current evaluation:

- MAE: 1.10
- RMSE: 1.75
- R²: 0.851

Architecture

React + Vite
     ↓
Flask API
     ↓
SQLite + ML Model
     ↓
Prediction → Risk → SHAP → Intervention

Run Locally

npm install
npm run dev

Start the Flask backend separately:

py -3 backend/app.py

Project Structure

Lever/
├── backend/
├── src/
├── index.html
├── package.json
├── vite.config.js
└── README.md

Status

🚧 Hackathon Prototype

Built to demonstrate explainable AI-driven student performance prediction and targeted academic intervention.
