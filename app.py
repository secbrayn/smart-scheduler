from flask import Flask, jsonify, request, render_template
from supabase import create_client
import os
from dotenv import load_dotenv



# Load environment variables
load_dotenv()

app = Flask(__name__)

# Supabase Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ... andere imports ...

# DEBUG: Test Supabase Connection
try:
    test = supabase.table('employees').select('*').execute()
    print(f"✓ Supabase connected! Found {len(test.data)} employees")
except Exception as e:
    print(f"✗ Supabase ERROR: {e}")


# ============ ALGORITHMUS ============
def calculate_skill_match(employee_skills, project_needs):
    """
    Berechnet wie gut die Skills des Mitarbeiters zum Projekt passen
    Returns: Score 0-100
    """
    react_match = 100 - abs(employee_skills['react'] - project_needs['react']) * 10
    python_match = 100 - abs(employee_skills['python'] - project_needs['python']) * 10
    
    # Weighted average (React wichtiger für manche Projekte)
    if project_needs['react'] > project_needs['python']:
        score = (react_match * 0.7) + (python_match * 0.3)
    else:
        score = (python_match * 0.7) + (react_match * 0.3)
    
    return max(0, score)  # Never negative


def calculate_availability_score(employee_hours, project_hours):
    """
    Wie gut passt die Verfügbarkeit?
    Returns: Score 0-100
    """
    if employee_hours >= project_hours:
        return 100
    else:
        return (employee_hours / project_hours) * 100


def calculate_match_score(employee, project):
    """
    HAUPT-ALGORITHMUS: Berechnet Gesamt-Match-Score
    Returns: Score 0-100
    """
    # Skill Match (40% Gewichtung)
    skill_score = calculate_skill_match(
        {'react': employee['react_skill'], 'python': employee['python_skill']},
        {'react': project['react_needed'], 'python': project['python_needed']}
    )
    
    # Availability (30% Gewichtung)
    availability_score = calculate_availability_score(
        employee['hours_available'],
        project['hours_needed']
    )
    
    # Past Performance (30% Gewichtung) - Für Demo fixed auf 80
    performance_score = 80
    
    # Weighted Total
    total_score = (skill_score * 0.4) + (availability_score * 0.3) + (performance_score * 0.3)
    
    return round(total_score, 1)


# ============ API ENDPOINTS ============

@app.route('/')
def index():
    """Frontend anzeigen"""
    return render_template('index.html')


@app.route('/api/employees', methods=['GET'])
def get_employees():
    """Alle Mitarbeiter holen"""
    response = supabase.table('employees').select('*').execute()
    return jsonify(response.data)


@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Alle Projekte holen"""
    response = supabase.table('projects').select('*').execute()
    return jsonify(response.data)


@app.route('/api/calculate', methods=['POST'])
def calculate_matches():
    """
    HAUPT-ENDPOINT: Berechnet optimale Zuteilungen
    """
    try:
        # Daten holen
        employees = supabase.table('employees').select('*').execute().data
        projects = supabase.table('projects').select('*').execute().data
        
        results = []
        
        # Für jedes Projekt: Beste Matches finden
        for project in projects:
            project_matches = []
            
            for employee in employees:
                score = calculate_match_score(employee, project)
                
                project_matches.append({
                    'employee_name': employee['name'],
                    'employee_id': employee['id'],
                    'score': score,
                    'skill_details': {
                        'react': f"{employee['react_skill']}/10",
                        'python': f"{employee['python_skill']}/10",
                        'hours': f"{employee['hours_available']}h"
                    }
                })
            
            # Sortiere nach Score (beste zuerst)
            project_matches.sort(key=lambda x: x['score'], reverse=True)
            
            results.append({
                'project_name': project['name'],
                'project_id': project['id'],
                'priority': project['priority'],
                'react_needed': project.get('react_needed', 0),
                'python_needed': project.get('python_needed', 0),
                'hours_needed': project.get('hours_needed', 40),
                'best_match': project_matches[0],  # Bester Match
                'all_matches': project_matches     # Alle Matches
            })
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)