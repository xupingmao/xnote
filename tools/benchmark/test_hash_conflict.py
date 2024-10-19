import hashlib
import random

def get_md5_hex(str_value: str):
    md5 = hashlib.md5()
    md5.update(str_value.encode('utf-8'))
    return md5.hexdigest()

def get_sha256_hex(str_value: str):
    hash = hashlib.sha256()
    hash.update(str_value.encode('utf-8'))
    return hash.hexdigest()

def get_sha1_hex(str_value: str):
    hash = hashlib.sha1()
    hash.update(str_value.encode('utf-8'))
    return hash.hexdigest()

def test_hash_conflict(loops: int, hash_func = get_md5_hex):
    dup_dict = dict()

    loop = 0
    value = 0
    while loop < loops:
        loop += 1
        # value += random.randint(1, 1000)
        value += 1
        int_str = str(value)
        hash_hex = hash_func(int_str)
        if loop < 10:
            print(f'int: {int_str}, hash_hex: {hash_hex}')

        if not hash_hex.startswith("5f"):
            continue

        dup_result = dup_dict.get(hash_hex)

        if dup_result != None:
            dup_result.append(int_str)
            print(f"dup values: {dup_result}, hash_hex: {hash_hex}")
        else:
            dup_result = [int_str]
        
        dup_dict[hash_hex] = dup_result


if __name__ == "__main__":
    test_hash_conflict(20000_0000, hash_func=get_md5_hex)

