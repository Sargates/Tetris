from copy import deepcopy
from enum import Enum, auto
from utilities.signaledge import SignalEdge; from utilities.repeatedPrint import RepeatedPrint as RP
import random, pygame as pg, math, datetime, json, pprint
from pygame import Vector2

RP.formattedRP()

# 
# Tetris, by Nick Gates, 5/31/23
# Requires Pygame package, setup.py included
# 

pg.init()
class Game:
	#	    0      90    180    270
	# I : 03840  08738  00240  17476
	# J : 02272  01604  00226  01100
	# L : 00736  01094  00232  03140
	# O : 01632  01632  01632  01632
	# S : 01728  01122  00108  02244
	# T : 01248  01124  00228  01220
	# Z : 03168  00612  00198  01224

	"""
	Pieces are encoded like this:
	Imagine a 4x4 grid of cells, each cell is either filled or not, 2^16 bits can represent any combination like this
	Because there are only 4 rotations of a given type of piece (i.e. 'I', 'J', 'T', etc.), any and every piece can
	be given a "meta id" based on which 4 of the 16 bits are active. Any rotation of a piece is just a permutation 
	of those 4 bits. Things like color can be deduced by using a hashmap. The x and y components for the anchor of
	the active piece describe the top left of the 4x4 grid of cells. Hopefully that makes sense.
	"""
	
	# tests if audio devices are attached to machine
	canPlayMusic = True
	try:
		pg.mixer.init()
	except:
		canPlayMusic = False
	if canPlayMusic:
		themeSong = pg.mixer.Sound("./assets/mainTheme.ogg")
		themeSong.set_volume(0.05)
		popSound = pg.mixer.Sound("./assets/pop.ogg")
		popSound.set_volume(0.02)
		gameoverMusic = pg.mixer.Sound("./assets/gameover.ogg")
		gameoverMusic.set_volume(0.03)

	typeAndRotToMeta = {
		"I" : {
			"0": 3840,
			"R": 8738,
			"2": 240,
			"L": 17476,
		},
		"J" : {
			"0": 2272,
			"R": 1604,
			"2": 226,
			"L": 1100,
		},
		"L" : {
			"0": 736,
			"R": 1094,
			"2": 232,
			"L": 3140,
		},
		"O" : {
			"0": 1632,
			"R": 1632,
			"2": 1632,
			"L": 1632,
		},
		"S" : {
			"0": 1728,
			"R": 1122,
			"2": 108,
			"L": 2244,
		},
		"T" : {
			"0": 1248,
			"R": 1124,
			"2": 228,
			"L": 1220,
		},
		"Z" : {
			"0": 3168,
			"R": 612,
			"2": 198,
			"L": 1224,
		}
	}
	typeList = ["I", "J", "L", "O", "S", "T", "Z"]

	metaIdToActiveBits = {
		3840: [8, 9, 10, 11], 	# I0
		8738: [1, 5, 9, 13],	# IR
		240: [4, 5, 6, 7],		# I2
		17476: [2, 6, 10, 14],	# IL
		
		2272: [5, 6, 7, 11],	# J0
		1604: [2, 6, 9, 10],	# JR
		226: [1, 5, 6, 7],		# J2
		1100: [2, 3, 6, 10],	# JL

		736: [5, 6, 7, 9],		# L0
		1094: [1, 2, 6, 10],	# LR
		232: [3, 5, 6, 7],		# L2
		3140: [2, 6, 10, 11],	# LL

		1632: [5, 6, 9, 10],	# O

		1728: [6, 7, 9, 10],	# S0
		1122: [1, 5, 6, 10],	# SR
		108: [2, 3, 5, 6],		# S2
		2244: [2, 6, 7, 11],	# SL

		1248: [5, 6, 7, 10],	# T0
		1124: [2, 5, 6, 10],	# TR
		228: [2, 5, 6, 7],		# T2
		1220: [2, 6, 7, 10],	# TL

		3168: [5, 6, 10, 11],	# Z0
		612: [2, 5, 6, 9],		# ZR
		198: [1, 2, 6, 7],		# Z2
		1224: [3, 6, 7, 10],	# ZL
	}
	metaIdToTypeAndRot = {}
	for outerK, outerV in typeAndRotToMeta.items():
		for innerK, innerV in outerV.items():
			metaIdToTypeAndRot[innerV] = outerK+innerK
	
	metaIdToXYBounds = {}
	for k, v in metaIdToActiveBits.items():
		minX, maxX, minY, maxY = 4, 0, 4, 0
		for bit in v:
			x = (15 - bit) %  4
			y = (15 - bit) // 4
			if x < minX:
				minX = x
			if x > maxX:
				maxX = x
			if y < minY:
				minY = y
			if y > maxY:
				maxY = y
		metaIdToXYBounds[k] = [minX, maxX, minY, maxY]

	class States(Enum):
		menu = auto()
		countdown = auto()
		playing = auto()
		gameover = auto()
	
	def moveActivePieceHorz(self, dir :int):
		if self.checkPieceCollision(self.anchorX+dir, self.anchorY, self.activePiece):
			return
		self.anchorX += dir

	def placePiece(self):
		minoType, pieceRot = self.metaIdToTypeAndRot[self.activePiece]

		for xComponent, yComponent in list(map(lambda x: ((15-x)%4, (15-x)//4), self.metaIdToActiveBits[self.activePiece])):
			self.gameBoard[self.anchorY+yComponent][self.anchorX+xComponent] = minoType

		minY, maxY = self.metaIdToXYBounds[self.activePiece][2:]
		linesThisPiece = 0
		for i in range(minY, maxY+1):
			for cell in self.gameBoard[self.anchorY+i]:
				if cell == '-':
					break
			else:
				self.gameBoard.pop(self.anchorY+i)
				self.gameBoard.insert(0, ['-' for x in range(10)])
				linesThisPiece += 1
		
		match linesThisPiece:
			case 0:
				self.score += 0
			case 1:
				self.score += 40*((self.totalLines//10)+1)
			case 2:
				self.score += 100*((self.totalLines//10)+1)
			case 3:
				self.score += 300*((self.totalLines//10)+1)
			case 4:
				self.score += 1200*((self.totalLines//10)+1)


		self.totalLines += linesThisPiece
		self.activePiece = self.nextList.pop(0)
		if self.canPlayMusic: self.popSound.play()
		self.addNextPiece()
		self.canHoldPiece = True
		self.anchorX = 3
		self.anchorY = -1

		if self.checkPieceCollision(self.anchorX, self.anchorY, self.activePiece):
			self.state = self.States.gameover

			if self.canPlayMusic: self.themeSong.stop(); self.gameoverMusic.play()
			print(self)
			self.countdownTimer = 4.0
			
	def updateDisplayedBoard(self):
		outBoard = deepcopy(self.gameBoard)
		minoType, pieceRot = self.metaIdToTypeAndRot[self.activePiece]
		for xComponent, yComponent in list(map(lambda x: ((15-x)%4, (15-x)//4), self.metaIdToActiveBits[self.activePiece])):
			outBoard[self.anchorY+yComponent][self.anchorX+xComponent] = minoType

		return outBoard

	def checkPieceCollision(self, anchorX :int, anchorY :int, metaID :int) -> bool:
		"""
		Returns True if collision is detected for given piece ( {metaID} ) at given XY anchor ( {anchorX, anchorY} )
		Falsy condition could be for multiple reasons: cell out of bounds, overlap on filled cell	"""

		if sum(list(map(lambda x: (not (0<=anchorX+((15-x)%4)<10))+(not (0<=anchorY+((15-x)//4)<20)), self.metaIdToActiveBits[metaID]))):
			return True
		for xComponent, yComponent in list(map(lambda x: ((15-x)%4, (15-x)//4), self.metaIdToActiveBits[metaID])):
			if self.gameBoard[anchorY+yComponent][anchorX+xComponent] != '-':
				return True
		return False

	def stepActivePieceDown(self):
		newAnchorY = self.anchorY
		if not self.checkPieceCollision(self.anchorX, newAnchorY+1, self.activePiece):
			# print(newAnchorY)
			self.anchorY = newAnchorY+1
			return
		

		self.placePiece()
	
	def dropActivePieceDown(self):
		newAnchorY = self.anchorY
		while not self.checkPieceCollision(self.anchorX, newAnchorY+1, self.activePiece):
			newAnchorY += 1
		self.anchorY = newAnchorY
		self.placePiece()

	def getNeededKick(self, oldRot, newRot, pieceType):
		if pieceType == "O":
			return (0, 0)
		
		match (oldRot, newRot, pieceType=="I"):
			case ('0', 'R', False): kickTests = [(0, 0), (-1, 0), (-1,+1), ( 0,-2), (-1,-2)]
			case ('R', '0', False): kickTests = [(0, 0), (+1, 0), (+1,-1), ( 0,+2), (+1,+2)]
			case ('R', '2', False): kickTests = [(0, 0), (+1, 0), (+1,-1), ( 0,+2), (+1,+2)]
			case ('2', 'R', False): kickTests = [(0, 0), (-1, 0), (-1,+1), ( 0,-2), (-1,-2)]
			case ('2', 'L', False): kickTests = [(0, 0), (+1, 0), (+1,+1), ( 0,-2), (+1,-2)]
			case ('L', '2', False): kickTests = [(0, 0), (-1, 0), (-1,-1), ( 0,+2), (-1,+2)]
			case ('L', '0', False): kickTests = [(0, 0), (-1, 0), (-1,-1), ( 0,+2), (-1,+2)]
			case ('0', 'L', False): kickTests = [(0, 0), (+1, 0), (+1,+1), ( 0,-2), (+1,-2)]
			case ('0', 'R', True): kickTests = [(0, 0), (-2, 0), (+1, 0), (+1,+2), (-2,-1)]
			case ('R', '0', True): kickTests = [(0, 0), (+2, 0), (-1, 0), (+2,+1), (-1,-2)]
			case ('R', '2', True): kickTests = [(0, 0), (-1, 0), (+2, 0), (-1,+2), (+2,-1)]
			case ('2', 'R', True): kickTests = [(0, 0), (-2, 0), (+1, 0), (-2,+1), (+1,-1)]
			case ('2', 'L', True): kickTests = [(0, 0), (+2, 0), (-1, 0), (+2,+1), (-1,-1)]
			case ('L', '2', True): kickTests = [(0, 0), (+1, 0), (-2, 0), (+1,+2), (-2,-1)]
			case ('L', '0', True): kickTests = [(0, 0), (-2, 0), (+1, 0), (-2,+1), (+1,-2)]
			case ('0', 'L', True): kickTests = [(0, 0), (+2, 0), (-1, 0), (-1,+2), (+2,-1)]

		
		# iterate through each available test
		for xKick, yKick in kickTests:
			# if test does not collide, return
			if not self.checkPieceCollision(self.anchorX+xKick, self.anchorY-yKick, self.typeAndRotToMeta[pieceType][newRot]):
				return (xKick, -yKick)
		return (69, 420) # No tests work, abort rotation

	def rotateActivePiece(self, dir :int):
		pieceType, pieceRot = self.metaIdToTypeAndRot[self.activePiece]

		assert dir in [ 1, -1], "Variable 'dir' must be of type 'int' with value '1' or '-1'"
		match (pieceRot, dir):
			case ('0',  1): newRot = 'R'
			case ('R',  1): newRot = '2'
			case ('R', -1): newRot = '0'
			case ('2',  1): newRot = 'L'
			case ('2', -1): newRot = 'R'
			case ('L',  1): newRot = '0'
			case ('L', -1): newRot = '2'
			case ('0', -1): newRot = 'L'
		
		xKick, yKick = self.getNeededKick(pieceRot, newRot, pieceType)
		if (xKick, yKick) == (69, 420): # No rotation test succeeded, abort
			return
		self.anchorX += xKick; self.anchorY += yKick
		self.activePiece = self.typeAndRotToMeta[pieceType][newRot]
	
	def addNextPiece(self):
		newPieceType = self.typeList[random.randint(0, 6)]
		if self.droughtCounter >= 25:
			newPieceType = "I"
			print("Drought Exceeded")
			self.droughtCounter = 0
		elif newPieceType == "I":
			self.droughtCounter = 0
		else:
			self.droughtCounter += 1

		self.nextList.append(self.typeAndRotToMeta[newPieceType]['0'])

	def holdActivePiece(self):
		if not self.canHoldPiece:
			return
		
		self.anchorX = 3
		self.anchorY = -1
		
		self.canHoldPiece = False
		
		if self.heldPiece == 0:
			self.heldPiece = self.typeAndRotToMeta[self.metaIdToTypeAndRot[self.activePiece][0]]['0']
			self.activePiece = self.nextList.pop(0)
			self.addNextPiece()
			return

		temp = self.typeAndRotToMeta[self.metaIdToTypeAndRot[self.activePiece][0]]['0']
		self.activePiece = self.heldPiece
		self.heldPiece = temp

	def calcShadowPos(self):
		newAnchorY = self.anchorY
		while not self.checkPieceCollision(self.anchorX, newAnchorY+1, self.activePiece):
			newAnchorY += 1
		return newAnchorY

	def __init__(self):
		self.gameBoard :list[list[str]] = [['-' for x in range(10)] for x in range(20)]
		
		
		# self.activePiece = 1124
		self.activePiece :int = self.typeAndRotToMeta[self.typeList[random.randint(0, 6)]]['0']
		self.droughtCounter = 0
		self.nextList = []; self.addNextPiece(); self.addNextPiece(); self.addNextPiece()
		self.canHoldPiece = True
		self.heldPiece = 0
		self.anchorX :int= 3
		self.anchorY :int= -1
		self.totalLines = 0
		self.score = 0
		
		self.state = self.States.countdown
		self.countdownTimer = 3.0
	
	def __str__(self):
		o = ""
		o += f"Total Lines: 	{self.totalLines}\n"
		o += f"Level: 		{self.totalLines//10}\n"
		o += f"Score:		{self.score}"
		return o


class Display:
	pseudoFramesPerSecond = 60
	maxFrameHistory = 5

	pseudoFrameCount :int
	pseudoFrameCountDelta :float
	pseudoFrameCountLastTrigger :int
	fpsHistory :list
	fpsSum :int
	pause :bool
	debug :bool

	# things for key "listener"
	keyFrameCountCache = {}
	background = pg.image.load('./assets/board.png')


	def checkIfKeyShouldExec(self, keycode :int, keys :list[int]):


		if not keys[keycode]  or  (not keycode in self.keyFrameCountCache):
			self.keyFrameCountCache[keycode] = -1
			return False

		
		self.keyFrameCountCache[keycode] += 1

		v = self.keyFrameCountCache[keycode]
		spamFrequency = 4		# in frames
		delayBeforeSpam = 4 	# in frames
		return ((v < 1) or ((v//spamFrequency) > delayBeforeSpam and (v%spamFrequency)//1==0))
	

	def drawLevel(self, game :Game):
		# self.screen.blit(self.levelSurfaceTemplate, self.levelBoxPos)
		levelText = self.levelFont.render("LEVEL: "+ str(game.totalLines//10), 1, (255, 255, 255))
		self.screen.blit(levelText, (195 - levelText.get_width()/2 , 417 - levelText.get_height()/2))

	def drawScore(self, game :Game):
		# self.screen.blit(self.scoreSurfaceTemplate, self.scoreBoxPos)
		scoreText = self.scoreFont.render(str(game.score), 1, (255, 255, 255))
		self.screen.blit(scoreText, (195 - scoreText.get_width()/2 , 656 - scoreText.get_height()/2))

	def drawHold(self, game :Game):
		# self.screen.blit(self.holdSurfaceTemplate, self.holdBoxPos)
		if game.heldPiece != 0:
			for x, y in list(map(lambda x: ((15-x)%4, (15-x)//4), game.metaIdToActiveBits[game.heldPiece])):
				self.screen.blit(
					self.typeToImage[game.metaIdToTypeAndRot[game.heldPiece][0]], (					 # Image 	:pygame.Image
					int(155+(x*40)-(self.nextlistPieceOffsets[game.metaIdToTypeAndRot[game.heldPiece][0]][0])), # X coord 	:int
					int(161+(y*40)-(self.nextlistPieceOffsets[game.metaIdToTypeAndRot[game.heldPiece][0]][1])), # Y coord	:int
					40, 40) 																					 # Image Width, Height :int
				)

	def drawNextList(self, game :Game):
		# self.screen.blit(self.nextlistSurfaceTemplate, self.nextlistBoxPos)
		for i, metaID in enumerate(game.nextList):
			for x, y in list(map(lambda x: ((15-x)%4, (15-x)//4), game.metaIdToActiveBits[metaID])):
				self.screen.blit(
					self.typeToImage[game.metaIdToTypeAndRot[metaID][0]], (								 # Image 	:pygame.Image
					int(960 + (x*40)-(self.nextlistPieceOffsets[game.metaIdToTypeAndRot[metaID][0]][0])), 			 # X coord 	:int
					int(245 + (y*40)-(self.nextlistPieceOffsets[game.metaIdToTypeAndRot[metaID][0]][1])+(165*i)), 	 # Y coord	:int
					40, 40)																						 # Image Width, Height :int
				)


	def drawBoard(self, game :Game):
		board = game.updateDisplayedBoard()
		for j in range(len(board)):
			for i in range(len(board[j])):
				if board[j][i] != '-':
					tup = self.gridToCoord(i, j)
					image = self.typeToImage[board[j][i].upper()]
					self.screen.blit(image, (tup[0], tup[1], 40, 40))

	def drawShadow(self, game :Game):
		shadowAnchorY = game.calcShadowPos()

		pieceType, pieceRot = game.metaIdToTypeAndRot[game.activePiece]
		for cellX, cellY in list(map(lambda x: ((15-x)%4, (15-x)//4), game.metaIdToActiveBits[game.activePiece])):
			x, y = self.gridToCoord(game.anchorX+cellX, shadowAnchorY+cellY)
			self.screen.blit(self.typeToShadowImage[pieceType], (x, y, 40, 40))


	def gridToCoord(self, x, y) -> tuple[int, int]:
		x *= 40
		y *= 40
		x += 400
		y += 50
		tup = (x, y)
		return tup

	def drawFrameRate(self):
		fps = self.fpsSum / self.maxFrameHistory

		font = pg.font.SysFont("Arial", 36)
		fps_text = font.render(f"FPS: {fps:.2f}", 1, (255,255,255))

		self.screen.blit(fps_text, (10, 10))

	def drawWindow(self, game :Game):
		w, h = (self.screen.get_width(), self.screen.get_height())
		self.screen.fill((0, 0, 0))
		match game.state:
			case game.States.playing:
				# self.screen.blit(self.background, (0,0))
				self.drawHold(game)
				self.drawNextList(game)
				self.drawShadow(game)
				self.drawLevel(game)
				self.drawScore(game)
				self.drawBoard(game)

				# pg.draw.rect(self.screen, (255,   0,   0), (80, 50, 230, 270), 10, 58)

			case game.States.menu:
				menuText = self.levelFont.render("Paused, Esc to unpause", 1, (255, 255, 255))
				self.screen.blit(menuText, (((w - menuText.get_width())/2 , (h - menuText.get_height()-40)/2)))


			case game.States.countdown:
				countdownText = self.levelFont.render(str(math.ceil(game.countdownTimer)), 1, (255, 255, 255))
				self.screen.blit(countdownText, (((w - countdownText.get_width())/2 , (h - countdownText.get_height()-40)/2)))

			case game.States.gameover:
				gameOverText = self.scoreFont.render("Game Over", 1, (255, 255, 255))
				restartingText = self.levelFont.render("Restarting...", 1, (255, 255, 255))
				self.screen.blit(gameOverText, (((w - gameOverText.get_width())/2 , (h - gameOverText.get_height()-40)/2)))
				self.screen.blit(restartingText, (((w - restartingText.get_width())/2 , (h + gameOverText.get_height()+40-restartingText.get_height())/2)))

		if len(self.fpsHistory) > self.maxFrameHistory:
			subtracted = self.fpsHistory.pop(-self.maxFrameHistory-1)
			self.fpsSum -= subtracted
		if self.debug:
			self.drawFrameRate()


	def pseudoFramesByLevel(self, level):
		if level > 29:
			level = 29
		speed = {
			0 : 48,
			1 :	43,
			2 :	38,
			3 :	33,
			4 :	28,
			5 :	23,
			6 :	18,
			7 :	13,
			8 :	8,
			9 :	6,
			10:	5,
			11: 5,
			12:	5,
			13: 4,
			14: 4,
			15:	4,
			16: 3,
			17: 3,
			18:	3,
			19: 2,
			20: 2,
			21: 2,
			22: 2,
			23: 2,
			24: 2,
			25: 2,
			26: 2,
			27: 2,
			28:	2,
			29:	1,
		}
		return speed[level]

	def __init__(self, width, height) -> None:

		self.screen = pg.display.set_mode((width, height))
		pg.display.set_caption("Tetris")
		self.clock = pg.time.Clock()

		with open('./resolutions.json', 'r') as f:
			self.resolutionPreset = json.load(f)[f'{width}x{height}']
		pprint.pprint(self.resolutionPreset)

		self.minoSize = self.resolutionPreset['playing']['generalPieceSize']
		self.nextlistIOffset = self.resolutionPreset['playing']['nextlistIOffset']
		self.nextlistPieceOffsets = {k: Vector2(self.minoSize*v[0], self.minoSize*v[1]) for k, v in self.resolutionPreset['playing']['nextlistPieceOffsets'].items()}

		self.typeToImage = {
			'I': pg.transform.scale(pg.image.load('./assets/i.png'), (self.minoSize, self.minoSize)),
			'J': pg.transform.scale(pg.image.load('./assets/j.png'), (self.minoSize, self.minoSize)),
			'L': pg.transform.scale(pg.image.load('./assets/l.png'), (self.minoSize, self.minoSize)),
			'S': pg.transform.scale(pg.image.load('./assets/s.png'), (self.minoSize, self.minoSize)),
			'Z': pg.transform.scale(pg.image.load('./assets/z.png'), (self.minoSize, self.minoSize)),
			'O': pg.transform.scale(pg.image.load('./assets/o.png'), (self.minoSize, self.minoSize)),
			'T': pg.transform.scale(pg.image.load('./assets/t.png'), (self.minoSize, self.minoSize)),
		}

		self.typeToShadowImage = {}
		for k, v in self.typeToImage.items():
			shadowTexture = pg.Surface(pg.Vector2(self.minoSize, self.minoSize), pg.SRCALPHA, 32)

			skew = 1
			swatch = v.get_at((self.minoSize//2, self.minoSize//2))
			shadowColor = pg.Color([x*y for x, y in zip(swatch, [skew, skew, skew])])
			
			pg.draw.polygon(shadowTexture, shadowColor, [pg.Vector2( 1,  1), pg.Vector2( 3,  3), pg.Vector2(self.minoSize-3,  3), pg.Vector2(self.minoSize-1,  1)])
			pg.draw.polygon(shadowTexture, shadowColor, [pg.Vector2( 1,  1), pg.Vector2( 3,  3), pg.Vector2( 3, self.minoSize-3), pg.Vector2( 1, self.minoSize-1)])
			pg.draw.polygon(shadowTexture, shadowColor, [pg.Vector2(self.minoSize-1,  1), pg.Vector2(self.minoSize-3,  3), pg.Vector2(self.minoSize-3, self.minoSize-3), pg.Vector2(self.minoSize-1, self.minoSize-1)])
			pg.draw.polygon(shadowTexture, shadowColor, [pg.Vector2(self.minoSize-1, self.minoSize-1), pg.Vector2(self.minoSize-3, self.minoSize-3), pg.Vector2( 3, self.minoSize-3), pg.Vector2( 1, self.minoSize-1)])

			self.typeToShadowImage[k] = shadowTexture
		
		# idek what this number is for it's just easier to estimate font sizes because I don't know how font pointing works

		self.holdBoxPos = Vector2(self.resolutionPreset['setup']['holdBoxPos'])
		holdBoxSize = Vector2(self.resolutionPreset['setup']['holdBoxSize'])
		holdBoxBorderThickness = self.resolutionPreset['setup']['holdBoxBorderThickness']
		holdBoxBorderRadius = self.resolutionPreset['setup']['holdBoxBorderRadius']
		holdFontSize = self.resolutionPreset['setup']['holdFontSize']
		holdLineSeparatorPos = [Vector2(x) for x in self.resolutionPreset['setup']['holdLineSeparatorPos']]
		holdLineSeparatorThickness = self.resolutionPreset['setup']['holdLineSeparatorThickness']

		self.holdSurfaceTemplate = pg.Surface(holdBoxSize)
		pg.draw.rect(self.holdSurfaceTemplate, (255, 255, 255), (0, 0, *holdBoxSize), holdBoxBorderThickness, holdBoxBorderRadius)
		pg.draw.line(self.holdSurfaceTemplate, (255, 255, 255), *holdLineSeparatorPos, 8)
		holdFont = pg.font.SysFont('calibri', holdFontSize).render("HOLD", 1, (255, 255, 255))
		self.holdSurfaceTemplate.blit(holdFont, (Vector2(holdBoxSize.x, holdLineSeparatorPos[0].y+holdLineSeparatorThickness/2)-Vector2(holdFont.get_rect().size))/2)
		self.holdPiecePos = (holdBoxSize + Vector2(0, holdLineSeparatorPos[0].y+holdLineSeparatorThickness))/2 - Vector2(0, holdBoxBorderThickness)
		# ^^^^ must be in local space for self.holdSurfaceTemplate
		

		self.nextlistBoxPos = Vector2(self.resolutionPreset['setup']['nextlistBoxPos'])
		nextlistBoxSize = Vector2(self.resolutionPreset['setup']['nextlistBoxSize'])
		nextlistBoxBorderThickness = self.resolutionPreset['setup']['nextlistBoxBorderThickness']
		nextlistBoxBorderRadius = self.resolutionPreset['setup']['nextlistBoxBorderRadius']
		nextlistFontSize = self.resolutionPreset['setup']['nextlistFontSize']
		nextlistLineSeparatorPos = [Vector2(x) for x in self.resolutionPreset['setup']['nextlistLineSeparatorPos']]
		nextlistLineSeparatorThickness = self.resolutionPreset['setup']['nextlistLineSeparatorThickness']

		self.nextlistSurfaceTemplate = pg.Surface(nextlistBoxSize)
		pg.draw.rect(self.nextlistSurfaceTemplate, (255, 255, 255), (0, 0, *nextlistBoxSize), nextlistBoxBorderThickness, nextlistBoxBorderRadius)
		pg.draw.line(self.nextlistSurfaceTemplate, (255, 255, 255), *nextlistLineSeparatorPos, 8)
		nextlistFont = pg.font.SysFont('calibri', nextlistFontSize).render("NEXT", 1, (255, 255, 255))
		self.nextlistSurfaceTemplate.blit(nextlistFont, (Vector2(nextlistBoxSize.x, nextlistLineSeparatorPos[0].y+nextlistLineSeparatorThickness/2)-Vector2(nextlistFont.get_rect().size))/2)
		self.nextlistPiecePos = (nextlistBoxSize + Vector2(0, nextlistLineSeparatorPos[0].y+nextlistLineSeparatorThickness-nextlistBoxBorderThickness))/2 - Vector2(0, nextlistBoxBorderThickness)
		# ^^^^ must be in local space for self.holdSurfaceTemplate


		self.levelBoxPos = Vector2(self.resolutionPreset['setup']['levelBoxPos'])
		levelBoxSize = Vector2(self.resolutionPreset['setup']['levelBoxSize'])
		levelBoxBorderThickness = self.resolutionPreset['setup']['levelBoxBorderThickness']
		levelBoxBorderRadius = self.resolutionPreset['setup']['levelBoxBorderRadius']
		levelFontSize = self.resolutionPreset['setup']['levelFontSize']
		self.levelFont = pg.font.SysFont('calibri', levelFontSize)
		self.levelSurfaceTemplate = pg.Surface(levelBoxSize)
		pg.draw.rect(self.levelSurfaceTemplate, (255, 255, 255), (0, 0, *levelBoxSize), levelBoxBorderThickness, levelBoxBorderRadius)
		self.levelTextPos = levelBoxSize/2


		self.scoreBoxPos = Vector2(self.resolutionPreset['setup']['scoreBoxPos'])
		scoreBoxSize = Vector2(self.resolutionPreset['setup']['scoreBoxSize'])
		scoreBoxBorderThickness = self.resolutionPreset['setup']['scoreBoxBorderThickness']
		scoreBoxBorderRadius = self.resolutionPreset['setup']['scoreBoxBorderRadius']
		scoreFontSizePrimary = self.resolutionPreset['setup']['scoreFontSizePrimary']
		scoreFontSizeSecondary = self.resolutionPreset['setup']['scoreFontSizeSecondary']
		scoreLineSeparatorPos = [Vector2(x) for x in self.resolutionPreset['setup']['scoreLineSeparatorPos']]
		scoreLineSeparatorThickness = self.resolutionPreset['setup']['scoreLineSeparatorThickness']
		
		self.scoreTextPos = (scoreBoxSize + Vector2(0, scoreLineSeparatorPos[0].y+scoreLineSeparatorThickness-scoreBoxBorderThickness))/2
		# ^^^^ must be in local space for self.holdSurfaceTemplate


		self.scoreSurfaceTemplate = pg.Surface(scoreBoxSize)
		pg.draw.rect(self.scoreSurfaceTemplate, (255, 255, 255), (0, 0, *scoreBoxSize), scoreBoxBorderThickness, scoreBoxBorderRadius)
		pg.draw.line(self.scoreSurfaceTemplate, (255, 255, 255), *scoreLineSeparatorPos, 8)
		scoreFontPrimary = pg.font.SysFont('calibri', scoreFontSizePrimary).render("SCORE", 1, (255, 255, 255))
		self.scoreSurfaceTemplate.blit(scoreFontPrimary, (Vector2(scoreBoxSize.x, scoreLineSeparatorPos[0].y+scoreLineSeparatorThickness/2)-Vector2(scoreFontPrimary.get_rect().size))/2)
		
		self.scoreFont = pg.font.SysFont('calibri', scoreFontSizeSecondary)



		# self.shadowSurfaceTemplate = pg.Surface()
		# self.boardSurfaceTemplate = pg.Surface()

class Controller:
	def startSinglePlayer():
		disp = Display(1200, 900)
		disp.keyFrameCountCache = {}

		
		run = True
		game = Game()
		disp.pseudoFrameCount = 0
		disp.pseudoFrameCountDelta = 0
		disp.pseudoFrameCountLastTrigger = 0
		disp.fpsHistory = []
		disp.fpsSum = 0.0

		fTimeElapsed = 0
		iFrameCount = -1

		disp.pause = False
		disp.debug = True




		while run:
			iFrameCount += 1
			dt = disp.clock.tick_busy_loop(60)/1000
			fTimeElapsed += dt
			disp.pseudoFrameCount = disp.pseudoFrameCountDelta + (fTimeElapsed*disp.pseudoFramesPerSecond)//1
			if dt == 0.0: dt = 0.001
			# RP.formattedRP(f"""
			# 	{disp.fpsHistory}
			# 	{dt}
			# """)
			fps = round(1/min(1, dt), 10)
			disp.fpsHistory.append(fps)
			disp.fpsSum += fps

			RP.formattedRP(f"""
				{fTimeElapsed}
				
			""")

			disp.drawWindow(game)
			pg.display.update()

			for e in pg.event.get():
				if e.type == pg.QUIT:
					pg.quit()
					quit()
				if e.type == pg.KEYDOWN:
					if e.key == pg.K_ESCAPE:
						match game.state:
							case game.States.menu:
								game.state = game.States.countdown
								game.countdownTimer = 3.0
							case game.States.playing:
								game.state = game.States.menu
								if game.canPlayMusic:game.themeSong.stop()

					if e.key == pg.K_p: # debug key
						disp.debug = not disp.debug
					if e.key == pg.K_F12:
						pg.image.save(disp.screen, f"./screenshots/{datetime.datetime.now()}.jpg")
					if game.state != game.States.playing:
						continue
					if e.key == pg.K_c:
						game.holdActivePiece()
						disp.pseudoFrameCountLastTrigger = disp.pseudoFrameCount


			match game.state:
				case game.States.playing:

					keys = pg.key.get_pressed()
					buttons = pg.mouse.get_pressed()


					if disp.checkIfKeyShouldExec(pg.K_LEFT, keys):
						game.moveActivePieceHorz(-1)
					if disp.checkIfKeyShouldExec(pg.K_RIGHT, keys):
						game.moveActivePieceHorz( 1)
					if disp.checkIfKeyShouldExec(pg.K_z, keys):
						game.rotateActivePiece(-1)
					if disp.checkIfKeyShouldExec(pg.K_UP, keys):
						game.rotateActivePiece( 1)

					if disp.checkIfKeyShouldExec(pg.K_DOWN, keys):
						game.stepActivePieceDown()
						disp.pseudoFrameCountDelta -= disp.pseudoFrameCount % disp.pseudoFramesByLevel(game.totalLines//10) + 1

					if SignalEdge.getRisingEdge(keys[pg.K_SPACE], pg.K_SPACE):
						game.dropActivePieceDown()
						disp.pseudoFrameCountDelta -= disp.pseudoFrameCount % disp.pseudoFramesByLevel(game.totalLines//10) + 1

					if (disp.pseudoFrameCount % disp.pseudoFramesByLevel(game.totalLines//10)) == 0 and disp.pseudoFrameCount != disp.pseudoFrameCountLastTrigger:
						disp.pseudoFrameCountLastTrigger = disp.pseudoFrameCount
						game.stepActivePieceDown()

				case game.States.menu:
					pass

				case game.States.countdown:
					game.countdownTimer -= dt
					if game.countdownTimer < 0:
						game.state = game.States.playing
						if game.canPlayMusic: game.themeSong.play(loops=-1)
												

				case game.States.gameover:
					game.countdownTimer -= dt
					if game.countdownTimer < 0:

						game = Game()
						game.state = game.States.countdown


if __name__ == "__main__":
	Controller.startSinglePlayer()