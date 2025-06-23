import os
import shutil

def cleanup_project():
    """Remove empty and unused files"""
    print("🧹 Starting project cleanup...")
    
    files_to_remove = [
        'startup.py', 
        'slash_commands.py', 
        'docker-compose.yml',
        'discord_bot_improved.py', 
        'deploy.py', 
        'config.py',
        'README_UPDATED.md', 
        'MIGRATION_GUIDE.md', 
        'Dockerfile',
        '.env.template', 
        'tests.py'
    ]
    
    dirs_to_remove = ['.github', '.qodo']
    
    removed_files = []
    removed_dirs = []
    
    # Remove empty/unused files
    for file in files_to_remove:
        if os.path.exists(file):
            try:
                os.remove(file)
                removed_files.append(file)
                print(f"✅ Removed: {file}")
            except Exception as e:
                print(f"❌ Failed to remove {file}: {e}")
        else:
            print(f"⚠️ File not found: {file}")
    
    # Remove directories
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                removed_dirs.append(dir_name)
                print(f"✅ Removed directory: {dir_name}")
            except Exception as e:
                print(f"❌ Failed to remove directory {dir_name}: {e}")
        else:
            print(f"⚠️ Directory not found: {dir_name}")
    
    print(f"\n📊 Cleanup Summary:")
    print(f"   Files removed: {len(removed_files)}")
    print(f"   Directories removed: {len(removed_dirs)}")
    
    if removed_files or removed_dirs:
        print("✅ Project cleanup completed successfully!")
    else:
        print("ℹ️ No files or directories needed cleanup.")

if __name__ == "__main__":
    cleanup_project()
