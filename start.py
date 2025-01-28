from subprocess import Popen

commands = [
	'python zbxmon.py',
	'python processing.py'
]

# run in parallel
processes = [Popen(cmd, shell=True) for cmd in commands]

for p in processes: p.wait()




	
