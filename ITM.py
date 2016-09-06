from ionTOF import Block
import numpy as np
import struct
import os.path
import zlib
import re

class ITM:
	def __init__(self, filename):
		self.filename = filename
		assert os.path.exists(filename)
		self.f = open(self.filename, 'rb')
		self.Type = self.f.read(8)
		assert self.Type == b'ITStrF01'
		self.root = Block.Block(self.f)

	def getSize(self):
		d=self.root.goto('LateralShiftCorrection').dictList()
		return {
			'pixels':{
				'X':d[b'ImageStack.Raster.Resolution.X']['long'],
				'Y':d[b'ImageStack.Raster.Resolution.Y']['long']},
			'real':{
				'X':d[b'ImageStack.FieldOfView.X']['float'],
				'Y':d[b'ImageStack.FieldOfView.Y']['float']},
			'Scans':d[b'ImageStack.NumberOfShiftCoordinates']['long']}

	def getIntensity(self):
			S = self.getSize()
			X,Y = S['pixels']['X'],S['pixels']['Y']
			return np.array(struct.unpack('<'+str(X*Y)+'I',zlib.decompress(self.root.goto('Meta/SI Image/intensdata').value))).reshape((Y,X))
