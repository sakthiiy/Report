
import os
import json
import random
import string
import cv2
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, Response, session,send_from_directory, flash
import face_recognition
import base64
from io import BytesIO
from PIL import Image
from werkzeug.utils import secure_filename



app = Flask(__name__)
app.secret_key = os.urandom(24)
face_recognized = False  # Global flag

# Load users from JSON
def load_users():
    file_path = "users.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []


def load_known_encodings():
    users = load_users()
    encodings = []
    for user in users:
        encoding = user.get("face_encoding")
        if isinstance(encoding, list) and len(encoding) == 128:
            encodings.append(np.array(encoding))
    return encodings


def gen_frames(user_face_encoding=None):
    global face_recognized

    known_encodings = load_known_encodings()
    cap = cv2.VideoCapture(0)

    while True:
        success, frame = cap.read()
        if not success:
            break

        rgb_frame = frame[:, :, ::-1]
        encodings = face_recognition.face_encodings(rgb_frame)
        text = "Face Not Recognized"
        color = (0, 0, 255)
        face_recognized = False

        for enc in encodings:
            if user_face_encoding:
                matches = face_recognition.compare_faces([np.array(user_face_encoding)], enc)
            else:
                matches = face_recognition.compare_faces(known_encodings, enc)

            if any(matches):
                text = "Face Recognized"
                color = (0, 255, 0)
                face_recognized = True
                break

        cv2.putText(frame, text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



    # Capture the face using OpenCV
def capture_face_image():
    cap = cv2.VideoCapture(0)  # Open default webcam
    if not cap.isOpened():
        print(" Error: Camera is not available!")
        return None

    print(" Press 'c' to capture image, or 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print(" Failed to capture frame.")
            break

        cv2.imshow("Register - Capture Face", frame)

        key = cv2.waitKey(1)
        if key & 0xFF == ord('c'):  # Capture image on 'c'
            # Save the captured image
            cv2.imwrite("captured_face.jpg", frame)
            print("Image captured!")
            cap.release()
            cv2.destroyAllWindows()
            return "captured_face.jpg"
        elif key & 0xFF == ord('q'):  # Quit on 'q'
            cap.release()
            cv2.destroyAllWindows()
            print(" Capture cancelled.")
            return None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
       if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Load users from JSON
        file_path = "users.json"
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                try:
                    users = json.load(file)
                except json.JSONDecodeError:
                    users = []
        else:
            users = []
            

       # Check username and password
        for user in users:
            if user["username"] == username and user["password"] == password:
                # Store user and face encoding in session
                session['user'] = username
                session['face_encoding'] = user.get("face_encoding")
                return redirect(url_for('face_recognition_page'))  # Redirect to face check

        return "Invalid username or password!"
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Function to load users from the JSON file
def load_users():
    file_path = "users.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []

# Function to encode face from image data
def encode_face(data_url):
    header, encoded = data_url.split(",", 1)
    image_data = base64.b64decode(encoded)
    image = Image.open(BytesIO(image_data)).convert("RGB")
    np_image = np.array(image)
    encodings = face_recognition.face_encodings(np_image)
    return encodings[0] if encodings else None

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Get form data
        fullname = request.form["fullname"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        image_data = request.form["face_image"]

        # Get the face encoding
        encoding = encode_face(image_data)
        if encoding is None:
            return "Face not detected. Please try again."

        # Check if the username already exists
        users = load_users()
        for user in users:
            if user["username"] == username:
                return "Username already exists. Please choose another one."

        # Create a new user entry
        new_entry = {
            "fullname": fullname,
            "email": email,
            "username": username,
            "password": password,
            "face_encoding": encoding.tolist()  # Convert encoding to list for JSON serialization
        }

        # Add new entry to existing user data
        users.append(new_entry)

        # Write updated users list back to JSON file
        file_path = "users.json"
        with open(file_path, "w") as file:
            json.dump(users, file, indent=4)

        # Redirect to success page
        return redirect(url_for("success", username=username))

    # Render the registration form
    return render_template("register.html")

@app.route("/success/<username>")
def success(username):
    return f"User {username} registered successfully!"


@app.route('/video_feed')
def video_feed():
    # Capture session data safely inside the request context
    face_encoding = session.get('face_encoding')
    return Response(gen_frames(face_encoding), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/face_recognition')
def face_recognition_page():
    return render_template('face_recognition.html', face_recognized=face_recognized)

@app.route('/check_face')
def check_face():
    if face_recognized:
        session['face_recognized'] = True
        user = session.get('user')

        if user:
            # Check if user has any card entry in cards.json
            if os.path.exists("cards.json"):
                with open("cards.json", "r") as f:
                    cards = json.load(f)
                user_cards = [card for card in cards if card["user"] == user]
            else:
                user_cards = []

            if user_cards:
                return redirect(url_for('view_own_card'))  # If card exists, view it
            else:
                return redirect(url_for('generate_card_page'))  # Otherwise, go generate one

    return redirect(url_for('face_recognition_page'))  # If not recognized


@app.route('/generate_card_page')
def generate_card_page():
    if session.get('face_recognized'):
        return render_template('generate_card.html')
    return redirect(url_for('index'))

@app.route('/generate_card', methods=['POST'])
def generate_card():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']

    # Create upload folder if not exists
    
    upload_folder = os.path.join("uploads", user)
    os.makedirs(upload_folder, exist_ok=True)

    
    # Save each uploaded file separately
    smart_file = request.files['smart_card']
    smart_path = os.path.join(upload_folder, f"{user}_smart.{smart_file.filename.rsplit('.', 1)[-1]}")
    smart_file.save(smart_path)

    pan_file = request.files['pan_card']
    pan_path = os.path.join(upload_folder, f"{user}_pan.{pan_file.filename.rsplit('.', 1)[-1]}")
    pan_file.save(pan_path)

    aadhar_file = request.files['aadhar_card']
    aadhar_path = os.path.join(upload_folder, f"{user}_aadhar.{aadhar_file.filename.rsplit('.', 1)[-1]}")
    aadhar_file.save(aadhar_path)

    license_file = request.files['license_card']
    license_path = os.path.join(upload_folder, f"{user}_license.{license_file.filename.rsplit('.', 1)[-1]}")
    license_file.save(license_path)

    # Save relative paths to JSON
    card_data = {
        "user": user,
        "smart_card": smart_path.replace("\\", "/"),
        "pan_card": pan_path.replace("\\", "/"),
        "aadhar_card": aadhar_path.replace("\\", "/"),
        "license_card": license_path.replace("\\", "/")
    }

    

    # Load or create cards.json
    if os.path.exists("cards.json"):
        with open("cards.json", "r") as f:
            cards = json.load(f)
    else:
        cards = []

    # Prevent duplicates
    for card in cards:
        if card["user"] == user:
            return "Card already uploaded."

    cards.append(card_data)
    with open("cards.json", "w") as f:
        json.dump(cards, f, indent=4)

    
    return f" ID card uploaded of {user}"
    return redirect(url_for('view_own_card'))



@app.route('/view_cards')
def view_cards():
    if not os.path.exists("cards.json"):
        cards = []
    else:
        with open("cards.json", "r") as f:
            cards = json.load(f)
    return render_template("view_cards.html", cards=cards)

@app.route('/uploads/<username>/<filename>')
def uploaded_file(username, filename):
    return send_from_directory(os.path.join('uploads', username), filename)

@app.route('/view_own_card')
def view_own_card():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))

    # Load card data for this specific user
    if os.path.exists("cards.json"):
        with open("cards.json", "r") as f:
            cards = json.load(f)
        user_cards = [card for card in cards if card["user"] == user]
    else:
        user_cards = []

    return render_template("view_own_cards.html", cards=user_cards)



if __name__ == '__main__':
    app.run(debug=True, port=8000)
    app.run(debug=True)




