"""
Migration script to update notes table schema
"""
from sqlmodel import SQLModel, create_engine, text
from app.db.session import engine
from app.models import Note, NoteShare

def migrate_notes_table():
    print("--- Migrating Notes Table ---")
    
    with engine.connect() as conn:
        # Drop old tables
        print("Dropping old note_shares table if exists...")
        conn.execute(text("DROP TABLE IF EXISTS note_shares"))
        
        print("Dropping old notes table...")
        conn.execute(text("DROP TABLE IF EXISTS notes"))
        
        conn.commit()
    
    # Recreate with new schema
    print("Creating notes and note_shares tables with new schema...")
    SQLModel.metadata.create_all(engine)
    
    print("✓ Migration completed successfully!")
    print("\nNew Note schema:")
    print("- id, title, content, type, tags")
    print("- is_pinned, is_archived, is_favorite, cover_image")
    print("- created_at, updated_at")
    print("- user_id (FK), task_id (FK)")
    print("- shared_with: many-to-many via note_shares table")

if __name__ == "__main__":
    migrate_notes_table()
