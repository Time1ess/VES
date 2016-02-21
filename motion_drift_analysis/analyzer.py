# coding: UTF-8

src_file = open("data.txt", "r")
dst_file = open("cleaned_data.txt", "w")

for line in src_file.readlines():
    if line.startswith("A:"):
        dst_file.write(line)
src_file.close()
dst_file.close()
import re
src_file = open("cleaned_data.txt", "r")
data = [[], [], []]
for line in src_file.readlines():
    m = re.match(r"A:\s(.+)\sB:\s(.+)\sC:\s(.+)", line)
    data[0].append((float(m.group(1))+360) % 360)
    data[1].append((float(m.group(2))+360) % 360)
    data[2].append((float(m.group(3))+360) % 360)

src_file.close()
# Do something with data
PRECISION = 5
dmax = [0, 0, 0]
dmin = [0, 0, 0]
davr = [0, 0, 0]
dmax = [max(data[0]), max(data[1]), max(data[2])]
dmin = [min(data[0]), min(data[1]), min(data[2])]
davr[0] = sum(data[0])/len(data[0])
davr[1] = sum(data[1])/len(data[1])
davr[2] = sum(data[2])/len(data[2])
print "MAX - MIN"
print map(lambda i: round(dmax[i]-dmin[i], PRECISION), xrange(3))
print "AVR"
print map(lambda x: round(x, PRECISION), davr)
print "MAX - AVR"
print map(lambda i: round(dmax[i]-davr[i], PRECISION), xrange(3))
print "AVR - MIN"
print map(lambda i: round(davr[i]-dmin[i], PRECISION), xrange(3))
