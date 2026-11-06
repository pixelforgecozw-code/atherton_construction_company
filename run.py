from app import create_app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        app.setup_database()  # creates tables + default admin on first run
    app.run(debug=app.config.get("DEBUG", False))
#hi
