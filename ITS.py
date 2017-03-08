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
		V   = self.root.goto('filterdata/TofCorrection/Spectrum/Reduced Data/IMassScaleSFK0')
		sf  = V.goto('sf').getDouble()
		k0  = V.goto('k0').getDouble()
		chW = V.goto('channelwidth').getDouble()*1e-6
		masses = ((ch+k0)/(sf/2))**2
		return masses,np.array(struct.unpack('<'+str(N)+'f',X))
