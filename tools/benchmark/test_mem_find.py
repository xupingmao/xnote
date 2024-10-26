
import time
import psutil
import xutils
from xutils import textutil

def find_dict_in_memory(size=10000, target=1):
    p = psutil.Process()
    start_memory = p.memory_info().rss

    result = []
    for id in range(1, size+1):
        item = dict(id = id, name = textutil.random_string(20))
        result.append(item)
    
    cost_memory = p.memory_info().rss - start_memory
    print(f"size: {size}, used memory: {xutils.format_size(cost_memory)}")

    start_time = time.time()
    print("start search...")
    for item in result:
        if item.get("id") == target:
            break
    
    cost_time = time.time() - start_time
    print(f"finish search, cost {cost_time:.4} seconds")

if __name__ == "__main__":
    # memory: 2.92M time: 0.0015 seconds
    find_dict_in_memory(10000, 10000)
    # memory: 28.66M time: 0.00252 seconds
    find_dict_in_memory(10_0000, 10_0000)
    # memory: 297.07M time: 0.0282 seconds
    find_dict_in_memory(100_0000, 100_0000)
