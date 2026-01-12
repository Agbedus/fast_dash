import json
from typing import Optional, List
from sqlmodel import SQLModel, Field, create_engine, Session

class MockNote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    tags: Optional[str] = None

def test_serialization():
    # Simulate what happens in the endpoint
    note_data = {
        "title": "Test Note",
        "tags": ["tag1", "tag2", "tag3"]
    }
    
    # Original state that caused the error (simulated)
    # note = MockNote(**note_data) # This would pass if the DB wasn't involved, but MySQL would fail
    
    # Applied fix
    if "tags" in note_data and isinstance(note_data["tags"], list):
        note_data["tags"] = json.dumps(note_data["tags"])
    
    note = MockNote(**note_data)
    print(f"Serialized tags: {note.tags}")
    assert isinstance(note.tags, str)
    assert note.tags == '["tag1", "tag2", "tag3"]'
    print("Verification SUCCESS: Tags are correctly serialized to a JSON string.")

if __name__ == "__main__":
    test_serialization()
