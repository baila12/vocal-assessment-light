import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api import create_app
from config import config

app = create_app(config)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("=" * 50)
    print("Vocal Assessment Web - http://localhost:" + str(port))
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True, use_reloader=False)