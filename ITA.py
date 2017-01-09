from pyTOF import Block
import numpy as np
import struct
import os.path
import zlib
import re
import scipy

class ITA:
	def __init__(self, filename):
		self.filename = filename
		assert os.path.exists(filename)
		self.f = open(self.filename, 'rb')
		self.Type = self.f.read(8)
		assert self.Type == b'ITStrF01'
		self.root = Block.Block(self.f)
		self.getMassInt()
		self.sx = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.XSize').getLong()
		self.sy = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.YSize').getLong()
		self.Nscan = int(self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.NumberOfScans').getLong())
		self.Nimg = int(self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image.NumberOfImages').getLong())

	def getMassInt(self):
		R=[z for z in self.root.goto('MassIntervalList').getList() if z['name'].decode()=='mi']
		N=len(R)
		self.peaks={}
		for x in R:
			try:
				X = self.root.goto('MassIntervalList/mi['+str(x['id'])+']')
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
	
	def showPeaks(self):
		self.getMassInt()
		for p in self.peaks:
			P={k.decode('utf8'):self.peaks[p][k] for k in self.peaks[p]}
			print("{0}) {peaklabel}".format(p,**P))

	def getChannelByMass(self, mass):
		for P in self.peaks:
			p=self.peaks[P]
			if p[b'id']['long']>1 and p[b'lmass']['float']<=mass and mass<=p[b'umass']['float']:
				return p[b'id']['long']
		return 0
			
	def showMassInt(self):
			for P in self.peaks:
				p=self.peaks[P]
				print(p[b'id']['long'],p[b'desc']['utf16'],p[b'assign']['utf16'],p[b'lmass']['float'],p[b'cmass']['float'],p[b'umass']['float'])

	def getSumImageByName(self, names, scans=None, prog=False, **kargs):
		if scans is None:
			scans = range(self.Nscan)
		if type(scans)==int: scans=[scans]
		Z = np.zeros((self.sy,self.sx))
		channels = self.getChannelsByName(names)
		if prog:
			from tqdm import tqdm
			scans=tqdm(scans)
		for s in scans:
			for ch in channels:
				ID = ch[b'id']['long']
				Z+=self.getImage(ID,s,**kargs)
		return Z,channels

	def getShiftsByMass(self, masses, centered=True, prog=False, Filter=None):
		Shifts=[(0,0)]
		if Filter is None: Filter=lambda z: z
		S0 = Filter(self.getSumImageByMass(masses,0))
		Y = range(1,self.Nscan)
		if prog:
			from tqdm import tqdm
			Y=tqdm(Y)
		for i in Y:
			S = Filter(self.getSumImageByMass(masses,i))
			Shift = np.real( np.fft.fftshift( np.fft.ifft2( np.conj(np.fft.fft2(S0)) * np.fft.fft2(S) ) ) )
			cord = np.unravel_index(np.argmax(Shift),S0.shape)
			trans = (cord[1]-S0.shape[1]/2,cord[0]-S0.shape[0]/2)
			Shifts.append(trans)
		if centered:
			avSx = np.round(np.mean([z[0] for z in Shifts]))
			avSy = np.round(np.mean([z[1] for z in Shifts]))
			Shifts = [(z[0]-avSx,z[1]-avSy) for z in Shifts]
		return Shifts

	def getXsectionByMass(self, x1, y1, x2, y2, masses, N=None, prog=False, **kargs):
		if N is None: N = int(np.sqrt((x2-x1)**2+(y2-y1)**2))+1
		x=np.linspace(x1,x2,N)
		y=np.linspace(y1,y2,N)
		out=np.zeros((self.Nscan,N))
		Y=range(self.Nscan)
		if prog:
			from tqdm import tqdm
			Y=tqdm(Y)
		for s in Y:
			Z = self.getSumImageByMass(masses,s,**kargs)
			P = scipy.ndimage.map_coordinates(Z,np.vstack((y,x)))
			out[s,:] = P
		return out
	
	def getSumImageByMass(self, masses, scans=None, prog=False, **kargs):
		if scans is None:
			scans = range(self.Nscan)
		if type(scans)==int: scans = [scans]
		if type(masses)==int or type(masses) == float: masses=[masses]
		Z = np.zeros((self.sy,self.sx))
		if prog:
			from tqdm import tqdm
			scans=tqdm(scans)
		for s in scans:
			assert s>=0 and s<self.Nscan
			for m in masses:
				ch = self.getChannelByMass(m)
				Z+=self.getImage(ch,s,**kargs)
		return Z

	def getImage(self, channel, scan, Shifts=None, ShiftMode='roll',**kargs):
		assert type(channel) == int
		assert type(scan) == int
		assert channel>=0 and channel<self.Nimg
		assert scan>=0 and scan<self.Nscan
		c = self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/Image['+str(channel)+']/ImageArray.Long['+str(scan)+']')
		D = zlib.decompress(c.value)
		V = np.array(struct.unpack('<'+str(self.sx*self.sy)+'I',D),dtype=np.float).reshape((self.sy,self.sx))
		if not Shifts is None:
			r = [int(z) for z in Shifts[scan]]
			V = np.roll(np.roll(V,-r[0],axis=1),-r[1],axis=0)
			if ShiftMode=='const' or ShiftMode=='NaN':
				if ShiftMode=='NaN': kargs['const']=np.nan
				if 'const' not in kargs: raise KeyError('Missing argument const')
				if r[1]<0:
					V[:-r[1],:] = kargs['const']
				elif r[1]>0:
					V[-r[1]:,:] = kargs['const']
				if r[0]<0:
					V[:,:-r[0]] = kargs['const']
				elif r[0]>0:
					V[:,-r[0]:] = kargs['const']
		return V
