from pyTOF import Block
import numpy as np
import struct
import os.path
import zlib
import re

class ITS:
	def __init__(self, filename):
		self.filename = filename
		assert os.path.exists(filename)
		self.f = open(self.filename, 'rb')
		self.Type = self.f.read(8)
		assert self.Type == b'ITStrF01'
		self.root = Block.Block(self.f)

	def getSpectra(self, ID=0):
		X = zlib.decompress(self.root.goto('DataCollection/{ID}/Reduced Data/IITFSpecArray/CorrectedData'.format(ID=ID)).value)
		N=len(X)//4
		ch = np.arange(N)
		# The channel-mass conversion was found empirically from data
		# There is no guarenty that this will be correct for all Data!!!
		masses = np.polyval([8.75206913e-10,1.82528185e-06,9.51676243e-04],ch)
		return masses,np.array(struct.unpack('<'+str(N)+'f',X))
