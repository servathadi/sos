
import os
import shutil
from pathlib import Path

SOURCE_DIR = Path("/Users/hadi/Development/Mumega/FRC2/Papers/16D")
DEST_DIR = Path("/Users/hadi/Development/Mumega/sos/docs/docs/frc/16d")

def migrate_papers():
    if not SOURCE_DIR.exists():
        print(f"Source dir {SOURCE_DIR} not found!")
        return

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # We want 16D.001 through 16D.050 and 16D.331
    files_moved = 0
    for filename in os.listdir(SOURCE_DIR):
        if filename.endswith(".md") and filename.startswith("16D."):
            # Simple filter to avoid copying huge master files or temp files
            if "Master" in filename: 
                continue
                
            src_file = SOURCE_DIR / filename
            dest_file = DEST_DIR / filename
            
            # Read content to check/add frontmatter
            with open(src_file, 'r') as f:
                content = f.read()
            
            # Simple check if Docusaurus frontmatter exists, if not add it
            if not content.startswith("---"):
                title = filename.replace(".md", "")
                frontmatter = f"---\ntitle: {title}\n---\n\n"
                content = frontmatter + content
                
            with open(dest_file, 'w') as f:
                f.write(content)
                
            print(f"Migrated: {filename}")
            files_moved += 1

    print(f"Total papers migrated: {files_moved}")

if __name__ == "__main__":
    migrate_papers()
