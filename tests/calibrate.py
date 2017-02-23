import sys
import profile

pr = profile.Profile()
res = []
N = int(sys.argv[1]) if sys.argv[1:] else 100000

for i in range(5):
    res.append(pr.calibrate(N))
    print(res[-1])

print("Avg:", sum(res) / len(res))
