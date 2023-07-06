class SignalEdge:
	idKV = {}

	def getRisingEdge(bool :bool, uniqueID):
		if bool and (uniqueID in SignalEdge.idKV and not SignalEdge.idKV[uniqueID]):
			SignalEdge.idKV[uniqueID] = True
			return True
		if not bool:
			SignalEdge.idKV[uniqueID] = False
		return False
	
	def getFallingEdge(bool :bool, uniqueID):
		if not bool and (uniqueID in SignalEdge.idKV and not SignalEdge.idKV[uniqueID]):
			SignalEdge.idKV[uniqueID] = True
			return True
		if bool:
			SignalEdge.idKV[uniqueID] = False
		return False
