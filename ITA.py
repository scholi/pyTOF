from pyTOF import Block
import numpy as np
import struct
import os.path
import zlib
import re

class ITA:
	def __init__(self, filename):
		self.filename = filename
		assert os.path.exists(filename)
		self.f = open(self.filename, 'rb')
		self.Type = self.f.read(8)
		assert self.Type == b'ITStrF01'
		self.root = Block.Block(self.f)
		self.getMassInt()

	def getMassInt(self):
		R=[z for z in self.root.goto('MassIntervalList').getList() if z['name'].decode()=='mi']
		N=len(R)
		self.peaks={}
		for i in range(N):
			try:
				X = self.root.goto('MassIntervalList/mi['+str(i)+']')
				d = X.dictList()
				self.peaks[d[b'id']['long']]=d
			except ValueError:
				pass

	def getChannelsByName(self, name):
		res=[]
		for P in self.peaks:
			p=self.peaks[P]
			ma=re.compile(name,re.I+re.U)
			if ma.match(p[b'assign']['utf16']) or ma.match(p[b'desc']['utf16']):
				res.append(p)
		return res

	def getChannelByMass(self, mass):
		for P in self.peaks:
			p=self.peaks[P]
			if p[b'id']['long']>1 and p[b'lmass']['float']<=mass and mass<=p[b'umass']['float']:
				return p[b'id']['long']
		return None
			
	def showMassInt(self):
			for P in self.peaks:
				p=self.peaks[P]
				print(p[b'id']['long'],p[b'desc']['utf16'],p[b'assign']['utf16'],p[b'lmass']['float'],p[b'cmass']['float'],p[b'umass']['float'])

	def getSize(self):
		X = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.XSize').getLong()
		Y = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.YSize').getLong()
		return X,Y

	def getNScans(self):
		return self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.NumberOfScans').getLong()
	
	def getNImages(self):
		Nimg = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.NumberOfImages').getLong()

	def getImage(self, channel, scan):
		assert type(channel) == int
		assert type(scan) == int
		Nscan = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.NumberOfScans').getLong()
		Nimg = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.NumberOfImages').getLong()
		assert channel>=0 and channel<Nimg
		assert scan>=0 and scan<Nscan
		X,Y = self.getSize()
		c = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image['+str(channel)+']/ImageArray.Long['+str(scan)+']')
		D = zlib.decompress(c.value)
		V = np.array(struct.unpack('<'+str(X*Y)+'I',D)).reshape((Y,X))
		return V
