import matplotlib.pyplot as plt
import numpy as np

# a = np.loadtxt('losses.csv').T
a = np.loadtxt('losses_single.csv').T

plt.plot(a[0])
plt.show()
plt.plot(a[1])
plt.show()
plt.plot(a[2])
plt.show()
plt.plot(a[3])
plt.show()