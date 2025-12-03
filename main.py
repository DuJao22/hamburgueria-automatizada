from app import app, socketio, init_db, start_ping_thread

init_db()
start_ping_thread()

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
