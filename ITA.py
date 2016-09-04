import Block
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
		R=[z for z in self.root.goto('MassIntervalList').List if z['name']=='mi']
		N=len(R)
		self.peaks={}
		for i in range(N):
			try:
				d=self.root.goto('MassIntervalList/mi['+str(i)+']').dictList()
				self.peaks[d['id']['long']]=d
			except: pass

	def getChannelByName(self, name):
		for P in self.peaks:
			p=self.peaks[P]
			ma=re.compile(name,re.I+re.U)
			if ma.match(p['assign']['utf16']) or ma.match(p['desc']['utf16']):
				return p['id']['long']
		return None

	def getChannelByMass(self, mass):
		for P in self.peaks:
			p=self.peaks[P]
			if p['id']['long']>1 and p['lmass']['float']<=mass and mass<=p['umass']['float']:
				return p['id']['long']
		return None
			
	def showMassInt(self):
			for P in self.peaks:
				p=self.peaks[P]
				print(p['id']['long'],p['desc']['utf16'],p['assign']['utf16'],p['lmass']['float'],p['cmass']['float'],p['umass']['float'])

	def getSize(self):
		X = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.XSize').getLong()
		Y = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.YSize').getLong()
		return X,Y

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
