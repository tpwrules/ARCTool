import struct
import sys
import os
from optparse import OptionParser

def openOutput(f):
	try:
		return open(f, "wb")
	except IOError:
		print "Output file could not be opened!"
		exit()

def makedir(dirname):
	global quiet
	try:
		os.mkdir(dirname)
	except OSError, e:
		if quiet == False:
			print "WARNING: Directory", dirname, "already exists!"

class rarc_header_class:
	_structformat = ">I4xI16xI8xI4xI8x"
	filesize = 0
	#4 bytes unknown
	dataStartOffset = 0 #where does actual data start? add 0x20
	#16 bytes unknown
	numNodes = 0
	#8 bytes unknown
	fileEntriesOffset = 0
	#4 bytes unknown
	stringTableOffset = 0 # where is the string table stored? add 0x20
	#8 bytes unknown
	def __init__(self):
		self._s = struct.Struct(self._structformat)
	def unpack(self, buf):
		s = self
		s.filesize, s.dataStartOffset, s.numNodes, s.fileEntriesOffset, s.stringTableOffset = s._s.unpack_from(buf)
	def size(self):
		#print self._s.size, "ohai"
		return self._s.size

class rarc_node_class:
	_structformat = ">II2xHI"
	type = 0
	filenameOffset = 0 #directory name, offset into string table
	#2 bytes unknown
	numFileEntries = 0 #how manu files belong to this node?
	firstFileEntryOffset = 0
	def __init__(self):
		self._s = struct.Struct(self._structformat)
	def unpack(self, buf):
		s = self
		s.type, s.filenameOffset, s.numFileEntries, s.firstFileEntryOffset = s._s.unpack_from(buf)
	def size(self):
		#print self._s.size
		return self._s.size

class rarc_fileEntry_class:
	_structformat = ">H4xHII4x"
	id = 0 #file id. if 0xFFFF, this entry is a subdir link
	#4 bytes unknown
	filenameOffset = 0 #file/subdir name, offset into string table
	dataOffset = 0 #offset to file data (for subdirs: index of node representing subdir)
	dataSize = 0 #size of data
	def __init__(self):
		self._s = struct.Struct(self._structformat)
	def unpack(self, buf):
		s = self
		s.id, s.filenameOffset, s.dataOffset, s.dataSize = s._s.unpack_from(buf)
	def size(self):
		return self._s.size

class U8_archive_header:
	_structformat = ">III16x"
	rootnode_offset = 0 #offset to root_node, always 0x20
	header_size = 0 #size of header from root_node to end of string table
	data_offset = 0 #offset to data: rootnode_offset + header_size aligned to 0x40
	#16 bytes zeros
	def __init__(self):
		self._s = struct.Struct(self._structformat)
	def unpack(self, buf):
		s = self
		s.rootnode_offset, s.header_size, s.data_offset = s._s.unpack_from(buf)
	def size(self):
		return self._s.size
		
class U8_node:
	_structformat = ">HHII"
	type = 0 #really u8, normal files = 0x0000, directories = 0x0100
	name_offset = 0 #really 'u24'
	data_offset = 0
	fsize = 0 #files: filesize, dirs: last included file with rootnode as 1
	def __init__(self):
		self._s = struct.Struct(self._structformat)
	def unpack(self, buf):
		s = self
		s.type, s.name_offset, s.data_offset, s.fsize = s._s.unpack_from(buf)
	def size(self):
		return self._s.size

class U8_globals:
	pass
	
def unyaz(input, output):
	global quiet, list
	#shamelessly stolen^W borrowed from yagcd
	data_size, = struct.unpack_from(">I", input.read(4)) #uncompressed data size
	if list:
		print "Uncompressed size:", data_size, "bytes"
		return
	t = input.read(8) #dummy
	srcplace = 0
	dstplace = 0
	bitsleft = 0
	currbyte = 0
	if quiet == False:
		print "Reading input"
	src = input.read()
	dst = [" "]*data_size
	#print len(dst), len(src)
	percent = 0
	if quiet == False:
		sys.stdout.write("Decompressing  0%")
		sys.stdout.flush()
	while dstplace < data_size:
		if bitsleft == 0:
			currbyte = ord(src[srcplace])
			srcplace += 1
			bitsleft = 8
		if (currbyte & 0x80) != 0:
			dst[dstplace] = src[srcplace]
			dstplace += 1
			srcplace += 1
		else:
			byte1 = ord(src[srcplace])
			byte2 = ord(src[srcplace+1])
			srcplace += 2
			dist = ((byte1 & 0xF) << 8) | byte2
			copySource = dstplace - (dist + 1)
			numbytes = byte1 >> 4
			if numbytes == 0:
				numbytes = ord(src[srcplace]) + 0x12
				srcplace += 1
			else:
				numbytes += 2
			j = 0
			for i in range(0, numbytes):
				dst[dstplace] = dst[copySource]
				copySource += 1
				dstplace += 1
				j += 1
		currbyte = (currbyte << 1)
		bitsleft -= 1
		if quiet == False:
			calcpercent = ((dstplace*1.0)/data_size)*100
			if int(calcpercent) > percent:
				if int(calcpercent) > 9:
					sys.stdout.write("\b")
				sys.stdout.write("\b\b" + str(int(calcpercent)) + "%")
				sys.stdout.flush()
				percent = calcpercent
	if quiet == False:
		print "\nWriting output"
	output.write("".join(dst))

def getNode(index, f, h):
	retval = rarc_node_class()
	f.seek(h.size() + 4 + index*retval.size())
	s = f.read(retval.size())
	retval.unpack(s)
	return retval

def getString(pos, f):
	t = f.tell()
	f.seek(pos)
	retval = []
	char = 0
	while True:
		char = f.read(1)
		if char == "\0":
			break
		retval.append(char)
	f.seek(t)
	return "".join(retval)

def getFileEntry(index, h, f):
	retval = rarc_fileEntry_class()
	f.seek(h.fileEntriesOffset + index*retval.size() + 0x20)
	retval.unpack(f.read(retval.size()))
	return retval

def processNode(node, h, f):
	global quiet, depthnum, list
	nodename = getString(node.filenameOffset + h.stringTableOffset + 0x20, f)
	if list == False:
		if quiet == False:
			print "Processing node", nodename
		makedir(nodename)
		os.chdir(nodename)
	else:
		print ("  "*depthnum) + nodename + "/"
		depthnum += 1
	for i in range(0, node.numFileEntries):
		currfile = getFileEntry(node.firstFileEntryOffset + i, h, f)
		currname = getString(currfile.filenameOffset + h.stringTableOffset + 0x20, f)
		if (currfile.id == 0xFFFF): #file is a subdir
			if currname != "." and currname != "..": # don't go to "." and ".."
				processNode(getNode(currfile.dataOffset, f, h), h, f)
		else:
			if list:
				print ("  "*depthnum) + currname, "-", currfile.dataSize
				continue
			if quiet == False:
				print "Dumping", nodename + "/" + currname, " 0%",
			try:
				percent = 0
				dest = open(currname, "wb")
				f.seek(currfile.dataOffset + h.dataStartOffset + 0x20)
				size = currfile.dataSize
				while size > 0:
					if quiet == False:
						calcpercent = int(((currfile.dataSize-size)/(currfile.dataSize*1.0))*100)
						calcpercent = int(calcpercent)
						if calcpercent > percent:
							if calcpercent > 9:
								sys.stdout.write("\b")
							sys.stdout.write("\b\b" + str(calcpercent) + "%")
							sys.stdout.flush()
							percent = calcpercent
					dest.write(f.read(size))
					size -= 1024
				if quiet == False:
					if percent > 9:
						sys.stdout.write("\b")
					sys.stdout.write("\b\b100%")
					print ""
				dest.close()
			except IOError:
				print "OMG SOMETHING WENT WRONG!!!!1111!!!!!"
				exit()
	if list == False:
		os.chdir("..")
	else:
		depthnum -= 1

def unrarc(i, o):
	global list
	header = rarc_header_class()
	header.unpack(i.read(header.size()))
	if list == False:
		try:
			makedir(o)
		except:
			pass
		os.chdir(o)
	processNode(getNode(0, i, header), header, i)

def get_u8_name(i, g, node):
	retval = []
	i.seek(g.string_table + node.name_offset-1)
	while True:
		t = i.read(1)
		if t == "\0":
			break
		retval.append(t)
	return "".join(retval)

def get_u8_node(i, g, index):
	retval = U8_node()
	index -= 1
	i.seek(g.header.rootnode_offset + (index * retval.size()))
	retval.unpack(i.read(retval.size()))
	return retval
	
def unu8(i, o):
	global quiet, depthnum, list
	header = U8_archive_header()
	header.unpack(i.read(header.size()))
	if list == False:
		try:
			makedir(o)
		except:
			pass
		os.chdir(o)
	root = U8_node()
	root.unpack(i.read(header.size()))
	g = U8_globals()
	g.rootnode = root
	g.numnodes = root.fsize
	g.header = header
	g.string_table = ((root.fsize)*root.size()) + header.rootnode_offset + 1
	depth = [root.fsize]
	for index in range(2, root.fsize+1):
		node = get_u8_node(i, g, index)
		name = get_u8_name(i, g, node)
		if list:
			if node.type == 0:
				print ("  "*depthnum) + name, "-", node.fsize, "bytes"
			elif node.type == 0x0100:
				print ("  "*depthnum) + name + "/"
				depthnum += 1
				depth.append(node.fsize)
		elif node.type == 0:
			if quiet == False:
				print "Dumping file node", name, " 0%",
			i.seek(node.data_offset)
			try:
				dest = open(name, "wb")
				percent = 0
				size = node.fsize
				while size > 0:
					if quiet == False:
						calcpercent = int(((node.fsize-size)/(node.fsize*1.0))*100)
						if calcpercent > percent:
							if calcpercent > 9:
								sys.stdout.write("\b")
							sys.stdout.write("\b\b" + str(calcpercent) + "%")
							sys.stdout.flush()
							percent = calcpercent
					dest.write(f.read(size))
					size -= 1024
				if quiet == False:
					if percent > 9:
						sys.stdout.write("\b")
					sys.stdout.write("\b\b100%\n")
				dest.close()
			except IOError:
				print "OMG SOMETHING WENT WRONG!!!!!!!111111111!!!!!!!!"
				exit()
		elif node.type == 0x0100:
			if quiet == False:
				print "Processing node", name
			makedir(name)
			os.chdir(name)
			depth.append(node.fsize)
		if index == depth[-1]:
			if list == False:
				os.chdir("..")
			depthnum -= 1
			depth.pop()
	if list == False:
		os.chdir("..")

def main():
	global of, quiet, list, depthnum
	parser = OptionParser(usage="python %prog [-q] [-o <output>] <inputfile> [inputfile2] ... [inputfileN]", version="ARCTool 0.3b")
	parser.add_option("-o", "--output", action="store", type="string", dest="of", help="write output to FILE/DIR. If you are extracting multiple archives, all of them will be put in this dir.", metavar="FILE/DIR")
	parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False, help="don't print anything (except errors)")
	parser.add_option("-l", "--list", action="store_true", dest="list", default=False, help="print a list of files contained in the specified archive (ignores -q)")
	
	
	(options, args) = parser.parse_args()
	
	of = options.of
	quiet = options.quiet
	list = options.list
	
	depthnum = 0
	
	if len(args) < 1:
		parser.error("Input filename required")
	
	if len(args) > 1:
		if options.of != None:
			makedir(of)
			os.chdir(of)
		
	for file in args:
		if options.of == None or len(args) > 1:
			of = os.path.split(file)[1] + ".extracted"
		if len(args) > 1 and options.of != None:
			file = "../" + file
		try:
			f = open(file, "rb")
		except IOError:
			print "Input file could not be opened!"
			exit()
		type = f.read(4)
		if type == "Yaz0":
			if quiet == False:
				print "Yaz0 compressed archive"
			unyaz(f, openOutput(of))
		elif type == "RARC":
			if quiet == False:
				print "RARC archive"
			unrarc(f, of)
		elif type == "U\xAA8-":
			if quiet == False:
				print "U8 archive"
			unu8(f, of)
		else:
			print "Unknown archive type!"
			exit()
		f.close()
	
if __name__ == "__main__":
	main()
