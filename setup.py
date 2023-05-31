import os, sys, time

# I got this off the internet a year and a half ago ago, I can't site the source but I **did not** write this
def setup():
	var = sys.version_info

	if int(var[0]) >= 3:
		if sys.platform == "linux":
			try:
				import pygame
			except:
				print("INSTALLING PIP")
				os.system("pip3 install --upgrade pip")
				print("INSTALLING PYGAME")
				os.system("python3.9 -m pip install -U pygame --user")

		elif sys.platform == "darwin":
			try:
				import pygame
			except:
				print("PLEASE INPUT YOUR PASSWORD TO INSTALL REQUIRED MODULES")
				print("INSTALLING PIP")
				os.console("pip install --upgrade pip")
				print("INSTALLING PYGAME")
				os.console("sudo python3.9 -m pip install -U pygame --user")

		elif sys.platform == "win32":
			try:
				import pygame
			except:
				print("INSTALLING PIP")
				os.system("pip3 install --upgrade pip")
				print("INSTALLING PYGAME")
				os.system("python -m pip install -U pygame --user")
	else:
		print("Python Version is out of date, please update python version to a version newer than Python 3.0.0 and restart")
		time.sleep(10)
		sys.exit()




