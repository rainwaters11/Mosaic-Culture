from app import app

if __name__ == "__main__":
    # Kill any existing process on port 5000 before starting
    import os
    os.system("kill -9 $(lsof -t -i:5000)") if os.name != "nt" else os.system("FOR /F \"tokens=5\" %P IN ('netstat -a -n -o ^| findstr :5000') DO TaskKill.exe /PID %P /F /T")
    app.run(host="0.0.0.0", port=5000, debug=True)