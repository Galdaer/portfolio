#!/usr/bin/env python3
"""
Test script to verify multi-core parser optimization
Run this to see CPU utilization across all cores
"""

import asyncio
import multiprocessing as mp
import os
import sys
import time

from pubmed.parser_optimized import OptimizedPubMedParser

# Add the src directory to Python path
sys.path.insert(0, "/app/src")


async def test_multicore_parsing():
    """Test multi-core XML parsing performance"""
    print("Testing multi-core PubMed parser")
    print(f"💻 Available CPU cores: {mp.cpu_count()}")

    # Find XML files in the data directory
    data_dir = "/app/data/pubmed"
    xml_files = []

    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename.endswith(".xml.gz"):
                xml_files.append(os.path.join(data_dir, filename))

    if not xml_files:
        print(f"❌ No XML files found in {data_dir}")
        return

    print(f"📁 Found {len(xml_files)} XML files to test with")

    # Test with different worker counts
    for worker_count in [1, mp.cpu_count()]:
        print(f"\n🧪 Testing with {worker_count} workers...")
        parser = OptimizedPubMedParser(max_workers=worker_count)

        start_time = time.time()

        # Parse all files
        results = await parser.parse_xml_files_parallel(xml_files[:3])  # Test with 3 files max

        end_time = time.time()
        duration = end_time - start_time

        total_articles = sum(len(articles) for articles in results.values())

        print(f"⚡ {worker_count} workers: {total_articles} articles in {duration:.2f}s")
        print(f"📊 Rate: {total_articles / duration:.0f} articles/second")

        if worker_count == 1:
            single_core_time = duration
        elif worker_count == mp.cpu_count():
            speedup = single_core_time / duration
            print(f"🚀 Speedup: {speedup:.2f}x faster with multi-core!")


if __name__ == "__main__":
    print("🔥 Multi-Core PubMed Parser Performance Test")
    print("Monitor CPU usage with: htop or top")
    print("You should see all CPU cores utilized during parsing!\n")

    asyncio.run(test_multicore_parsing())
