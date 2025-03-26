import os
 
# Read output line by line

with os.popen("df -h") as f:

    for line in f.readlines():

        print(line.strip())
 
# Run a shell command and capture output

output = os.popen("uname -a").read()

print(output)
 
