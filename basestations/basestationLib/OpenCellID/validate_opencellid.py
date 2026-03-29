# import scienceplots
import matplotlib.pyplot as plt

# plt.style.use(['science', 'ieee'])

import numpy as np
import pandas as pd


file_opencellid = "Countries/Belgium/flanders/Ghent_opencellid.csv"
file_government = "Countries/Belgium/flanders/Antennes_Gent.csv"
df_opencellid = pd.read_csv(file_opencellid)
df_government = pd.read_csv(file_government)



# MAKE A PLOT With locations of csv_opencellid vs csv_government
latitudes_opencellid = df_opencellid['lat']
longitudes_opencellid = df_opencellid['lon']

latitudes_government = df_government['Latitude']
longitudes_government = df_government['Longitude']

plt.figure()
plt.plot(longitudes_opencellid, latitudes_opencellid, 'ro', label='OpenCellID')
plt.plot(longitudes_government, latitudes_government, 'bx', label='Government')
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.grid(True)
plt.title("Locations of OpenCellID vs Government")
plt.legend()
plt.show()


