#!/usr/bin/env python3
"""
Test the comprehensive exercise download functionality
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, '/home/intelluxe/services/user/medical-mirrors/src')

from config import Config
from health_info.downloader import HealthInfoDownloader

# Override the DATA_DIR for testing
class TestConfig(Config):
    def __init__(self, data_dir: str = "/home/intelluxe/test_health_data"):
        super().__init__()
        self.DATA_DIR = data_dir
        
    def get_health_info_data_dir(self) -> str:
        """Get health information data directory"""
        path = f"{self.DATA_DIR}/health_info"
        os.makedirs(path, exist_ok=True)
        return path

async def test_comprehensive_exercise_download():
    """Test the comprehensive exercise download functionality"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test config
    config = TestConfig()
    
    print("🧪 Testing comprehensive exercise download from ExerciseDB")
    print(f"📁 Data directory: {config.get_health_info_data_dir()}")
    
    # Check if we have the API key
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        print("⚠️ RAPIDAPI_KEY not found - download will use fallback data")
    else:
        print(f"🔑 Using RapidAPI key: {rapidapi_key[:10]}...")
    
    async with HealthInfoDownloader(config) as downloader:
        print("\n📥 Starting comprehensive exercise download...")
        exercises = await downloader._download_exercise_data()
        
        print(f"\n✅ Download completed!")
        print(f"📊 Total exercises downloaded: {len(exercises)}")
        
        if exercises:
            print(f"📝 Sample exercise: {exercises[0]['name']} ({exercises[0]['body_part']})")
            
            # Show unique body parts, equipment, and targets
            body_parts = set(ex['body_part'] for ex in exercises)
            equipment = set(ex['equipment'] for ex in exercises)  
            targets = set(ex['target'] for ex in exercises)
            
            print(f"🎯 Unique body parts: {len(body_parts)} ({', '.join(sorted(body_parts))})")
            print(f"🏋️ Unique equipment: {len(equipment)} ({', '.join(sorted(equipment))})")
            print(f"💪 Unique targets: {len(targets)} ({', '.join(sorted(targets))})")
        
        # Get download stats
        stats = downloader.get_download_stats()
        print(f"\n📈 Download statistics:")
        print(f"  - API requests made: {stats['requests_made']}")
        print(f"  - Exercises downloaded: {stats['exercises_downloaded']}")
        if stats.get('errors'):
            print(f"  - Errors encountered: {stats['errors']}")
    
    # Save exercises to JSON file for inspection
    output_file = Path(config.get_health_info_data_dir()) / "all_exercises_comprehensive.json"
    with open(output_file, 'w') as f:
        json.dump({
            "metadata": {
                "total_exercises": len(exercises),
                "download_timestamp": stats.get('start_time'),
                "api_requests_made": stats.get('requests_made', 0),
                "source": "exercisedb_comprehensive_strategy"
            },
            "exercises": exercises
        }, f, indent=2, default=str)
    
    print(f"💾 Results saved to: {output_file}")
    
    return exercises

if __name__ == "__main__":
    exercises = asyncio.run(test_comprehensive_exercise_download())
    print(f"\n🎉 Test completed with {len(exercises)} exercises!")