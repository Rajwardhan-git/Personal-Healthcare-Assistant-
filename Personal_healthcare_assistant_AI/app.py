from flask import Flask, render_template, request, jsonify
import pickle
import numpy as np
import pandas as pd

from flask import session, redirect, url_for, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# Load the model and data
# model = pickle.load(open('models/model.pkl', 'rb'))
label_encoder = pickle.load(open('models/label_encoder.pkl', 'rb'))
symptoms_list = pickle.load(open('models/symptom_list.pkl', 'rb')) 
disease_index= pickle.load(open('models/disease_index.pkl', 'rb'))
disease_list= pickle.load(open('models/disease_list.pkl', 'rb'))

svc_model = pickle.load(open('models/svc_model.pkl', 'rb'))

symptom_index = {symptom: idx for idx, symptom in enumerate(symptoms_list)}
with open('models/symptom_index.pkl','wb') as f:
    pickle.dump(symptom_index,f)

#load the symptom index
symptom_index = pickle.load(open('models/symptom_index.pkl','rb'))


# Function to predict disease from symptoms

def get_predicted_value(patient_symptoms):
    input_vector = np.zeros(len(symptom_index))
    for item in patient_symptoms:
        input_vector[symptom_index[item]] = 1
    
    prediction = svc_model.predict([input_vector])[0]
    predicted_disease = label_encoder.inverse_transform([prediction])[0]
    return predicted_disease


# load the  datasets
precautions = pd.read_csv("dataset\precautions_df.csv")
workout = pd.read_csv("dataset\workout_df.csv")
description = pd.read_csv("dataset\description.csv")
medications = pd.read_csv('dataset\medications.csv')
diets = pd.read_csv("dataset\diets.csv")


def helper(pre_disease):
    desc = description[description['Disease'] == pre_disease]['Description']
    desc = " ".join([w for w in desc])

    pre = precautions[precautions['Disease'] == pre_disease][['Precaution_1', 'Precaution_2', 'Precaution_3', 'Precaution_4']]
    pre = [col for col in pre.values]

    med = medications[medications['Disease'] == pre_disease]['Medication']
    med = [med for med in med.values]

    die = diets[diets['Disease'] == pre_disease]['Diet']
    die = [die for die in die.values]

    wrkout = workout[workout['disease'] == pre_disease] ['workout']


    return desc,pre,med,die,wrkout

'''
if __name__ == "__main__":
    patient_symptoms = ['vomiting']
    pre_disease = get_predicted_value(patient_symptoms)
    print("\n=== Prediction Result ===")
    print(f"Input Symptoms: {patient_symptoms}")
    print(f"Predicted Disease: {pre_disease}")
'''

app.secret_key = '0dfe4c2b0a58d1267c7f7344eaf649ad'

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  
app.config['MYSQL_PASSWORD'] = ''  
app.config['MYSQL_DB'] = 'medicine_system'  

mysql = MySQL(app)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        cur = mysql.connection.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            mysql.connection.commit()
            flash('Registration successful. Please log in.')
            return redirect(url_for('login'))
        except:
            flash('Username already exists.')
            return redirect(url_for('register'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    session.pop('username', None)  # Clear the session on login page load
    session.clear()

    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()

        if user:
            stored_password = user[2]  
            if check_password_hash(stored_password, password_input):
                session['username'] = username
                return render_template("home.html")
            else:
                flash("Invalid password.", "danger")
        else:
            flash("Username not found.", "danger")

    return render_template("login.html")

# Helper function to check if the user is logged in
def is_logged_in():
    return 'username' in session

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove the username from session
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))  # Redirect to login after logging out


# creating routes========================================
@app.route('/')
def root():
    session.pop('username', None)  # Clear the session on login page load
    session.clear()
    return redirect(url_for('index'))
  # Redirect to index if logged in

@app.route('/index')
def index():
    session.pop('username', None)  # Clear the session on login page load
    session.clear()
   # Prevent access without login
    return render_template('index.html')  # Render the actual page


@app.route('/predict', methods=['GET', 'POST'])
def home():
    if not is_logged_in():
        return redirect(url_for('index'))

    if request.method == 'POST':
        symptom = request.form.get('symptoms')
        
        # Check for empty input or default placeholder
        if not symptom or symptom.lower().strip() in ["", "symptoms"]:
            message = "Please enter valid symptoms."
            return render_template('home.html', message=message)

        # Process the input into a list of symptoms
        user_symptoms = [s.strip().strip("[]' ") for s in symptom.split(',') if s.strip()]

        # Check if we got any valid symptoms after processing
        if not user_symptoms:
            message = "No recognizable symptoms found. Please try again."
            return render_template('home.html', message=message)

        try:
            # Try to predict
            predicted_disease = get_predicted_value(user_symptoms)

            # Handle if prediction failed (e.g., due to unknown symptoms)
            if not predicted_disease:
                message = "Could not predict disease from the given symptoms. Please try again."
                return render_template('home.html', message=message)

            # Get additional information
            dis_des, precautions, medications, rec_diet, workout = helper(predicted_disease)

            my_precautions = [p for p in precautions[0]]

            return render_template('home.html', predicted_disease=predicted_disease, dis_des=dis_des,
                       my_precautions=my_precautions, medications=medications, my_diet=rec_diet,
                       workout=workout, entered_symptoms=symptom)
        except Exception as e:
            print(f"Prediction error: {e}")
            message = "Undefined data for processing your request. Please check your symptoms and try again."
            return render_template('home.html', message=message)

    return render_template('home.html')


@app.route('/start')
def start():
    return render_template("login.html")

@app.route('/about')
def about():
    session.pop('username', None)  # Clear the session on login page load
    session.clear()
    return render_template("about.html")

if __name__ == '__main__':                                                                                                                                                                                                                                                                             

    app.run(debug=True)
