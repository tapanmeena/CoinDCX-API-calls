import threading
import time
i = 1
def printFunction2():
    global i
    index = 1
    while index != 300:
        index += 1
        time.sleep(20)
        i += 1
        print ("from func2: ",i)

def func1():
    global i,a
    index = 1
    while index != 300:
        index += 1
        time.sleep(10)
        i += 1
        print ("from func1: ",i)
        print ("aa: ",a)
a = 1
b = 2

def takeInput():
    global a,b
    while True:
        a = int(input("input from a: "))
        b = int(input("input from b: "))

if __name__ == "__main__":
    t1 = threading.Thread(target=takeInput)
    t2 = threading.Thread(target=func1)
  
    # starting thread 1
    t1.start()
    # starting thread 2
    t2.start()
    t2.join()
    t1.join()
    # wait until thread 1 is completely executed
    # t1.join()
    # wait until thread 2 is completely executed
    # t2.join()