from random import random

def monte_carlo(times):
    hit_sum = 0
    i = 0
    for i in range(times):
        x = random()
        y = random()
        if x*x + y*y <= 1:
            hit_sum += 1
    pi = hit_sum / times * 4
    return pi

def test():
    print(monte_carlo(1000000))
    
    
if __name__ == "__main__":
    print("montekaro")
    for i in range(10):
        test()