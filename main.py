from copy import deepcopy
from enum import Enum, auto
from utilities.signaledge import SignalEdge; from utilities.repeatedPrint import RepeatedPrint as RP
import random, pygame as pg, math, datetime, time, json, pprint, yaml
from pygame import Vector2


# 
# Tetris, by Nick Glenn, 5/31/23
# Requires Pygame package
# 

pg.init()


class GameStates(Enum):
	menu = auto()
	countdown = auto()
	playing = auto()
	gameover = auto()
	initialsInput = auto()
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

	fTimeElapsed = -1

	typeAndRotToMeta = {
		"I" : {
			"0": 0xF00,
			"R": 0x2222,
			"2": 0xF0,
			"L": 0x4444,
		},
		"J" : {
			"0": 0x8E0,
			"R": 0x644,
			"2": 0xE2,
			"L": 0x44C,
		},
		"L" : {
			"0": 0x2E0,
			"R": 0x446,
			"2": 0xE8,
			"L": 0xC44,
		},
		"O" : {
			"0": 0x660,
			"R": 0x660,
			"2": 0x660,
			"L": 0x660,
		},
		"S" : {
			"0": 0x6C0,
			"R": 0x462,
			"2": 0x6C,
			"L": 0x8C4,
		},
		"T" : {
			"0": 0x4E0,
			"R": 0x464,
			"2": 0xE4,
			"L": 0x4C4,
		},
		"Z" : {
			"0": 0xC60,
			"R": 0x264,
			"2": 0xC6,
			"L": 0x4C8,
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
		self.canHoldPiece = True
		self.anchorX = 3
		self.anchorY = -1
		self.addNextPiece()

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
			
		if self.isEasymode:
			for pieceType, piecesDroughtSize in self.droughtCounter.items():
				if pieceType == newPieceType:
					continue
				if piecesDroughtSize >= 25:
					newPieceType = pieceType
					break
				self.droughtCounter[pieceType] += 1
			self.droughtCounter[newPieceType] = 0

		self.nextList.append(self.typeAndRotToMeta[newPieceType]['0'])

		
		if self.checkPieceCollision(self.anchorX, self.anchorY, self.activePiece):
			if self.canPlayMusic: self.themeSong.stop(); self.gameoverMusic.play()
			# game over
			self.state = GameStates.initialsInput

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

	def __init__(self, easyMode :bool):
		self.gameBoard :list[list[str]] = [['-' for x in range(10)] for x in range(20)]
		
		
		# self.activePiece = 1124
		self.activePiece :int = self.typeAndRotToMeta[self.typeList[random.randint(0, 6)]]['0']
		self.droughtCounter = { type: 0 for type in self.typeList }
		self.anchorX :int= 3
		self.anchorY :int= -1
		self.canHoldPiece = True
		self.heldPiece = 0
		self.totalLines = 0
		self.score = 0
		self.isEasymode = easyMode
		self.nextList = []; self.addNextPiece(); self.addNextPiece(); self.addNextPiece()
		
		self.state = GameStates.countdown
		self.countdownTimer = 3.0
	
	def __str__(self):
		o = ""
		o += f"fTimeElapsed: 	{self.fTimeElapsed}\n"
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
	fTimeElapsed :float
	fpsHistory :list
	fpsSum :int
	pause :bool
	debug :bool

	highscores = []

	initialsText = ''

	# things for key "listener"
	perKeyTickCache = {}

	
	background = pg.image.load('./assets/board.png')


	def checkIfKeyShouldExec(self, keycode :int, keys :list[int]):
		isPressed = keys[keycode]
		if not isPressed  or  (not keycode in self.perKeyTickCache):
			#									V    first pressed     V  V     last trigger     V
			self.perKeyTickCache[keycode] = [self.pseudoFrameCount, self.pseudoFrameCount]
			return False

		# passes guard clause if it is a new pseudoframe
		if self.pseudoFrameCount == self.perKeyTickCache[keycode][1]:
			return False
		self.perKeyTickCache[keycode][1] = self.pseudoFrameCount

		deltaFrames = self.pseudoFrameCount-self.perKeyTickCache[keycode][0]-1
		spamFrequency = 4		# in pseudo-frames
		delayBeforeSpam = 16 	# in pseudo-frames
		return ((deltaFrames < 1) or (deltaFrames-delayBeforeSpam >= 0 and ((deltaFrames-delayBeforeSpam)%spamFrequency) == 0))
	
	

	def drawLevel(self, game :Game, elements :dict):
		boxPos, boxSize, boxBorderThickness, boxBorderRadius, fontSize \
		= elements.values()
		
		# draws the rounded rectangle for the given box
		pg.draw.rect(self.screen, (255, 255, 255), (*boxPos, *boxSize), boxBorderThickness, boxBorderRadius)
		
		levelText = pg.font.SysFont('calibri', fontSize).render("LEVEL: "+ str(game.totalLines//10), 1, (255, 255, 255))
		self.screen.blit(levelText, boxPos+(boxSize-Vector2(levelText.get_rect().size))/2)

	def drawScore(self, game :Game, elements :dict):
		boxPos, boxSize, boxBorderThickness, boxBorderRadius, fontSizePrimary, fontSizeSecondary, lineSeparatorPos, lineSeparatorThickness \
		= elements.values()
		boxPos = Vector2(boxPos)
		
		# draws the rounded rectangle for the given box
		pg.draw.rect(self.screen, (255, 255, 255), (*boxPos, *boxSize), boxBorderThickness, boxBorderRadius)
		pg.draw.line(self.screen, (255, 255, 255), *(boxPos+Vector2(x) for x in lineSeparatorPos), lineSeparatorThickness)
		
		labelText = pg.font.SysFont('calibri', fontSizePrimary).render("SCORE", 1, (255, 255, 255))
		scoreText = pg.font.SysFont('calibri', fontSizeSecondary).render(str(game.score), 1, (255, 255, 255))
		self.screen.blit(labelText, boxPos+(Vector2(boxSize[0], lineSeparatorPos[0][1]+lineSeparatorThickness/2)-Vector2(labelText.get_rect().size))/2)
		self.screen.blit(scoreText, boxPos+(boxSize-Vector2(scoreText.get_rect().size)+Vector2(0, -2*boxBorderThickness+lineSeparatorPos[0][1]+lineSeparatorThickness/2))/2)

	def drawHold(self, game :Game, elements :dict):
		boxPos, boxSize, boxBorderThickness, boxBorderRadius, fontSize, lineSeparatorPos, lineSeparatorThickness \
		= elements.values()
		boxPos = Vector2(boxPos)
		
		# draws the rounded rectangle for the given box
		font = pg.font.SysFont('calibri', fontSize).render("HOLD", 1, (255, 255, 255))
		self.screen.blit(font, boxPos+(Vector2(boxSize[0], lineSeparatorPos[0][1]+lineSeparatorThickness/2)-Vector2(font.get_rect().size))/2)
		pg.draw.rect(self.screen, (255, 255, 255), (*boxPos, *boxSize), boxBorderThickness, boxBorderRadius)
		pg.draw.line(self.screen, (255, 255, 255), *(boxPos+Vector2(x) for x in lineSeparatorPos), lineSeparatorThickness)
		
		piecePos = (boxSize + Vector2(0, lineSeparatorPos[0][1]+(lineSeparatorThickness/2)-boxBorderThickness))/2
		if game.heldPiece != 0:
			for x, y in list(map(lambda x: ((15-x)%4, (15-x)//4), game.metaIdToActiveBits[game.heldPiece])):
				offset = self.playingElements['pieceOffsets'][game.metaIdToTypeAndRot[game.heldPiece][0]]
				boardVector = Vector2(x, y)
				position = boxPos+piecePos+(boardVector-offset)*self.playingElements['minoSize']
				self.screen.blit(
					self.typeToImage[game.metaIdToTypeAndRot[game.heldPiece][0]], (
					position,
					Vector2(self.playingElements['minoSize'], self.playingElements['minoSize']))
				)

	def drawNextlist(self, game :Game, elements :dict):
		boxPos, boxSize, boxBorderThickness, boxBorderRadius, fontSize, lineSeparatorPos, lineSeparatorThickness, indexOffset \
		= elements.values()
		boxPos = Vector2(boxPos)
		
		# draws the rounded rectangle for the given box
		font = pg.font.SysFont('calibri', fontSize).render("NEXT", 1, (255, 255, 255))
		self.screen.blit(font, boxPos+(Vector2(boxSize[0], lineSeparatorPos[0][1]+lineSeparatorThickness/2)-Vector2(font.get_rect().size))/2)
		pg.draw.rect(self.screen, (255, 255, 255), (*boxPos, *boxSize), boxBorderThickness, boxBorderRadius)
		pg.draw.line(self.screen, (255, 255, 255), *(boxPos+Vector2(x) for x in lineSeparatorPos), lineSeparatorThickness)

		piecePos = (boxSize + Vector2(0, lineSeparatorPos[0][1]+(lineSeparatorThickness/2)-boxBorderThickness))/2
		for i, metaID in enumerate(game.nextList):
			for x, y in list(map(lambda x: ((15-x)%4, (15-x)//4), game.metaIdToActiveBits[metaID])):
				offset = self.playingElements['pieceOffsets'][game.metaIdToTypeAndRot[metaID][0]]
				boardVector = Vector2(x, y)
				indexOffsetVector = Vector2(0, (i-1)*indexOffset)
				position = boxPos+piecePos+(boardVector-offset)*self.playingElements['minoSize']+indexOffsetVector
				self.screen.blit(
					self.typeToImage[game.metaIdToTypeAndRot[metaID][0]], (
					position,
					Vector2(self.playingElements['minoSize'], self.playingElements['minoSize']))
				)

	def drawBoard(self, game :Game, elements :dict):
		boxPos, boxSize, boxBorderThickness, cellSeparatorThickness \
		= elements.values()
		board = game.updateDisplayedBoard()

		boxPos = Vector2(boxPos)
		
		# draws fill color of board
		pg.draw.rect(self.screen, (26, 26, 26), (*boxPos, *boxSize))
		# draws border color of board as outset border
		borderOffset = Vector2(boxBorderThickness, boxBorderThickness)
		pg.draw.rect(self.screen, (255, 255, 255), (*(boxPos-borderOffset), *(boxSize+borderOffset)), boxBorderThickness)

		# Converts index values from board space coordinates (10x20) as integer tuples into screenspace coordinates as pygame.Vector2
		# Iterates through separator ending positions and draws them on the screen
		horizontalSeparators :list[Vector2]= list(map(lambda x: (Vector2(x)*self.playingElements['minoSize']), zip([10 for x in range(20)], range(20))))
		for position in horizontalSeparators:
			pg.draw.line(self.screen, (255, 255, 255), boxPos+Vector2(0, position.y), boxPos+position, cellSeparatorThickness)
		verticalSeparators :list[Vector2]= list(map(lambda x: (Vector2(x)*self.playingElements['minoSize']), zip(range(10), [20 for x in range(10)])))
		for position in verticalSeparators:
			pg.draw.line(self.screen, (255, 255, 255), boxPos+Vector2(position.x, 0), boxPos+position, cellSeparatorThickness)

		
		for j in range(len(board)):
			for i in range(len(board[j])):
				if board[j][i] != '-':
					tup = boxPos + Vector2(i, j)*self.playingElements['minoSize']
					image = self.typeToImage[board[j][i].upper()]
					self.screen.blit(image, (tup[0], tup[1], 40, 40))

	def drawPiece(self, game :Game, elements :dict):
		boxPos = elements['boxPos']
		boxPos = Vector2(boxPos)

		

		# draws shadow of piece
		shadowAnchorY = game.calcShadowPos()
		pieceType, pieceRot = game.metaIdToTypeAndRot[game.activePiece]
		for cellX, cellY in list(map(lambda x: ((15-x)%4, (15-x)//4), game.metaIdToActiveBits[game.activePiece])):
			if game.updateDisplayedBoard()[shadowAnchorY+cellY][game.anchorX+cellX] != '-':
				continue
			tup = boxPos + Vector2(game.anchorX+cellX, shadowAnchorY+cellY)*self.playingElements['minoSize']
			self.screen.blit(self.typeToShadowImage[pieceType], (*tup, *Vector2(self.playingElements['minoSize'], self.playingElements['minoSize'])))

	def drawFrameRate(self):
		fps = self.fpsSum / self.maxFrameHistory

		font = pg.font.SysFont("Arial", 36)
		fps_text = font.render(f"FPS: {fps:.2f}", 1, (255,255,255))

		self.screen.blit(fps_text, (10, 10))


	def drawHighScores(self, elements :dict):
		garbage, headerFontSize, listFontSize, boxSize, boxBorderThickness, boxBorderRadius, lineSeparatorPos, lineSeparatorThickness, elementSpacing \
		= elements.values()

		screenSize = Vector2(self.screen.get_rect().size)
		boxSize = Vector2(boxSize)

		# box is centered on screen, so values are in absolute space
		# draws the rounded rectangle for the given box
		pg.draw.rect(self.screen, (255, 255, 255), (*((screenSize-boxSize)/2), *boxSize), boxBorderThickness, boxBorderRadius)
		pg.draw.line(self.screen, (255, 255, 255), *(((screenSize-boxSize)/2)+Vector2(x) for x in lineSeparatorPos), lineSeparatorThickness)

		boxPos = screenSize - boxSize

		headerFont = pg.font.Font('./assets/font.ttf', headerFontSize).render("Highscores", 1, (255, 255, 255))
		listFont = pg.font.Font('./assets/font.ttf', listFontSize)
		self.screen.blit(headerFont, (
			boxPos \
			 + Vector2(boxSize[0], 2*boxBorderThickness+lineSeparatorPos[0][1]-lineSeparatorThickness/2) \
			 - Vector2(headerFont.get_rect().size)
			)/2)

		targetWidth = int((boxSize[0]-lineSeparatorPos[0][1])//listFontSize)
		for i in range(min(int((boxSize[1]-lineSeparatorPos[0][1])//listFontSize), len(self.highscores))):
			paddingWidth = targetWidth-len(f"{self.highscores[i][0]}")-len(f"{self.highscores[i][1]}")
			outString = f"{self.highscores[i][0]}"+"."*paddingWidth+f"{self.highscores[i][1]}"
			leaderBoardFont = listFont.render(outString, 1, (255, 255, 255))
			indexOffset = Vector2(0, listFontSize*i+elementSpacing)
			self.screen.blit(leaderBoardFont, (
				boxPos \
				+ Vector2(boxSize[0], 2*(boxBorderThickness+lineSeparatorPos[0][1]+lineSeparatorThickness)) \
				- Vector2(leaderBoardFont.get_rect().size) \
				)/2 \
				+ indexOffset)


	def drawInitialsInput(self, elements :dict):
		garbage, headerFontSize, inputFontSize, boxSize, boxBorderThickness, boxBorderRadius, lineSeparatorPos, lineSeparatorThickness \
		= elements.values()
		
		screenSize = Vector2(self.screen.get_rect().size)
		boxSize = Vector2(boxSize)
		boxPos = screenSize - boxSize

		# box is centered on screen, so values are in absolute space
		# draws the rounded rectangle for the given box
		pg.draw.rect(self.screen, (255, 255, 255), (*((screenSize-boxSize)/2), *boxSize), boxBorderThickness, boxBorderRadius)
		pg.draw.line(self.screen, (255, 255, 255), *(((screenSize-boxSize)/2)+Vector2(x) for x in lineSeparatorPos), lineSeparatorThickness)
		

		headerFontTop = pg.font.Font('./assets/font.ttf', headerFontSize).render("Enter", 1, (255, 255, 255))
		headerFontBot = pg.font.Font('./assets/font.ttf', headerFontSize).render("your name!", 1, (255, 255, 255))
		self.screen.blit(headerFontTop, (
			screenSize \
			- boxSize \
			+ Vector2(lineSeparatorPos[1]) \
			+ Vector2(0, 2*boxBorderThickness-lineSeparatorThickness-headerFontTop.get_rect().size[1]) \
			- headerFontTop.get_rect().size
			)/2)
		self.screen.blit(headerFontBot, (
			screenSize \
			- boxSize \
			+ Vector2(lineSeparatorPos[1]) \
			+ Vector2(0, 2*boxBorderThickness-lineSeparatorThickness+headerFontBot.get_rect().size[1]) \
			- headerFontBot.get_rect().size
			)/2)

		inputText = self.initialsText + "_"*(3-len(self.initialsText))
		initialsFont = pg.font.Font('./assets/font.ttf', inputFontSize).render(inputText, 1, (255, 255, 255))
		self.screen.blit(initialsFont, (
				boxPos \
				+ Vector2(boxSize[0], boxSize[1]+(lineSeparatorPos[0][1]+lineSeparatorThickness-boxBorderThickness))
				- Vector2(initialsFont.get_rect().size) \
				)/2)


	def drawWindow(self, game :Game):
		w, h = self.screen.get_rect().size
		match game.state:
			case GameStates.playing:
				self.screen.fill((0, 0, 0))
				
				# pythonic way to execute respective functions with respective arguments
				# needs to be changed to accommodate multiple games
				[self.drawHold(game, holdElements) for holdElements in self.playingElements['hold']]
				[self.drawNextlist(game, nextlistElements) for nextlistElements in self.playingElements['nextlist']]
				[self.drawLevel(game, levelElements) for levelElements in self.playingElements['level']]
				[self.drawScore(game, scoreElements) for scoreElements in self.playingElements['score']]
				[self.drawBoard(game, boardElements) for boardElements in self.playingElements['board']]
				[self.drawPiece(game, shadowElements) for shadowElements in self.playingElements['piece']]

			case GameStates.menu:
				# guard clause used to examine the board for debugging
				if self.debug:
					return
				self.screen.fill((0, 0, 0))
				menuText = pg.font.SysFont('calibri', self.menuElements['fontSize']).render("Paused, Esc to unpause", 1, (255, 255, 255))
				self.screen.blit(menuText, (((w - menuText.get_width())/2 , (h - menuText.get_height())/2)))


			case GameStates.countdown:
				self.screen.fill((0, 0, 0))
				countdownText = pg.font.SysFont('calibri', self.countdownElements['fontSize']).render(f"Starting in: {math.ceil(game.countdownTimer)}", 1, (255, 255, 255))
				self.screen.blit(countdownText, ((w - countdownText.get_width())/2 , (h - countdownText.get_height())/2))

			case GameStates.gameover:
				self.screen.fill((0, 0, 0))
				self.drawHighScores(self.gameoverElements)
				
				# self.drawHighScores(self.gameoverElements)
			case GameStates.initialsInput:
				self.screen.fill((0, 0, 0))
				self.drawInitialsInput(self.initialsInputElements)


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
		# pprint.pprint(self.resolutionPreset)

		self.playingElements = self.resolutionPreset['playing']
		self.menuElements = self.resolutionPreset['menu']
		self.countdownElements = self.resolutionPreset['countdown']
		self.gameoverElements = self.resolutionPreset['gameover']
		self.initialsInputElements = self.resolutionPreset['initialsInput']


		minoSize = self.playingElements['minoSize']
		self.typeToImage = {
			'I': pg.transform.scale(pg.image.load('./assets/i.png'), (minoSize, minoSize)),
			'J': pg.transform.scale(pg.image.load('./assets/j.png'), (minoSize, minoSize)),
			'L': pg.transform.scale(pg.image.load('./assets/l.png'), (minoSize, minoSize)),
			'S': pg.transform.scale(pg.image.load('./assets/s.png'), (minoSize, minoSize)),
			'Z': pg.transform.scale(pg.image.load('./assets/z.png'), (minoSize, minoSize)),
			'O': pg.transform.scale(pg.image.load('./assets/o.png'), (minoSize, minoSize)),
			'T': pg.transform.scale(pg.image.load('./assets/t.png'), (minoSize, minoSize)),
		}

		self.typeToShadowImage = {}
		for k, v in self.typeToImage.items():
			shadowTexture = pg.Surface(pg.Vector2(minoSize, minoSize), pg.SRCALPHA, 32)

			skew = 1
			swatch = v.get_at((minoSize//2, minoSize//2))
			shadowColor = pg.Color([x*y for x, y in zip(swatch, [skew, skew, skew])])
			
			pg.draw.polygon(shadowTexture, shadowColor, [pg.Vector2( 1,  1), pg.Vector2( 3,  3), pg.Vector2(minoSize-3,  3), pg.Vector2(minoSize-1,  1)])
			pg.draw.polygon(shadowTexture, shadowColor, [pg.Vector2( 1,  1), pg.Vector2( 3,  3), pg.Vector2( 3, minoSize-3), pg.Vector2( 1, minoSize-1)])
			pg.draw.polygon(shadowTexture, shadowColor, [pg.Vector2(minoSize-1,  1), pg.Vector2(minoSize-3,  3), pg.Vector2(minoSize-3, minoSize-3), pg.Vector2(minoSize-1, minoSize-1)])
			pg.draw.polygon(shadowTexture, shadowColor, [pg.Vector2(minoSize-1, minoSize-1), pg.Vector2(minoSize-3, minoSize-3), pg.Vector2( 3, minoSize-3), pg.Vector2( 1, minoSize-1)])

			self.typeToShadowImage[k] = shadowTexture

class Controller:
	def startSinglePlayer():
		disp = Display(1200, 900)
		disp.perKeyTickCache = {}

		run = True
		game = Game(True)

		disp.pseudoFrameCount = 0
		disp.pseudoFrameCountDelta = 0
		disp.pseudoFrameCountLastTrigger = 0
		disp.fpsHistory = []
		disp.fpsSum = 0.0

		disp.fTimeElapsed = 0

		disp.pause = False
		disp.debug = False


		while run:
			dt = disp.clock.tick_busy_loop()/1000

			disp.drawWindow(game)
			pg.display.update()

			for e in pg.event.get():
				if e.type == pg.QUIT:
					pg.quit()
					quit()
				if e.type == pg.KEYDOWN:
					match game.state:
						case GameStates.menu:
							if e.key == pg.K_ESCAPE:
								game.state = GameStates.countdown
								timerList = [3.0, 0.0]
								game.countdownTimer = timerList[int(disp.debug)]
							
						case GameStates.playing:
							if e.key == pg.K_ESCAPE:
								game.state = GameStates.menu
								if game.canPlayMusic:game.themeSong.stop()
						
						case GameStates.gameover:
							if e.key == pg.K_SPACE:
								game.state = GameStates.countdown
								game.countdownTimer = 3.0
						
						case GameStates.initialsInput:
							if e.key == pg.K_BACKSPACE:
								if len(disp.initialsText) > 0:
									disp.initialsText = disp.initialsText[:-1]
							if e.key == pg.K_ESCAPE:
								with open("./logs/gamelogs.yaml", 'r+') as f:
									file :dict= yaml.safe_load(f)
									out = []
									for id, g in file.items():
										out.append((g['Initials'], g['Score']))
									
									disp.highscores = sorted(out, key=lambda x: x[1], reverse=True)
								game.state = GameStates.gameover
								game.countdownTimer = 3.0
							elif e.key == pg.K_RETURN:
								if len(disp.initialsText) == 3:
									game.state = GameStates.gameover
									game.countdownTimer = 4.0
									with open("./logs/gamelogs.yaml", 'r+') as f:
										file :dict= yaml.safe_load(f)
										f.seek(0)
										file.update({
											f"Game @ {datetime.datetime.now()}": {
												"Total Gametime": str(datetime.timedelta(seconds=game.fTimeElapsed)),
												"Total Lines": game.totalLines,
												"Level": game.totalLines//10,
												"Score": game.score,
												"Drought at Game Over": game.droughtCounter,
												"Initials": disp.initialsText.upper(),
											}
										})
										# set highscores for displaying in next game-state
										out = []
										for id, g in file.items():
											out.append((g['Initials'], g['Score']))
										
										disp.highscores = sorted(out, key=lambda x: x[1], reverse=True)


										yaml.safe_dump(file, f)
							elif len(disp.initialsText) != 3:
								# Append the pressed key to the input text
								assert isinstance(e.unicode, str)

								if e.unicode.isalnum():
									disp.initialsText += e.unicode

					if e.key == pg.K_p: # debug key
						disp.debug = not disp.debug
					if e.key == pg.K_F12:
						pg.image.save(disp.screen, f"./screenshots/{datetime.datetime.now()}.png")
					if game.state != GameStates.playing:
						continue
					if e.key == pg.K_c:
						game.holdActivePiece()
						disp.pseudoFrameCountDelta -= disp.pseudoFrameCount % disp.pseudoFramesByLevel(game.totalLines//10) + 1

			match game.state:

				case GameStates.playing:
					disp.fTimeElapsed += dt
					disp.pseudoFrameCount = math.floor(disp.fTimeElapsed*disp.pseudoFramesPerSecond)
					game.fTimeElapsed = disp.fTimeElapsed
					if dt == 0.0: dt = 0.001
					
					fps = round(1/max(0.001,dt))
					disp.fpsHistory.append(fps)
					disp.fpsSum += fps

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
						disp.pseudoFrameCountDelta = disp.pseudoFrameCount % disp.pseudoFramesByLevel(game.totalLines//10)-1

					if disp.checkIfKeyShouldExec(pg.K_SPACE, keys):
						game.dropActivePieceDown()
						disp.pseudoFrameCountDelta = disp.pseudoFrameCount % disp.pseudoFramesByLevel(game.totalLines//10)-1

					if ((disp.pseudoFrameCount+disp.pseudoFrameCountDelta) % disp.pseudoFramesByLevel(game.totalLines//10)) == 0 and (disp.pseudoFrameCount+disp.pseudoFrameCountDelta) != disp.pseudoFrameCountLastTrigger:
						disp.pseudoFrameCountLastTrigger = (disp.pseudoFrameCount+disp.pseudoFrameCountDelta)
						game.stepActivePieceDown()

				case GameStates.menu:
					pass
				
				case GameStates.initialsInput:
					pass

				case GameStates.countdown:
					game.countdownTimer -= dt
					if game.countdownTimer <= 0:
						game.state = GameStates.playing
						if game.canPlayMusic: game.themeSong.play(loops=-1)
												

				case GameStates.gameover:
					disp.initialsText = ''
					game.countdownTimer -= dt
					if game.countdownTimer <= 0:
						game = Game(game.isEasymode)
						game.state = GameStates.gameover


if __name__ == "__main__":
	Controller.startSinglePlayer()
