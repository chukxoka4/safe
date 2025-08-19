import psutil
import time

def monitor(interval=1, duration=120):
    print("timestamp,cpu_percent,mem_percent")
    for _ in range(int(duration / interval)):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        print(f"{time.time()},{cpu},{mem}")
        time.sleep(interval)

if __name__ == "__main__":
    monitor()