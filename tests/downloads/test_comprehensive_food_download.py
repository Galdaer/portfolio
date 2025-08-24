#!/usr/bin/env python3
"""
Test the comprehensive food download functionality
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

async def test_comprehensive_food_download():
    """Test the comprehensive food download functionality"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test config
    config = TestConfig()
    
    print("🧪 Testing comprehensive food download from USDA FoodData Central")
    print(f"📁 Data directory: {config.get_health_info_data_dir()}")
    
    # Check if we have the API key
    usda_api_key = os.getenv("USDA_API_KEY")
    if not usda_api_key:
        print("⚠️ USDA_API_KEY not found - download will use fallback data")
    else:
        print(f"🔑 Using USDA API key: {usda_api_key[:10]}...")
    
    async with HealthInfoDownloader(config) as downloader:
        print("\\n📥 Starting comprehensive food download...")
        foods = await downloader._download_usda_food_data()
        
        print(f"\\n✅ Download completed!")
        print(f"📊 Total foods downloaded: {len(foods)}")
        
        if foods:
            print(f"📝 Sample food: {foods[0]['description']} ({foods[0].get('food_category', 'N/A')})")
            
            # Show unique categories and data types
            categories = set(food.get('food_category', 'Unknown') for food in foods)
            sources = set(food.get('source', 'Unknown') for food in foods)
            
            print(f"🏷️ Unique food categories: {len(categories)} ({', '.join(sorted(categories)[:10])}...)")
            print(f"📋 Data sources: {len(sources)} ({', '.join(sorted(sources))})") 
        
        # Get download stats
        stats = downloader.get_download_stats()
        print(f"\\n📈 Download statistics:")
        print(f"  - API requests made: {stats['requests_made']}")
        print(f"  - Food items downloaded: {stats['food_items_downloaded']}")
        if stats.get('errors'):
            print(f"  - Errors encountered: {stats['errors']}")
    
    # Save foods to JSON file for inspection
    output_file = Path(config.get_health_info_data_dir()) / "all_foods_comprehensive.json"
    with open(output_file, 'w') as f:
        json.dump({
            "metadata": {
                "dataset_type": "food_items",
                "total_items": len(foods),
                "download_timestamp": stats.get('start_time'),
                "api_requests_made": stats.get('requests_made', 0),
                "source": "usda_comprehensive_strategy"
            },
            "food_items": foods
        }, f, indent=2, default=str)
    
    print(f"💾 Results saved to: {output_file}")
    
    return foods

if __name__ == "__main__":
    foods = asyncio.run(test_comprehensive_food_download())
    print(f"\\n🎉 Test completed with {len(foods)} foods!")