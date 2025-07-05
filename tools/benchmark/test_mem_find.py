
import time
import psutil
import xutils
from xutils import textutil
import gc

def create_name(id=0):
    return str(id).rjust(20, "0")

def find_in_row_dict_memory(size=10000, target_id=1):
    """row = dict(id = id, column_name = column_value)
    """
    gc.collect()
    target = create_name(target_id)
    p = psutil.Process()
    start_memory = p.memory_info().rss

    result = []
    for id in range(1, size+1):
        name = create_name(id)
        item = dict(id = id, name = name)
        result.append(item)
    
    cost_memory = p.memory_info().rss - start_memory
    print(f"size: {size}, used memory: {xutils.format_size(cost_memory)}")

    start_time = time.time()
    print("start search...")
    for item in result:
        if item.get("name") == target:
            break
    
    cost_time = time.time() - start_time
    print(f"finish search, cost {cost_time:.4} seconds")

def find_in_row_tuple_memory(size=10000, target_id=1):
    """row = (id, column_value)
    """
    gc.collect()
    target = create_name(target_id)
    p = psutil.Process()
    start_memory = p.memory_info().rss

    result = []
    for id in range(1, size+1):
        name = create_name(id)
        item = (id, name)
        result.append(item)
    
    cost_memory = p.memory_info().rss - start_memory
    print(f"size: {size}, used memory: {xutils.format_size(cost_memory)}")

    start_time = time.time()
    print("start search...")
    for item in result:
        if item[1] == target:
            break
    
    cost_time = time.time() - start_time
    print(f"finish search, cost {cost_time:.4} seconds")

def find_in_column_dict_memory(size=10000, target_id=1):
    """row = dict(column_value = id)
    """
    gc.collect()
    target = create_name(target_id)
    p = psutil.Process()
    start_memory = p.memory_info().rss

    name_dict = {}

    for id in range(1, size+1):
        name = create_name(id)
        name_dict[name] = id
    
    for name, id in name_dict.items():
        print(name, id)
        break

    print(f"name_dict.size = {len(name_dict)}")
    cost_memory = p.memory_info().rss - start_memory
    print(f"size: {size}, used memory: {xutils.format_size(cost_memory)}")

    start_time = time.time()
    print("start search...")
    for name in name_dict:
        if name == target:
            target_id = name_dict[name]
            break
    
    cost_time = time.time() - start_time
    print(f"finish search, cost {cost_time:.4} seconds")

def find_in_index_list_memory(size=10000, target_id=1):
    """row = [column_value_1, row_id_1, column_value_2, row_id_2]
    """
    gc.collect()
    target = create_name(target_id)
    p = psutil.Process()
    start_memory = p.memory_info().rss

    index_list = []

    for id in range(1, size+1):
        name = create_name(id)
        index_list.append(name)
        index_list.append(id)

    print(f"index_list.size = {len(index_list)}")
    
    cost_memory = p.memory_info().rss - start_memory
    print(f"size: {size}, used memory: {xutils.format_size(cost_memory)}")

    start_time = time.time()
    print("start search...")
    for index in range(0, len(index_list), 2):
        col_value = index_list[index]
        id_value = index_list[index+1]
        if col_value == target:
            target_id = id_value
            break
    
    cost_time = time.time() - start_time
    print(f"finish search, cost {cost_time:.4} seconds")

def print_head(head: str):
    print("")
    print(head.center(60, "="))

if __name__ == "__main__":
    print_head("find_in_row_dict_memory")
    # memory: 2.92M time: 0.0015 seconds
    find_in_row_dict_memory(10000, -1)
    # memory: 28.66M time: 0.00252 seconds
    find_in_row_dict_memory(10_0000, -1)
    # memory: 297.07M time: 0.0282 seconds
    find_in_row_dict_memory(100_0000, -1)
    # memory: 595.35M time: 0.06012 seconds
    find_in_row_dict_memory(200_0000, -1)

    print_head("find_in_row_tuple_memory")
    # memory: 352.00K time: 0.0015 seconds
    find_in_row_tuple_memory(10000, -1)
    # memory: 16.59M time: 0.00252 seconds
    find_in_row_tuple_memory(10_0000, -1)
    # memory: 174.63M time: 0.0282 seconds
    find_in_row_tuple_memory(100_0000, -1)
    # memory: 351.18M time: 0.06012 seconds
    find_in_row_tuple_memory(200_0000, -1)

    print_head("find_in_column_dict_memory")
    # memory: 32.00K time: 0.001508 seconds
    find_in_column_dict_memory(10000, -1)
    # memory: 15.95M time: 0.001002 seconds
    find_in_column_dict_memory(10_0000, -1)
    # memory: 135.36M time: 0.01061 seconds
    find_in_column_dict_memory(100_0000, -1)
    # memory: 270.32M time: 0.02495 seconds
    find_in_column_dict_memory(200_0000, -1)

    print_head("find_in_index_list_memory")
    # memory: 564.00K
    find_in_index_list_memory(10000, -1)
    # memory: 14.42M
    find_in_index_list_memory(10_0000, -1)
    # memory: 121.44M
    find_in_index_list_memory(100_0000, -1)
    # memory: 243.84M
    find_in_index_list_memory(200_0000, -1)