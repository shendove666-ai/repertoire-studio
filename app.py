"""Classical piano repertoire and practice analysis.

Author: Mao Wen
"""

import os
import sqlite3
from datetime import date, timedelta
from functools import wraps
from typing import Any, Callable

from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Build a studio, with configuration overrides for isolated instances."""
    app = Flask(__name__, instance_relative_config=True)
    default_db = os.path.join(app.root_path, "repertoire.db")
    demo_database = os.environ.get("REPERTOIRE_DEMO_DATABASE")

    app.config.from_mapping(
        SECRET_KEY=(
            os.environ["FLASK_SECRET_KEY"]
            if demo_database
            else os.environ.get("FLASK_SECRET_KEY", "repertoire-studio-dev-key-2026")
        ),
        DATABASE=demo_database or default_db,
        DEMO_MODE=bool(demo_database),
        SEED_USERNAME="studio-demo" if demo_database else "maowen",
        SEED_PASSWORD="demo-only" if demo_database else "piano2026",
    )

    if test_config is not None:
        app.config.update(test_config)

    def get_db() -> sqlite3.Connection:
        """Reuse one connection per application context; enforce foreign keys on it."""
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON;")
        return g.db

    @app.teardown_appcontext
    def close_db(exception: BaseException | None = None) -> None:
        """Release the context-owned connection after either request outcome."""
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def seed_initial_data(db: sqlite3.Connection) -> None:
        """Seed an empty user table with repertoire and linked practice sessions."""
        existing_account = db.execute("SELECT id FROM users LIMIT 1").fetchone()
        if existing_account is not None:
            return

        seed_password_hash = generate_password_hash(app.config["SEED_PASSWORD"])
        account_insert = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (app.config["SEED_USERNAME"], seed_password_hash),
        )
        user_id = account_insert.lastrowid

        classical_works = [
            (
                user_id,
                "Heroic Polonaise in A-flat Major",
                "Frederic Chopin",
                "Op. 53",
                "A-flat Major",
                "Ternary Form (A-B-A')",
                "Left-hand descending octave ostinato, voicing inner chords",
                5,
                "Performance Ready",
                "Focus on wrist relaxation during the E major middle section octave passages.",
            ),
            (
                user_id,
                "Fugue in C Minor (WTC Book I)",
                "Johann Sebastian Bach",
                "BWV 847",
                "C Minor",
                "Three-Voice Fugue",
                "Independent contrapuntal voice leading, crisp articulation",
                4,
                "Polishing",
                "Isolate middle voice entries on a silent keyboard surface before combining.",
            ),
            (
                user_id,
                "Piano Sonata No. 23 'Appassionata'",
                "Ludwig van Beethoven",
                "Op. 57",
                "F Minor",
                "Sonata-Allegro Form",
                "Sudden dynamic contrasts, rapid arpeggio figurations",
                5,
                "In Progress",
                "Maintain structural pulse across the Allegro assai development section.",
            ),
            (
                user_id,
                "Jeux d'eau",
                "Maurice Ravel",
                "M. 30",
                "E Major",
                "Sonata-Allegro (Impressionist)",
                "Double-note cascades, half-pedaling resonance control",
                5,
                "In Progress",
                "Keep thumb weight minimal in rapid right-hand figurations.",
            ),
            (
                user_id,
                "Traumerei (Kinderszenen)",
                "Robert Schumann",
                "Op. 15, No. 7",
                "F Major",
                "Binary Rounded Form",
                "Cantabile soprano projection, harmonic rubato balance",
                2,
                "Performance Ready",
                "Shape recurring upward fourth motifs with subtle tonal shading.",
            ),
        ]

        if app.config["DEMO_MODE"]:
            from demo_seed import DEMO_SESSIONS, DEMO_WORKS

            classical_works = [(user_id, *piece_fields) for piece_fields in DEMO_WORKS]

        piece_ids: list[int] = []
        for piece_fields in classical_works:
            piece_insert = db.execute(
                """
                INSERT INTO pieces (
                    user_id, title, composer, opus_catalog, musical_key,
                    musical_form, technical_focus, difficulty, mastery_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                piece_fields,
            )
            piece_ids.append(int(piece_insert.lastrowid))

        today = date.today()
        sample_sessions = [
            (user_id, piece_ids[0], 55, 116, "mm. 81-120", "Left-hand octave stamina drill at 85% tempo.", (today - timedelta(days=6)).isoformat()),
            (user_id, piece_ids[1], 40, 88, "mm. 1-31", "Separate voice phrasing and subject articulation.", (today - timedelta(days=5)).isoformat()),
            (user_id, piece_ids[2], 65, 132, "mm. 65-135", "Development transition voicing and pedal clarity.", (today - timedelta(days=4)).isoformat()),
            (user_id, piece_ids[0], 50, 122, "mm. 1-48", "Full exposition run-through with rhythmic precision.", (today - timedelta(days=3)).isoformat()),
            (user_id, piece_ids[3], 45, 108, "mm. 19-50", "Cadenza balance and upper register shimmer.", (today - timedelta(days=2)).isoformat()),
            (user_id, piece_ids[4], 30, 66, "mm. 1-24", "Soprano line legato and inner chord voicing.", (today - timedelta(days=1)).isoformat()),
            (user_id, piece_ids[0], 60, 126, "mm. 121-182", "Coda integration and dynamic pacing.", today.isoformat()),
        ]

        if app.config["DEMO_MODE"]:
            sample_sessions = [
                (user_id, piece_ids[piece_index], minutes, bpm, measures, notes,
                 (today - timedelta(days=days_before)).isoformat())
                for piece_index, days_before, minutes, bpm, measures, notes in DEMO_SESSIONS
            ]

        db.executemany(
            """
            INSERT INTO practice_logs (
                user_id, piece_id, duration_minutes, target_bpm,
                measure_range, session_notes, practiced_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            sample_sessions,
        )
        db.commit()

    def init_db() -> None:
        """Apply the schema and seed the newly created database."""
        db = get_db()
        schema_path = os.path.join(app.root_path, "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            db.executescript(schema_file.read())
        seed_initial_data(db)

    with app.app_context():
        if not os.path.exists(app.config["DATABASE"]):
            init_db()

    def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator redirecting unauthenticated visitors to the login page."""
        @wraps(view)
        def wrapped_view(**kwargs: Any) -> Any:
            if session.get("user_id") is None:
                return redirect(url_for("login"))
            return view(**kwargs)

        return wrapped_view

    @app.before_request
    def load_logged_in_user() -> None:
        """Attach the authenticated user record to flask.g for template access."""
        user_id = session.get("user_id")
        if user_id is None:
            g.user = None
        else:
            g.user = get_db().execute(
                "SELECT id, username FROM users WHERE id = ?", (user_id,)
            ).fetchone()

    @app.route("/")
    def index() -> Any:
        """Render studio dashboard for signed-in users or landing overview."""
        if g.user is None:
            return render_template("index.html", summary=None, recent_logs=[])

        db = get_db()
        user_id = g.user["id"]

        summary_row = db.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM pieces WHERE user_id = ?) AS total_pieces,
                (SELECT COUNT(*) FROM pieces WHERE user_id = ? AND mastery_status = 'Performance Ready') AS ready_pieces,
                (SELECT COALESCE(SUM(duration_minutes), 0) FROM practice_logs WHERE user_id = ?) AS total_minutes,
                (SELECT COUNT(*) FROM practice_logs WHERE user_id = ?) AS total_sessions
            """,
            (user_id, user_id, user_id, user_id),
        ).fetchone()

        recent_logs = db.execute(
            """
            SELECT
                pl.id, pl.duration_minutes, pl.target_bpm, pl.measure_range,
                pl.session_notes, pl.practiced_on, p.title, p.composer, p.opus_catalog
            FROM practice_logs pl
            JOIN pieces p ON pl.piece_id = p.id
            WHERE pl.user_id = ?
            ORDER BY pl.practiced_on DESC, pl.id DESC
            LIMIT 6
            """,
            (user_id,),
        ).fetchall()

        pieces = db.execute(
            "SELECT id, title, composer, opus_catalog FROM pieces WHERE user_id = ? ORDER BY title ASC",
            (user_id,),
        ).fetchall()

        return render_template(
            "index.html",
            summary=summary_row,
            recent_logs=recent_logs,
            pieces=pieces,
            today_str=date.today().isoformat(),
        )

    @app.route("/register", methods=("GET", "POST"))
    def register() -> Any:
        """Create an account and start a session after the insert commits."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            confirmation = request.form.get("confirmation", "")

            if not username or not password:
                flash("Username and password are required.", "error")
            elif len(username) < 3:
                flash("Username must contain at least 3 characters.", "error")
            elif password != confirmation:
                flash("Password confirmation does not match.", "error")
            else:
                db = get_db()
                try:
                    cursor = db.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)),
                    )
                    db.commit()
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    flash("Account created successfully. Welcome to Repertoire Studio.", "success")
                    return redirect(url_for("index"))
                except sqlite3.IntegrityError:
                    flash("That username is already taken.", "error")

        return render_template("register.html")

    @app.route("/login", methods=("GET", "POST"))
    def login() -> Any:
        """Check the stored password hash before setting the session account."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            db = get_db()
            user = db.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Invalid username or password.", "error")
            else:
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("index"))

        return render_template("login.html")

    @app.route("/logout")
    def logout() -> Any:
        """End the session and return to the public landing page."""
        session.clear()
        return redirect(url_for("index"))

    @app.route("/repertoire")
    @login_required
    def repertoire() -> Any:
        """List and filter repertoire works with total logged practice minutes."""
        db = get_db()
        status_filter = request.args.get("status", "All").strip()
        query_text = request.args.get("q", "").strip()

        sql = """
            SELECT
                p.*,
                COALESCE(SUM(pl.duration_minutes), 0) AS logged_minutes,
                COUNT(pl.id) AS session_count
            FROM pieces p
            LEFT JOIN practice_logs pl ON p.id = pl.piece_id
            WHERE p.user_id = ?
        """
        query_parameters: list[Any] = [g.user["id"]]

        if status_filter and status_filter != "All":
            sql += " AND p.mastery_status = ?"
            query_parameters.append(status_filter)

        if query_text:
            sql += " AND (p.title LIKE ? OR p.composer LIKE ? OR p.musical_form LIKE ? OR p.technical_focus LIKE ?)"
            like_term = f"%{query_text}%"
            query_parameters.extend([like_term, like_term, like_term, like_term])

        sql += " GROUP BY p.id ORDER BY p.created_at DESC, p.id DESC"
        works = db.execute(sql, query_parameters).fetchall()

        return render_template(
            "repertoire.html",
            works=works,
            status_filter=status_filter,
            query_text=query_text,
        )

    @app.route("/repertoire/add", methods=("GET", "POST"))
    @login_required
    def add_piece() -> Any:
        """Store a score's form and practice metadata for the signed-in user."""
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            composer = request.form.get("composer", "").strip()
            opus_catalog = request.form.get("opus_catalog", "").strip() or "Unnumbered"
            musical_key = request.form.get("musical_key", "").strip()
            musical_form = request.form.get("musical_form", "").strip()
            technical_focus = request.form.get("technical_focus", "").strip()
            mastery_status = request.form.get("mastery_status", "In Progress").strip()
            notes = request.form.get("notes", "").strip()

            try:
                difficulty = int(request.form.get("difficulty", 3))
            except ValueError:
                difficulty = 3

            if not title or not composer or not musical_key or not musical_form:
                flash("Title, composer, key, and musical form are required.", "error")
            elif difficulty < 1 or difficulty > 5:
                flash("Difficulty must be between 1 and 5.", "error")
            else:
                db = get_db()
                db.execute(
                    """
                    INSERT INTO pieces (
                        user_id, title, composer, opus_catalog, musical_key,
                        musical_form, technical_focus, difficulty, mastery_status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        g.user["id"],
                        title,
                        composer,
                        opus_catalog,
                        musical_key,
                        musical_form,
                        technical_focus or "General musical phrasing",
                        difficulty,
                        mastery_status,
                        notes,
                    ),
                )
                db.commit()
                flash(f"Added '{title}' to your repertoire catalog.", "success")
                return redirect(url_for("repertoire"))

        return render_template("add_piece.html")

    @app.route("/repertoire/<int:piece_id>/status", methods=("POST",))
    @login_required
    def update_piece_status(piece_id: int) -> Any:
        """Accept a catalog mastery stage for a piece owned by the current user."""
        new_status = request.form.get("mastery_status", "").strip()
        mastery_stages = {"In Progress", "Polishing", "Performance Ready"}
        if new_status in mastery_stages:
            db = get_db()
            db.execute(
                "UPDATE pieces SET mastery_status = ? WHERE id = ? AND user_id = ?",
                (new_status, piece_id, g.user["id"]),
            )
            db.commit()
            flash("Mastery status updated.", "success")
        return redirect(url_for("repertoire"))

    @app.route("/repertoire/<int:piece_id>/delete", methods=("POST",))
    @login_required
    def delete_piece(piece_id: int) -> Any:
        """Delete a repertoire work and its associated practice logs."""
        db = get_db()
        db.execute(
            "DELETE FROM pieces WHERE id = ? AND user_id = ?",
            (piece_id, g.user["id"]),
        )
        db.commit()
        flash("Repertoire work removed.", "success")
        return redirect(url_for("repertoire"))

    @app.route("/practice/log", methods=("POST",))
    @login_required
    def log_practice() -> Any:
        """Record a structured practice session for an existing piece."""
        try:
            piece_id = int(request.form.get("piece_id", 0))
            duration_minutes = int(request.form.get("duration_minutes", 0))
            target_bpm = int(request.form.get("target_bpm", 0))
        except ValueError:
            flash("Duration and target BPM must be valid numbers.", "error")
            return redirect(url_for("index"))

        measure_range = request.form.get("measure_range", "").strip() or "Full work"
        session_notes = request.form.get("session_notes", "").strip()
        practiced_on = request.form.get("practiced_on", "").strip() or date.today().isoformat()

        if piece_id <= 0 or duration_minutes <= 0 or target_bpm <= 0:
            flash("Please select a piece and enter positive duration and BPM values.", "error")
            return redirect(url_for("index"))

        db = get_db()
        piece = db.execute(
            "SELECT id FROM pieces WHERE id = ? AND user_id = ?",
            (piece_id, g.user["id"]),
        ).fetchone()

        if piece is None:
            flash("Selected repertoire work was not found.", "error")
            return redirect(url_for("index"))

        db.execute(
            """
            INSERT INTO practice_logs (
                user_id, piece_id, duration_minutes, target_bpm,
                measure_range, session_notes, practiced_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                g.user["id"],
                piece_id,
                duration_minutes,
                target_bpm,
                measure_range,
                session_notes,
                practiced_on,
            ),
        )
        db.commit()
        flash("Practice session logged.", "success")
        return redirect(url_for("index"))

    @app.route("/analytics")
    @login_required
    def analytics() -> Any:
        """Render the canvases populated by the separate analytics endpoint."""
        return render_template("analytics.html")

    @app.route("/api/analytics-data")
    @login_required
    def analytics_data() -> Any:
        """Return composer minutes, observed-day minutes, and counts by form."""
        db = get_db()
        user_id = g.user["id"]

        composer_totals = db.execute(
            """
            SELECT p.composer, COALESCE(SUM(pl.duration_minutes), 0) AS minutes
            FROM pieces p
            LEFT JOIN practice_logs pl ON p.id = pl.piece_id
            WHERE p.user_id = ?
            GROUP BY p.composer
            ORDER BY minutes DESC
            """,
            (user_id,),
        ).fetchall()

        daily_totals = db.execute(
            """
            SELECT practiced_on, SUM(duration_minutes) AS minutes
            FROM practice_logs
            WHERE user_id = ?
            GROUP BY practiced_on
            ORDER BY practiced_on ASC
            LIMIT 14
            """,
            (user_id,),
        ).fetchall()

        form_counts = db.execute(
            """
            SELECT musical_form, COUNT(*) AS count
            FROM pieces
            WHERE user_id = ?
            GROUP BY musical_form
            ORDER BY count DESC
            """,
            (user_id,),
        ).fetchall()

        return jsonify(
            {
                "composers": [dict(row) for row in composer_totals],
                "daily": [dict(row) for row in daily_totals],
                "forms": [dict(row) for row in form_counts],
            }
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
