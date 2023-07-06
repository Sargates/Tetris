class RepeatedPrint:
	def formattedRP(out :str = "") -> None:
		"Just meant print variables without repeated spam in console, automatically appends '\033[A' (control character to recede print head)"
		numLines = len(out.replace('\t', '').strip().split('\n'))
		print(out.replace('\t', '').strip(), end='\033[A'*(numLines-1)+"\r")