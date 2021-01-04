import os
import sys
from simulation import City

if __name__ == "__main__":
    cars = int(sys.argv[1]) 
    rank = int(sys.argv[2]) 
    steps = int(sys.argv[3]) 

    gif_file_name = f"sim_{cars}_{rank}_{steps}.gif"

    c = City(cars, rank)
    c.save_simulation_with_graphics(steps, gif_file_name)

    os.system(f'ffmpeg -i {gif_file_name} -movflags faststart -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" sim_{cars}_{rank}_{steps}.mp4')