from copy import deepcopy
import fractions
from pprint import pprint
from enum import Enum, auto
from signaledge import SignalEdge
import keyboard, re, time, random, pygame as pg

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
		if self.checkActivePieceCollision(self.anchorX+dir, self.anchorY, self.activePiece):
			return
		self.anchorX += dir

	def placePiece(self):
		minoType, pieceRot = self.metaIdToTypeAndRot[self.activePiece]

		for xComponent, yComponent in list(map(lambda x: ((15-x)%4, (15-x)//4), self.metaIdToActiveBits[self.activePiece])):
			self.gameBoard[self.anchorY+yComponent][self.anchorX+xComponent] = minoType

		minY, maxY = self.metaIdToXYBounds[self.activePiece][2:]
		for i in range(minY, maxY+1):
			for cell in self.gameBoard[self.anchorY+i]:
				if cell == '-':
					break
			else:
				self.gameBoard.pop(self.anchorY+i)
				self.gameBoard.insert(0, ['-' for x in range(10)])

				# This is where score should be updated for the removal of any lines(s)
				# self.addScore()


		self.activePiece = self.nextList.pop(0)
		self.nextList.append(self.typeAndRotToMeta[self.typeList[random.randint(0, 6)]]['0'])
		self.canHoldPiece = True
		self.anchorX = 3
		self.anchorY = -1

	def updateDisplayedBoard(self):
		outBoard = deepcopy(self.gameBoard)
		minoType, pieceRot = self.metaIdToTypeAndRot[self.activePiece]
		for xComponent, yComponent in list(map(lambda x: ((15-x)%4, (15-x)//4), self.metaIdToActiveBits[self.activePiece])):
			outBoard[self.anchorY+yComponent][self.anchorX+xComponent] = minoType

		return outBoard

	def checkActivePieceCollision(self, anchorX :int, anchorY :int, metaID :int) -> bool:
		"""
		Returns True if collision is detected for given piece ( {metaID} ) on given XY anchor ( {anchorX, anchorY} )
		Falsy condition could be for multiple reasons: cell out of bounds, overlap on filled cell	"""

		if sum(list(map(lambda x: (not (0<=anchorX+((15-x)%4)<10))+(not (0<=anchorY+((15-x)//4)<20)), self.metaIdToActiveBits[metaID]))):
			return True
		for xComponent, yComponent in list(map(lambda x: ((15-x)%4, (15-x)//4), self.metaIdToActiveBits[metaID])):
			if anchorY+yComponent > len(self.gameBoard):
				...
			if self.gameBoard[anchorY+yComponent][anchorX+xComponent] != '-':
				return True
		return False
	
	def stepActivePieceDown(self):
		newAnchorY = self.anchorY
		if not self.checkActivePieceCollision(self.anchorX, newAnchorY+1, self.activePiece):
			# print(newAnchorY)
			self.anchorY = newAnchorY+1
			return
		

		self.placePiece()
	
	def dropActivePieceDown(self):
		newAnchorY = self.anchorY
		while not self.checkActivePieceCollision(self.anchorX, newAnchorY+1, self.activePiece):
			newAnchorY += 1
		self.anchorY = newAnchorY
		self.placePiece()

	def getNeededKick(self, oldRot, newRot, pieceType):
		if pieceType == "O":
			return (0, 0)
		
		match (oldRot, newRot, pieceType=="I"):
			case ('0', 'R', False):
				kickTests = [(0, 0), (-1, 0), (-1,+1), ( 0,-2), (-1,-2)]
			case ('R', '0', False):
				kickTests = [(0, 0), (+1, 0), (+1,-1), ( 0,+2), (+1,+2)]
			case ('R', '2', False):
				kickTests = [(0, 0), (+1, 0), (+1,-1), ( 0,+2), (+1,+2)]
			case ('2', 'R', False):
				kickTests = [(0, 0), (-1, 0), (-1,+1), ( 0,-2), (-1,-2)]
			case ('2', 'L', False):
				kickTests = [(0, 0), (+1, 0), (+1,+1), ( 0,-2), (+1,-2)]
			case ('L', '2', False):
				kickTests = [(0, 0), (-1, 0), (-1,-1), ( 0,+2), (-1,+2)]
			case ('L', '0', False):
				kickTests = [(0, 0), (-1, 0), (-1,-1), ( 0,+2), (-1,+2)]
			case ('0', 'L', False):
				kickTests = [(0, 0), (+1, 0), (+1,+1), ( 0,-2), (+1,-2)]
			case ('0', 'R', True):
				kickTests = [(0, 0), (-2, 0), (+1, 0), (+1,+2), (-2,-1)]
			case ('R', '0', True):
				kickTests = [(0, 0), (+2, 0), (-1, 0), (+2,+1), (-1,-2)]
			case ('R', '2', True):
				kickTests = [(0, 0), (-1, 0), (+2, 0), (-1,+2), (+2,-1)]
			case ('2', 'R', True):
				kickTests = [(0, 0), (-2, 0), (+1, 0), (-2,+1), (+1,-1)]
			case ('2', 'L', True):
				kickTests = [(0, 0), (+2, 0), (-1, 0), (+2,+1), (-1,-1)]
			case ('L', '2', True):
				kickTests = [(0, 0), (+1, 0), (-2, 0), (+1,+2), (-2,-1)]
			case ('L', '0', True):
				kickTests = [(0, 0), (-2, 0), (+1, 0), (-2,+1), (+1,-2)]
			case ('0', 'L', True):
				kickTests = [(0, 0), (+2, 0), (-1, 0), (-1,+2), (+2,-1)]
			case _:
				print(oldRot, newRot, pieceType=="I")

		
		# iterate through each available test
		for xKick, yKick in kickTests:

			# if test does not collide, return
			if not self.checkActivePieceCollision(self.anchorX+xKick, self.anchorY+yKick, self.typeAndRotToMeta[pieceType][newRot]):
				return (xKick, yKick)
		return (69, 420) # No tests work, abort rotation

	def rotateActivePiece(self, dir :int):
		pieceType, pieceRot = self.metaIdToTypeAndRot[self.activePiece]

		assert dir in [ 1, -1], "Variable 'dir' must be of type 'int' with value '1' or '-1'"
		match (pieceRot, dir):
			case ('0',  1):
				newRot = 'R'
			case ('R',  1):
				newRot = '2'
			case ('R', -1):
				newRot = '0'
			case ('2',  1):
				newRot = 'L'
			case ('2', -1):
				newRot = 'R'
			case ('L',  1):
				newRot = '0'
			case ('L', -1):
				newRot = '2'
			case ('0', -1):
				newRot = 'L'
		
		xKick, yKick = self.getNeededKick(pieceRot, newRot, pieceType)
		if xKick == 69: # No rotation test succeeded, abort
			return
		self.anchorX += xKick; self.anchorY += yKick
		self.activePiece = self.typeAndRotToMeta[pieceType][newRot]


	def holdActivePiece(self):
		# if not self.canHoldPiece:
		# 	return
		
		self.anchorX = 3
		self.anchorY = -1
		
		self.canHoldPiece = False
		if self.heldPiece == 0:
			self.heldPiece = self.typeAndRotToMeta[self.metaIdToTypeAndRot[self.activePiece][0]]['0']
			self.activePiece = self.nextList.pop(0)
			self.nextList.append(self.typeAndRotToMeta[self.typeList[random.randint(0, 6)]]['0'])
			return
		
		temp = self.typeAndRotToMeta[self.metaIdToTypeAndRot[self.activePiece][0]]['0']
		self.activePiece = self.heldPiece
		self.heldPiece = temp
		


	def __init__(self):
		self.gameBoard :list[list[str]] = [['-' for x in range(10)] for x in range(20)]
		
		self.activePiece = 3840
		# self.activePiece :int = self.typeAndRotToMeta[self.typeList[random.randint(0, 6)]]['0']
		self.nextList = [self.typeAndRotToMeta[self.typeList[random.randint(0, 6)]]['0'], self.typeAndRotToMeta[self.typeList[random.randint(0, 6)]]['0'], self.typeAndRotToMeta[self.typeList[random.randint(0, 6)]]['0']]
		self.canHoldPiece = True
		self.heldPiece = 0
		self.anchorX :int= 3
		self.anchorY :int= -1

class Display:
	levelFont = pg.font.SysFont('calibri', 62)
	scoreFont = pg.font.SysFont('calibri', 80)
	pseudoFramesPerSecond = 60

	# things for key "listener"
	keyFrameCountCache = {}

	typeToImage = {
		'I': pg.image.load('./assets/i.png'),
		'J': pg.image.load('./assets/j.png'),
		'L': pg.image.load('./assets/l.png'),
		'S': pg.image.load('./assets/s.png'),
		'Z': pg.image.load('./assets/z.png'),
		'O': pg.image.load('./assets/o.png'),
		'T': pg.image.load('./assets/t.png'),
	}

	nextPositions = {
		'I': (-40,   0),
		'J': (-20, -20),
		'L': (-20, -20),
		'S': (-20, -20),
		'Z': (-20, -20),
		'O': (-40, -20),
		'T': (-20, -20),
	}



	def checkIfKeyShouldExec(self, keycode :int, keys :list[int]):
		if not keys[keycode]  or  (not keycode in self.keyFrameCountCache):
			self.keyFrameCountCache[keycode] = -1
			return False
		
		self.keyFrameCountCache[keycode] += 1

		v = self.keyFrameCountCache[keycode]
		return ((v < 1) or ((v//3) > 5 and (v%3)==0))

	def drawWindow(self):
		self.screen.blit(self.background, (0,0))

		self.renderHold()
		self.renderNextList()
		# self.drawShadow()
		self.drawBoard()

	def renderLevel(self):
		levelText = Display.levelFont.render("LEVEL: "+ str(self.game.level), 1, (255, 255, 255))
		self.screen.blit(levelText, (195 - levelText.get_width()/2 , 417 - levelText.get_height()/2))

	def renderScore(self):
		scoreText = Display.scoreFont.render(str(self.game.score), 1, (255, 255, 255))
		self.screen.blit(scoreText, (195 - scoreText.get_width()/2 , 656 - scoreText.get_height()/2))

	def renderHold(self):
		if self.game.heldPiece != 0:
			for x, y in list(map(lambda x: ((15-x)%4, (15-x)//4), self.game.metaIdToActiveBits[self.game.heldPiece])):
				self.screen.blit(
					self.typeToImage[self.game.metaIdToTypeAndRot[self.game.heldPiece][0]], (					 # Image 	:pygame.Image
					int(155+(x*40)+self.nextPositions[self.game.metaIdToTypeAndRot[self.game.heldPiece][0]][0]), # X coord 	:int
					int(161+(y*40)+self.nextPositions[self.game.metaIdToTypeAndRot[self.game.heldPiece][0]][1]), # Y coord	:int
					40, 40) 																					 # Image Width, Height :int
				)


	def renderNextList(self):
		for i, metaID in enumerate(self.game.nextList):
			for x, y in list(map(lambda x: ((15-x)%4, (15-x)//4), self.game.metaIdToActiveBits[metaID])):
				self.screen.blit(
					self.typeToImage[self.game.metaIdToTypeAndRot[metaID][0]], (								 # Image 	:pygame.Image
					int(960 + (x*40)+self.nextPositions[self.game.metaIdToTypeAndRot[metaID][0]][0]), 			 # X coord 	:int
					int(245 + (y*40)+(165*i)+self.nextPositions[self.game.metaIdToTypeAndRot[metaID][0]][1]), 	 # Y coord	:int
					40, 40)																						 # Image Width, Height :int
				)


	def gridToCoord(self, x, y) -> tuple[int, int]:
		x *= 40
		y *= 40
		x += 400
		y += 50
		tup = (x, y)
		return tup

	def drawBoard(self):
		board = self.game.updateDisplayedBoard()
		for j in range(len(board)):
			for i in range(len(board[j])):
				if board[j][i] != '-':
					tup = self.gridToCoord(i, j)
					image = self.typeToImage[board[j][i]]
					self.screen.blit(image, (tup[0], tup[1], 40, 40))

			
	def __init__(self):
		self.keyFrameCountCache = {}

		
		run = True
		self.game = Game()
		self.pseudoFrameCount = 0
		self.pseudoFrameCountDelta = 0
		self.pseudoFrameCountLastTrigger = 0
		
		self.screen = pg.display.set_mode((1200, 900))
		pg.display.set_caption("Tetris")
		self.background = pg.image.load('./assets/board.png')
		clock = pg.time.Clock()
		
		fTimeElapsed = 0
		iFrameCount = -1

		self.pause = False



		while run:
			iFrameCount += 1
			dt = clock.tick_busy_loop()/1000
			fTimeElapsed += dt
			self.pseudoFrameCount = self.pseudoFrameCountDelta + (fTimeElapsed*self.pseudoFramesPerSecond)//1

			self.drawWindow()
			pg.display.update()


			keys = pg.key.get_pressed()
			buttons = pg.mouse.get_pressed()

			for e in pg.event.get():
				if e.type == pg.QUIT:
					pg.quit()
					quit()
				if e.type == pg.KEYDOWN:
					if e.key == pg.K_c:
						self.game.holdActivePiece()
					if e.key == pg.K_ESCAPE:
						self.pause = not self.pause
					if e.key == pg.K_p:
						g = self.game
						for piece in self.game.nextList:
							print(self.game.metaIdToTypeAndRot[piece])

			if self.checkIfKeyShouldExec(pg.K_a, keys):
				self.game.moveActivePieceHorz(-1)
			if self.checkIfKeyShouldExec(pg.K_d, keys):
				self.game.moveActivePieceHorz( 1)
			if self.checkIfKeyShouldExec(pg.K_z, keys):
				self.game.rotateActivePiece(-1)
			if self.checkIfKeyShouldExec(pg.K_w, keys):
				self.game.rotateActivePiece( 1)

			if self.checkIfKeyShouldExec(pg.K_s, keys):
				self.game.stepActivePieceDown()
				self.pseudoFrameCountDelta -= self.pseudoFrameCount % 29 + 1

			if SignalEdge.getRisingEdge(keys[pg.K_SPACE], pg.K_SPACE):
				self.game.dropActivePieceDown()
				self.pseudoFrameCountDelta -= self.pseudoFrameCount % 29 + 1


			if (self.pseudoFrameCount % 29) == 0 and self.pseudoFrameCount != self.pseudoFrameCountLastTrigger:
				self.pseudoFrameCountLastTrigger = self.pseudoFrameCount
				self.game.stepActivePieceDown()
			
			# self.game.dropActivePieceDown()








# pprint(Game.typeToActiveBits)
Display()