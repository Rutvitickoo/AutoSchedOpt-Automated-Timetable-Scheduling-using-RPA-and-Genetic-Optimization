from flask import Flask, render_template, request, redirect, url_for, session
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'
users = {}

# ✅ Add this line to fix the error
app.config['UPLOAD_FOLDER'] = 'uploads'

# Imports (must be present already)
import pandas as pd
import random

# ✨ Add this Genetic Algorithm code right here
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
time_slots = ['9:00', '10:00', '11:00', '12:00']

def generate_random_timetable(data, num_slots=5):
    subjects = data['Subject'].unique()
    teachers = data['Teacher'].unique()
    rooms = data['Room'].unique()

    timetable = []
    for i in range(num_slots):
        sub = random.choice(subjects)
        teacher = data[data['Subject'] == sub]['Teacher'].values[0]
        room = random.choice(rooms)
        day = random.choice(days)
        time_slot = random.choice(time_slots)

        timetable.append({
            'Slot': f'Slot {i+1}',
            'Subject': sub,
            'Teacher': teacher,
            'Room': room,
            'Day': day,
            'Time Slot': time_slot
        })

    return pd.DataFrame(timetable)


def fitness(timetable):
    teacher_conflicts = timetable.duplicated(subset=['Slot', 'Teacher']).sum()
    room_conflicts = timetable.duplicated(subset=['Slot', 'Room']).sum()
    return -(teacher_conflicts + room_conflicts)

def genetic_algorithm(data, generations=100, population_size=10):
    population = [generate_random_timetable(data) for _ in range(population_size)]

    for _ in range(generations):
        scored = [(fitness(t), t) for t in population]
        scored.sort(key=lambda x: x[0], reverse=True)
        population = [t[1] for t in scored[:population_size//2]]

        new_population = population.copy()
        while len(new_population) < population_size:
            parent1 = random.choice(population)
            parent2 = random.choice(population)
            child = pd.concat([parent1.iloc[:len(parent1)//2], parent2.iloc[len(parent2)//2:]]).reset_index(drop=True)
            new_population.append(child)

        population = new_population

    best = max(population, key=fitness)
    return best


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.get(email)
        if user and user['password'] == password:
            session['email'] = email
            session['role'] = user['role']
            return redirect('/admin' if user['role'] == 'admin' else '/student')
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        if not email or not password or not role:
            return 'All fields are required.'
        users[email] = {'password': password, 'role': role}
        return redirect('/login')
    return render_template('signup.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin':
        return redirect('/login')

    timetable_html = None

    if request.method == 'POST':
        file = request.files['timetable_file']
        if file:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            try:
                df = pd.read_excel(filepath, engine='openpyxl')
                optimized = genetic_algorithm(df)
                optimized.to_excel('uploads/optimized_schedule.xlsx', index=False)

                # Convert to HTML with better styling
                timetable_html = optimized.to_html(classes='table-auto w-full text-left border-collapse border border-gray-300',index=False,border=0)
            except Exception as e:
                timetable_html = f"<p class='text-red-500'>Error: {e}</p>"

    return render_template('admin_dashboard.html', timetable=timetable_html)



@app.route('/student')
def student():
    if session.get('role') != 'student':
        return redirect('/login')

    timetable = None
    calendar = {}

    try:
        df = pd.read_excel('uploads/optimized_schedule.xlsx', engine='openpyxl')

        timetable = df.to_html(index=False,
    border=0,
    escape=False,
    classes="min-w-full table-auto border-collapse text-sm",
    justify='center')

        for _, row in df.iterrows():
            key = f"{row['Day']} {row['Time Slot']}"
            calendar[key] = f"{row['Subject']}<br><span class='text-sm text-gray-500'>{row['Teacher']}</span>"
    except Exception as e:
        timetable = f"<p class='text-red-500'>Error loading timetable: {e}</p>"

    return render_template('student_dashboard.html', timetable=timetable, calendar=calendar)



@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True, port=5001)
