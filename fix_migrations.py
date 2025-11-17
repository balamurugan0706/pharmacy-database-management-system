from app import app, db
from sqlalchemy import text

def fix_alembic_version():
    with app.app_context():
        try:
            # First, check if alembic_version table exists
            check_table = text("SHOW TABLES LIKE 'alembic_version'")
            result = db.session.execute(check_table)
            if not list(result):
                # Create alembic_version table if it doesn't exist
                create_table = text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
                db.session.execute(create_table)
                db.session.commit()
                print("Created alembic_version table")

            # Update to current revision
            update_version = text("TRUNCATE TABLE alembic_version")
            db.session.execute(update_version)
            insert_version = text("INSERT INTO alembic_version (version_num) VALUES ('current_schema')")
            db.session.execute(insert_version)
            db.session.commit()
            print("Updated alembic_version to current_schema")

        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_alembic_version()