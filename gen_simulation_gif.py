import sys
from topology import City

if __name__ == "__main__":
    cars = int(sys.argv[1]) 
    rank = int(sys.argv[2]) 
    steps = int(sys.argv[3]) 

    c = City(cars, rank)
    c.save_simualtion_gif(steps)