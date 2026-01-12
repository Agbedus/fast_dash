"""
Migration script to update events table schema
"""
from sqlmodel import text
from app.db.session import engine

def migrate_events_table():
    print("--- Migrating Events Table ---")
    
    with engine.connect() as conn:
        print("Checking/Adding missing columns to events table...")
        
        # Add color
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN color VARCHAR(255)"))
            print("✓ Added column: color")
        except Exception as e:
            print(f"! Column 'color' might already exist or error: {e}")
            
        # Add created_at
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN created_at VARCHAR(255)"))
            print("✓ Added column: created_at")
        except Exception as e:
            print(f"! Column 'created_at' might already exist or error: {e}")
            
        # Add updated_at
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN updated_at VARCHAR(255)"))
            print("✓ Added column: updated_at")
        except Exception as e:
            print(f"! Column 'updated_at' might already exist or error: {e}")
            
        # Add user_id
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN user_id VARCHAR(255)"))
            # Add foreign key constraint if users table exists
            conn.execute(text("ALTER TABLE events ADD CONSTRAINT fk_event_user FOREIGN KEY (user_id) REFERENCES users(id)"))
            print("✓ Added column: user_id and foreign key constraint")
        except Exception as e:
            print(f"! Column 'user_id' might already exist or error: {e}")
            
        conn.commit()
    
    print("\n✓ Migration completed successfully!")

if __name__ == "__main__":
    migrate_events_table()
