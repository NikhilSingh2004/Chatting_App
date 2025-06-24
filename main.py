import os
import random
import traceback
from datetime import datetime
from dotenv import load_dotenv
from string import ascii_letters
from flask_socketio import SocketIO, send, join_room, leave_room
from flask import Flask, request, redirect, url_for, render_template, session
load_dotenv()

# Move the Session and Chat to Mongo
rooms = {}

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
socket = SocketIO()
socket.init_app(app=app)

def create_room(room_code):
  try:
    if len(rooms) > 100:
      return None, "Maximium Room Creation Limit Exceeded"
    
    if (room_code in rooms) or (len(room_code) < 5):
      while True:
        new_room = "".join([random.choice(ascii_letters) for _ in range(5)])
        if new_room not in rooms:
          return new_room, None
    else:
      return room_code, None
  except:
    print(f"Error :: create_room :: {traceback.format_exc()}")
    return None, "Something Went Wrong (1)"

@app.route("/", methods=["POST", "GET"])
def main(error=None):
  session.clear()
  try:
    if request.method == "POST":
      print("Form Data : ", request.form)
      name = request.form.get("name", "").strip()
      room = request.form.get("room", "").strip()
      create = request.form.get("create", False)
      join = request.form.get("join", False)
      
      if not name:
        return render_template("home.html", error="Please Enter the Name")
      elif join!=False:
        if not room:
          return render_template("home.html", error="Please Enter the Room Code")
        elif room not in rooms:
          return render_template("home.html", error="Room Does not Exists")
      elif create!=False:
        room, error = create_room(room_code=room)
        if error:
          return render_template("home.html", error=error)
        print(rooms)
        rooms[room] = { "members" : 0, "messages" : [] }
      
      session["room"] = room
      session["name"] = name
      
      return redirect(url_for("room"))
    else:
      return render_template("home.html", error=error)
  except:
    print(f"Error :: {traceback.format_exc()}")
    return render_template("home.html", error="Something Went Wrong (0)")
  
@app.route("/room", methods=["POST", "GET"])
def room():
  try:
    room = session.get("room")
    name = session.get("name")
    
    if not room or room not in rooms or not name:
      return redirect(url_for("main"))
    
    return render_template("room.html", room=room, name=name, messages=rooms.get(room, {}).get("messages"))
  except:
    print(f"Error :: {traceback.format_exc()}")
    return render_template("home.html", error="Something Went Wrong (0)")
  
@socket.on("connect")
def connect(auth):
  try:
    room = session.get("room")
    name = session.get("name")
    
    if not room or not name:
      return redirect(url_for("main"))
    elif room not in rooms:
      leave_room(room)
      return redirect(url_for("main"))
    elif rooms[room]["members"] >= 32:
      return redirect(url_for("main", error="Room is full"))
    
    join_room(room)
    send({"name" :name, "message" : "has joined the room", "time" : datetime.strftime(datetime.now(), "%d-%m-%Y %H:%m:%S")}, to=room)
    rooms[room]["members"] += 1
    print("{} Joined {}, Total Members : {}".format(name, room, rooms[room]["members"]))
  except:
    print(f"Error :: connect :: {traceback.format_exc()}")
    return render_template("home.html", error="Something Went Wrong (2)")
  
  
@socket.on("disconnect")
def disconnect(auth):
  try:
    room = session.get("room")
    name = session.get("name")
    
    leave_room(room)
    send({"name":name, "message" : "has left the room", "time" : datetime.strftime(datetime.now(), "%d-%m-%Y %H:%m:%S")}, to=room)
    
    if room in rooms:
      rooms[room]["members"] -= 1
      if rooms[room]["members"] <= 0:
        print("Room Deleted : ",rooms[room])
        del rooms[room]
    
      print("{} Left {}, Total Members : {}".format(name, room, rooms.get(room, {}).get("members")))
  except:
    print(f"Error :: disconnect :: {traceback.format_exc()}")
    return render_template("home.html", error="Something Went Wrong (3)")
  
@socket.on("message")
def message(data):
  try:
    room = session.get("room")

    if room not in rooms:
      return redirect(url_for("main"))
    
    content = {
      "to" : room,
      "name" : session.get("name"),
      "message" : data["message"],
      "time" : datetime.strftime(datetime.now(), "%d-%m-%Y %H:%m:%S")
    }
    
    rooms[room]["messages"].append(content)
    
    send(content, to=room)
  except:
    print(f"Error :: message :: {traceback.format_exc()}")
    return render_template("home.html", error="Something Went Wrong (4)")
    
if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  socket.run(app, host='0.0.0.0', port=port)