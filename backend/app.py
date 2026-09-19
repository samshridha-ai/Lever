import json
import sqlite3
from functools import wraps
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from config import SECRET_KEY
from database import connect, init_db
from services.ml_service import predict, risk_for, explain, feature_json, load_model, has_model_inputs, model_input_status
from services.intervention_service import recommendations

app = Flask(__name__); app.config.update(SECRET_KEY=SECRET_KEY, SESSION_COOKIE_SAMESITE='Lax')
CORS(app, supports_credentials=True, origins=['http://localhost:5173','http://127.0.0.1:5173'])
init_db()
def error(message, code=400): return jsonify(error=message), code
def current():
    uid=session.get('user_id')
    if not uid:return None
    with connect() as db:return db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
def auth(role=None):
 def deco(fn):
  @wraps(fn)
  def wrapped(*args,**kwargs):
   user=current()
   if not user:return error('Authentication required.',401)
   if role and user['role']!=role:return error('Permission denied.',403)
   return fn(user,*args,**kwargs)
  return wrapped
 return deco
def student_for(user, identifier):
 with connect() as db:
  if str(identifier)=='me': s=db.execute('SELECT s.*,u.name,u.email FROM students s JOIN users u ON u.id=s.user_id WHERE s.user_id=?',(user['id'],)).fetchone()
  else: s=db.execute('SELECT s.*,u.name,u.email FROM students s JOIN users u ON u.id=s.user_id WHERE s.id=? OR s.student_id=?',(identifier,str(identifier))).fetchone()
 if not s:return None
 if user['role']=='student' and s['user_id']!=user['id']:return None
 return s
def serialize(s):
 d=dict(s); d.update(feature_json(d.pop('features_json'))); return d
def latest_prediction(student_id):
 with connect() as db:
  snapshot=db.execute('SELECT id FROM academic_snapshots WHERE student_id=? ORDER BY id DESC LIMIT 1',(student_id,)).fetchone()
  if snapshot:
   linked=db.execute('SELECT predicted_score,risk_level,created_at,snapshot_id FROM predictions WHERE snapshot_id=? ORDER BY id DESC LIMIT 1',(snapshot['id'],)).fetchone()
   if linked:return linked
  return db.execute('SELECT predicted_score,risk_level,created_at FROM predictions WHERE student_id=? ORDER BY id DESC LIMIT 1',(student_id,)).fetchone()
def latest_snapshot(student_id):
 with connect() as db:
  return db.execute('SELECT * FROM academic_snapshots WHERE student_id=? ORDER BY id DESC LIMIT 1',(student_id,)).fetchone()
def snapshot_features(snapshot):
 return {key:snapshot[key] for key in ('absences','studytime','failures','G1','G2')}
def validate_snapshot(payload):
 raw={key:payload.get(key, payload.get(f'feature_{key}')) for key in ('G1','G2','absences','studytime','failures')}
 if any(raw[key] in (None,'') for key in raw):raise ValueError('G1, G2, absences, study time, and failures are required for an academic snapshot.')
 values={key:float(value) for key,value in raw.items()}
 if not 0<=values['G1']<=20 or not 0<=values['G2']<=20:raise ValueError('G1 and G2 must be between 0 and 20.')
 if values['absences']<0 or values['failures']<0:raise ValueError('Absences and failures cannot be negative.')
 if values['studytime'] not in (1,2,3,4):raise ValueError('Study time must be a whole number from 1 to 4.')
 return values
def store_prediction(student_id, features, snapshot_id=None):
 """Persist a prediction only from actual supplied student inputs."""
 score,_=predict(features); level=risk_for(score)
 with connect() as db: db.execute('INSERT INTO predictions(student_id,predicted_score,risk_level,snapshot_id) VALUES(?,?,?,?)',(student_id,score,level,snapshot_id))
 return score,level
def submitted_features(payload):
 """Accept only real fields from the saved training schema; ignore UI/profile fields."""
 _, metadata = load_model()
 nested = payload.get('features') if isinstance(payload.get('features'), dict) else {}
 output = {}
 for feature in metadata['features']:
  value = nested.get(feature, payload.get(f'feature_{feature}'))
  if value in (None, ''): continue
  output[feature] = float(value) if feature in metadata['numeric_features'] else value
 return output
@app.post('/api/auth/login')
def login():
 data=request.get_json(silent=True) or {}; email=data.get('email','').strip().lower(); password=data.get('password','')
 with connect() as db:user=db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
 if not user or not check_password_hash(user['password_hash'],password):return error('Invalid email or password.',401)
 session.clear();session['user_id']=user['id']; return jsonify(user={'id':user['id'],'name':user['name'],'email':user['email'],'role':user['role']})
@app.get('/api/auth/me')
@auth()
def me(user):
 d=dict(user);d.pop('password_hash');
 if user['role']=='student':
  with connect() as db:s=db.execute('SELECT * FROM students WHERE user_id=?',(user['id'],)).fetchone()
  if s:
   profile=serialize(s); profile['student_db_id']=profile.pop('id'); profile.pop('user_id',None); d.update(profile)
 return jsonify(user=d)
@app.post('/api/auth/logout')
def logout():session.clear();return jsonify(message='Logged out')
@app.get('/api/students')
@auth('faculty')
def students(user):
 with connect() as db:rows=db.execute('SELECT s.*,u.name,u.email,p.predicted_score,p.risk_level FROM students s JOIN users u ON u.id=s.user_id LEFT JOIN predictions p ON p.id=(SELECT id FROM predictions WHERE student_id=s.id ORDER BY id DESC LIMIT 1)').fetchall()
 return jsonify(students=[serialize(r) for r in rows])
@app.post('/api/students')
@auth('faculty')
def create_student(user):
 d=request.get_json() or {}; required=['name','email','student_id','password']
 if any(not d.get(k) for k in required):return error('Name, email, student ID, and initial password are required.')
 try:
  features=submitted_features(d)
  has_snapshot_values=any(d.get(f'feature_{key}') not in (None,'') for key in ('G1','G2','absences','studytime','failures'))
  snapshot_values=validate_snapshot(d) if has_snapshot_values else None
  with connect() as db:
   cur=db.execute('INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)',(d['name'],d['email'].lower(),generate_password_hash(d['password']),'student'))
   student_id=db.execute('INSERT INTO students(user_id,student_id,department,year,section,features_json) VALUES(?,?,?,?,?,?)',(cur.lastrowid,d['student_id'],d.get('department'),d.get('year'),d.get('section'),json.dumps(features))).lastrowid
   snapshot_id=db.execute('INSERT INTO academic_snapshots(student_id,G1,G2,absences,studytime,failures) VALUES(?,?,?,?,?,?)',(student_id,snapshot_values['G1'],snapshot_values['G2'],snapshot_values['absences'],snapshot_values['studytime'],snapshot_values['failures'])).lastrowid if snapshot_values else None
 except sqlite3.IntegrityError:return error('Email or student ID already exists.',409)
 except ValueError:return error('Academic numeric fields must contain valid numbers.',422)
 try:
  prediction=store_prediction(student_id,snapshot_values or features,snapshot_id) if (snapshot_values or has_model_inputs(features)) else None
 except RuntimeError as e:return error(str(e),503)
 except (TypeError, ValueError):return error('Invalid model input data.',422)
 with connect() as db:
  created=db.execute('SELECT s.*,u.name,u.email FROM students s JOIN users u ON u.id=s.user_id WHERE s.user_id=?',(cur.lastrowid,)).fetchone()
 return jsonify(message='Student created',student=serialize(created),prediction=(dict(predicted_score=prediction[0],risk_level=prediction[1]) if prediction else None)),201
@app.put('/api/students/<identifier>')
@auth('faculty')
def update_student(user,identifier):
 s=student_for(user,identifier)
 if not s:return error('Student not found.',404)
 d=request.get_json() or {}; features=feature_json(s['features_json'])
 try:
  supplied=submitted_features(d); features.update(supplied)
 except ValueError:return error('Academic numeric fields must contain valid numbers.',422)
 with connect() as db:
  db.execute('UPDATE users SET name=?,email=? WHERE id=?',(d.get('name',s['name']),d.get('email',s['email']).lower(),s['user_id']))
  db.execute('UPDATE students SET student_id=?,department=?,year=?,section=?,features_json=? WHERE id=?',(d.get('student_id',s['student_id']),d.get('department',s['department']),d.get('year',s['year']),d.get('section',s['section']),json.dumps(features),s['id']))
 try:
  prediction=store_prediction(s['id'],features) if supplied else None
 except RuntimeError as e:return error(str(e),503)
 except (TypeError, ValueError):return error('Invalid model input data.',422)
 return jsonify(message='Student updated',prediction=(dict(predicted_score=prediction[0],risk_level=prediction[1]) if prediction else None))
@app.get('/api/students/<identifier>')
@auth()
def get_student(user,identifier):
 s=student_for(user,identifier)
 return jsonify(serialize(s)) if s else error('Student not found.',404)
@app.get('/api/students/<identifier>/snapshots')
@auth()
def snapshots(user,identifier):
 s=student_for(user,identifier)
 if not s:return error('Student not found.',404)
 with connect() as db:
  rows=db.execute('SELECT a.*,p.predicted_score,p.risk_level,p.created_at prediction_created_at FROM academic_snapshots a LEFT JOIN predictions p ON p.id=(SELECT id FROM predictions WHERE snapshot_id=a.id ORDER BY id DESC LIMIT 1) WHERE a.student_id=? ORDER BY a.id DESC',(s['id'],)).fetchall()
 return jsonify(snapshots=[dict(row) for row in rows])
@app.post('/api/students/<identifier>/snapshots')
@auth('faculty')
def create_snapshot(user,identifier):
 s=student_for(user,identifier)
 if not s:return error('Student not found.',404)
 try: values=validate_snapshot(request.get_json() or {})
 except (TypeError,ValueError) as e:return error(str(e),422)
 with connect() as db:
  snapshot_id=db.execute('INSERT INTO academic_snapshots(student_id,G1,G2,absences,studytime,failures) VALUES(?,?,?,?,?,?)',(s['id'],values['G1'],values['G2'],values['absences'],values['studytime'],values['failures'])).lastrowid
 try: score,level=store_prediction(s['id'],values,snapshot_id)
 except RuntimeError as e:return error(str(e),503)
 except (TypeError,ValueError):return error('Invalid model input data.',422)
 return jsonify(snapshot=dict(id=snapshot_id,**values,predicted_score=score,risk_level=level),message='Academic snapshot created'),201
@app.get('/api/students/<identifier>/prediction')
@auth()
def get_prediction(user,identifier):
 s=student_for(user,identifier)
 if not s:return error('Student not found.',404)
 snapshot=latest_snapshot(s['id']); features=snapshot_features(snapshot) if snapshot else feature_json(s['features_json'])
 stored=latest_prediction(s['id'])
 if stored:return jsonify(predicted_score=stored['predicted_score'],risk_level=stored['risk_level'],risk=stored['risk_level'],prediction_source='stored',**model_input_status(features),**features)
 try:
  if not has_model_inputs(features): return jsonify(predicted_score=None,risk_level=None,risk=None,**model_input_status(features),**features)
  score,_=predict(features)
 except RuntimeError as e:return error(str(e),503)
 except (TypeError, ValueError):return error('Invalid model input data.',422)
 return jsonify(predicted_score=score,risk_level=risk_for(score),risk=risk_for(score),**model_input_status(features),**features)
@app.post('/api/predict')
@auth('faculty')
def create_prediction(user):
 d=request.get_json() or {}; s=student_for(user,d.get('student_id'))
 if not s:return error('Student not found.',404)
 features=feature_json(s['features_json']); supplied=submitted_features(d); features.update(supplied)
 try:
  if not has_model_inputs(features): return error('No model input data is available for this student.',422)
  score,_=predict(features); factors=explain(features)
 except RuntimeError as e:return error(str(e),503)
 except (TypeError, ValueError):return error('Invalid model input data.',422)
 with connect() as db:
  if supplied:db.execute('UPDATE students SET features_json=? WHERE id=?',(json.dumps(features),s['id']))
  db.execute('INSERT INTO predictions(student_id,predicted_score,risk_level) VALUES(?,?,?)',(s['id'],score,risk_for(score)))
 return jsonify(predicted_score=score,risk_level=risk_for(score),risk=risk_for(score),**model_input_status(features),recommendations=recommendations(features,score,factors))
@app.get('/api/students/<identifier>/risk')
@auth()
def risk(user,identifier):
 s=student_for(user,identifier)
 if not s:return error('Student not found.',404)
 snapshot=latest_snapshot(s['id']); features=snapshot_features(snapshot) if snapshot else feature_json(s['features_json'])
 stored=latest_prediction(s['id'])
 if stored:return jsonify(risk_level=stored['risk_level'],risk=stored['risk_level'],prediction_source='stored',**model_input_status(features))
 try:
  if not has_model_inputs(features): return jsonify(risk_level=None,risk=None,**model_input_status(features))
  score,_=predict(features)
 except RuntimeError as e:return error(str(e),503)
 except (TypeError, ValueError):return error('Invalid model input data.',422)
 return jsonify(risk_level=risk_for(score),risk=risk_for(score),**model_input_status(features))
@app.get('/api/students/<identifier>/explain')
@auth()
def explanation(user,identifier):
 s=student_for(user,identifier)
 if not s:return error('Student not found.',404)
 try:
  snapshot=latest_snapshot(s['id']); features=snapshot_features(snapshot) if snapshot else feature_json(s['features_json'])
  if not has_model_inputs(features): return jsonify(factors=[],**model_input_status(features))
  return jsonify(factors=explain(features),**model_input_status(features))
 except Exception:return error('Explanation is unavailable for this prediction.',503)
@app.get('/api/interventions')
@auth()
def interventions(user):
 with connect() as db:
  query='SELECT i.*,s.student_id,u.name student_name,p.risk_level risk FROM interventions i JOIN students s ON s.id=i.student_id JOIN users u ON u.id=s.user_id LEFT JOIN predictions p ON p.id=(SELECT id FROM predictions WHERE student_id=s.id ORDER BY id DESC LIMIT 1)'; args=()
  if user['role']=='student':query+=' WHERE s.user_id=?';args=(user['id'],)
  rows=db.execute(query,args).fetchall()
 return jsonify(items=[dict(r) for r in rows])
@app.get('/api/students/<identifier>/recommendations')
@auth()
def student_recommendations(user,identifier):
 s=student_for(user,identifier)
 if not s:return error('Student not found.',404)
 snapshot=latest_snapshot(s['id']); features=snapshot_features(snapshot) if snapshot else feature_json(s['features_json'])
 if not has_model_inputs(features):return jsonify(recommendations=[],**model_input_status(features))
 try:
  score,_=predict(features); factors=explain(features)
 except (RuntimeError, TypeError, ValueError):return error('Recommendations are unavailable for this prediction.',503)
 return jsonify(recommendations=recommendations(features,score,factors),**model_input_status(features))
@app.post('/api/interventions')
@auth('faculty')
def create_intervention(user):
 d=request.get_json() or {}; sid=d.get('student_id')
 if not sid or not d.get('recommended_action'):return error('Student ID and recommended action are required.')
 s=student_for(user,sid)
 if not s:return error('Student not found.',404)
 with connect() as db:
  cur=db.execute('INSERT INTO interventions(student_id,detected_factor,recommended_action,priority,notes,status) VALUES(?,?,?,?,?,?)',(s['id'],d.get('detected_factor') or d.get('factor'),d['recommended_action'],d.get('priority','Medium'),d.get('notes'),d.get('status','Planned')))
 return jsonify(id=cur.lastrowid,message='Intervention created'),201
@app.put('/api/interventions/<int:intervention_id>')
@auth('faculty')
def update_intervention(user,intervention_id):
 d=request.get_json() or {}
 with connect() as db:
  row=db.execute('SELECT id FROM interventions WHERE id=?',(intervention_id,)).fetchone()
  if not row:return error('Intervention not found.',404)
  db.execute('UPDATE interventions SET detected_factor=COALESCE(?,detected_factor),recommended_action=COALESCE(?,recommended_action),priority=COALESCE(?,priority),notes=COALESCE(?,notes),status=COALESCE(?,status) WHERE id=?',(d.get('detected_factor'),d.get('recommended_action'),d.get('priority'),d.get('notes'),d.get('status'),intervention_id))
 return jsonify(message='Intervention updated')
@app.post('/api/what-if')
@auth('student')
def what_if(user):
 d=request.get_json() or {}; s=student_for(user,'me')
 if not s:return error('Student profile not found.',404)
 snapshot=latest_snapshot(s['id'])
 original=snapshot_features(snapshot) if snapshot else feature_json(s['features_json'])
 changes=d.get('changes') or {k:v for k,v in d.items() if k!='student_id'}
 if not changes:return error('Provide at least one model-supported feature change.')
 try:
  _,meta=load_model()
  invalid=sorted(set(changes)-set(meta['features']))
  if invalid:return error('Unsupported model feature(s): '+', '.join(invalid)+'.')
  for feature in meta['numeric_features']:
   if feature in changes:
    try: changes[feature]=float(changes[feature])
    except (TypeError, ValueError): return error(f'Invalid numeric value for {feature}.',422)
  simulated=original.copy();simulated.update(changes)
  if not has_model_inputs(simulated):return error('Provide at least one supported model input for the simulation.',422)
  stored=latest_prediction(s['id'])
  baseline,_=predict(original) if has_model_inputs(original) else ((stored['predicted_score'] if stored else None), None)
  score,_=predict(simulated)
 except RuntimeError as e:return error(str(e),503)
 return jsonify(current_prediction=baseline,simulated_prediction=score,difference=(score-baseline if baseline is not None else None),changed_features=changes,**model_input_status(simulated),notice='Model-based simulation using the trained pipeline preprocessing; not a causal or guaranteed outcome.')
@app.get('/api/analytics/overview')
@auth('faculty')
def analytics(user):
 with connect() as db:
  total=db.execute('SELECT COUNT(*) total FROM students').fetchone()['total']
  rows=db.execute('SELECT predicted_score,risk_level FROM predictions WHERE id IN (SELECT MAX(id) FROM predictions GROUP BY student_id)').fetchall()
 scores=[row['predicted_score'] for row in rows]; risks=[row['risk_level'] for row in rows]
 return jsonify(total_students=total,average_predicted_score=(sum(scores)/len(scores) if scores else None),high_risk=risks.count('HIGH'),medium_risk=risks.count('MEDIUM'),low_risk=risks.count('LOW'))
if __name__=='__main__':app.run(debug=True,port=5000)
