import pandas as pd

data = pd.read_csv(sensor_data.csv)

avg_temp = data("Temperature").mean

print(avg_temp)

