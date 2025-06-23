#!/usr/bin/env python3
"""
Test script to verify the bot setup and command registration
"""
import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_command_registration():
    """Test that we can create a bot and register commands"""
    print("🧪 Testing command registration...")
    
    # Create a minimal bot instance
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    # Test command registration
    @bot.tree.command(name="test_command", description="A test command")
    async def test_command(interaction: discord.Interaction):
        await interaction.response.send_message("Test successful!")
    
    # Test our sync utility
    try:
        from utils.command_sync import sync_commands
        print("✅ Command sync utility imported successfully")
        
        # Note: We can't actually sync without connecting to Discord
        print("✅ Command registration test passed")
        
    except ImportError as e:
        print(f"❌ Failed to import command sync utility: {e}")
        return False
    except Exception as e:
        print(f"❌ Command registration test failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration setup"""
    print("🧪 Testing configuration...")
    
    try:
        from config import Config
        print("✅ Config module imported successfully")
        
        # Test that directories are created
        required_dirs = [Config.STATE_DIR, Config.LOGS_DIR, Config.CHARACTERS_DIR, Config.COMBAT_DIR]
        for dir_path in required_dirs:
            if os.path.exists(dir_path):
                print(f"✅ Directory exists: {dir_path}")
            else:
                print(f"❌ Directory missing: {dir_path}")
                return False
        
        print("✅ Configuration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_state_manager():
    """Test state manager with error handling"""
    print("🧪 Testing state manager...")
    
    try:
        from utils.state_manager import load_state, save_state
        
        # Test with a dummy session
        test_session = "test_session_123"
        test_data = {"test": "data", "number": 42}
        
        # Test save
        save_state(test_session, test_data)
        print("✅ State save test passed")
        
        # Test load
        loaded_data = load_state(test_session)
        if all(loaded_data.get(k) == v for k, v in test_data.items()):
            print("✅ State load test passed")
        else:
            print(f"❌ State load test failed: {loaded_data} != {test_data}")
            return False
        
        # Cleanup
        import os
        test_file = os.path.join(os.path.dirname(__file__), 'state', f'{test_session}.json')
        if os.path.exists(test_file):
            os.remove(test_file)
        
        print("✅ State manager test passed")
        return True
        
    except Exception as e:
        print(f"❌ State manager test failed: {e}")
        return False

def test_pending_roll_detection():
    print("🧪 Testing pending roll detection...")
    try:
        from services.openai_service import detect_roll_request
        text = "The goblin growls. Roll a d20, you need 15 or higher."
        pending = detect_roll_request(text, "123")
        if pending and pending['type'] in ('d20', '1d20') and pending.get('dc') == 15 and pending['player_id'] == '123':
            print("✅ Pending roll detected correctly")
            return True
        print(f"❌ Pending roll incorrect: {pending}")
        return False
    except Exception as e:
        print(f"❌ Pending roll test failed: {e}")
        return False

def test_attack_resolution():
    print("🧪 Testing attack resolution...")
    try:
        from utils.combat_manager import start_combat, attack, end_combat, roll_initiative
        channel = 'test_chan'
        start_combat(channel, [('1', 'Hero')], [{'name':'Goblin','hp':5,'ac':10}])
        roll_initiative(channel)
        result = attack(channel, '1', 'Goblin', 5, '1d4')
        end_combat(channel)
        if result and 'hit' in result:
            print("✅ Attack function executed")
            return True
        print("❌ Attack function failed")
        return False
    except Exception as e:
        print(f"❌ Attack test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting bot setup verification...\n")
    
    tests = [
        ("Configuration", test_config),
        ("State Manager", test_state_manager),
        ("Command Registration", test_command_registration),
        ("Pending Roll", test_pending_roll_detection),
        ("Attack", test_attack_resolution),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} Test ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
                
        except Exception as e:
            print(f"❌ {test_name} test FAILED with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bot setup is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    asyncio.run(main())
