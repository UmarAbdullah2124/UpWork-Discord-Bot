import sqlite3
import datetime
import logging

logger = logging.getLogger("Database")

class JobDatabase:
    def __init__(self, db_path="upwork_jobs.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    job_id TEXT,
                    url_source TEXT,
                    title TEXT,
                    first_seen TIMESTAMP,
                    PRIMARY KEY (job_id, url_source)
                )
            """)
            # Removed 'client_hires' from this list
            cols = [
                "budget TEXT", "proposals TEXT", "location TEXT",
                "total_spent REAL", "description TEXT", "job_type TEXT",
                "experience_level TEXT", "duration TEXT",
                "published_time TEXT", "skills TEXT"
            ]
            for col in cols:
                try:
                    conn.execute(f"ALTER TABLE seen_jobs ADD COLUMN {col}")
                except sqlite3.OperationalError:
                    pass
            conn.commit()

    def is_new_job(self, job_id, url_source):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM seen_jobs WHERE job_id = ? AND url_source = ?",
                (job_id, url_source)
            )
            return cursor.fetchone() is None

    def mark_job_as_seen(
        self,
        job_id,
        url_source,
        title,
        budget,
        proposals,
        location,
        total_spent,
        description,
        job_type,
        experience_level,
        duration,
        published_time,
        skills
    ):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO seen_jobs
                    (
                        job_id, url_source, title, budget, proposals, location,
                        total_spent, description, job_type, experience_level,
                        duration, published_time, skills, first_seen
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id, url_source, title, budget, proposals, location,
                    total_spent, description, job_type, experience_level,
                    duration, published_time, skills, datetime.datetime.now()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"❌ Database Error: {e}")

    def cleanup_old_jobs(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM seen_jobs WHERE first_seen < datetime('now', '-30 days')")
                conn.commit()
                logger.info("🧹 Database cleanup complete.")
        except Exception as e:
            logger.error(f"❌ Database Cleanup Error: {e}")
