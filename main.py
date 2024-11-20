from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

# Initialize the Flask application
app = Flask(__name__)
app.config["SECRET_KEY"] = "shhhh"  # Secret key for session management
socketio = SocketIO(app)  # Initialize SocketIO for real-time communication

# Dictionary to store room data, including members and messages
rooms = {}

# Function to generate a unique room code
def generate_unique_code(length):
    """
    Generate a unique room code of the given length.
    Ensures the code is not already in use.
    """
    while True:
        code = "".join(random.choice(ascii_uppercase) for _ in range(length))  # Generate a random code
        if code not in rooms:  # Check if the code is unique
            return code

# Route for the home page
@app.route("/", methods=["POST", "GET"])
def home():
    """
    Render the home page and handle user actions: 
    - Create a room
    - Join an existing room
    """
    session.clear()  # Clear the session to start fresh for a new user

    if request.method == "POST":
        # Get user inputs from the form
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        # Check if the user entered a name
        if not name:
            return render_template("home.html", error="Please enter a name", code=code, name=name)

        if create:  # User wants to create a new room
            room = generate_unique_code(4)  # Generate a 4-character room code
            rooms[room] = {"members": 0, "message": []}  # Initialize room data
        elif join:  # User wants to join an existing room
            # Check if the room exists
            if not code or code not in rooms:
                return render_template("home.html", error="This Room does not exist.", code=code, name=name)
            room = code
        else:  # Neither create nor join selected
            return render_template("home.html", error="Please select an action (create or join).", code=code, name=name)

        # Save user information in the session
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))  # Redirect to the room page

    # Render the home page for GET requests
    return render_template("home.html")

# Route for the room page
@app.route("/room")
def room():
    """
    Render the chat room page for a valid user.
    Redirect to the home page if the user or room is invalid.
    """
    room = session.get("room")  # Get room code from the session
    name = session.get("name")  # Get username from the session

    # Check if the user is valid and the room exists
    if room is None or name is None or room not in rooms:
        return redirect(url_for("home"))  # Redirect invalid users to the home page

    return render_template("room.html", room=room, name=name, code=room )  # Render the room page

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    content = {
        "name": session.get("name"),
        "message":data ["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said:{data['data']}")


# Socket.IO event to handle new connections
@socketio.on("connect")
def connect(auth):
    """
    Handle a new connection to the server.
    Join the user to the room and notify others in the room.
    """
    room = session.get("room")  # Get room code from the session
    name = session.get("name")  # Get username from the session

    if not room or not name:  # Validate the session data
        return  # Stop processing if data is invalid

    if room not in rooms:  # Check if the room exists
        leave_room(room)  # Leave the room if it doesn't exist
        return

    join_room(room)  # Add the user to the room
    send({"name": name, "message": "has entered the room"}, to=room)  # Notify others in the room
    rooms[room]["members"] += 1  # Increment the member count for the room
    print(f"{name} joined room {room}")  # Log the event on the server


@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <=0:
          del rooms[room]

    send({"name": name, "message": "has left the room"}, to=room)
    print(f" {name} has left the room {room}")


# Entry point of the application
if __name__ == "__main__":
    socketio.run(app, debug=False)  # Run the app with debug mode enabled