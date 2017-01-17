from pyTOF import Block
import numpy as np
import struct
import os.path
import zlib
import re
import scipy
import scipy.ndimage
import matplotlib.pyplot as plt
import pickle

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
		RAW         = zlib.decompress(self.root.goto('Meta/SI Image[0]/intensdata').value)
		self.Width  = self.root.goto('Meta/SI Image[0]/res_x').getLong()
		self.Height = self.root.goto('Meta/SI Image[0]/res_y').getLong()
		data        = struct.unpack("<{0}I".format(self.Width*self.Height),RAW)
		self.img    = np.array(data).reshape((self.Height,self.Width))
		self.fov    = self.root.goto('Meta/SI Image[0]/fieldofview').getDouble()

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

	def showStage(self, ax = None, markers=False):
		"""
		Display an image of the stage used
		ax: provide an axis to be ploted in. If None a new one will be created
		markers: If True will display on the map the Position List items.
		"""
		W = self.root.goto('SampleHolderInfo/bitmap/res_x').getLong()
		H = self.root.goto('SampleHolderInfo/bitmap/res_y').getLong()
		
		if ax is None:
			fig, ax = plt.subplots(1,1,figsize=(W*10/H,10))

		Dat = zlib.decompress(self.root.goto('SampleHolderInfo/bitmap/imagedata').value)
		I = 255*np.array(struct.unpack("<"+str(W*H*3)+"B",Dat)).reshape((H,W,3))
		ax.imshow(I);
		if markers:
			X = self.root.goto('Meta/SI Image[0]/stageposition_x').getDouble()
			Y = self.root.goto('Meta/SI Image[0]/stageposition_y').getDouble()

			def toXY(xy,W,H):
				sx=23
				sy=23
				return (913+sx*xy[0],1145+sy*xy[1])
    
			for x in self.root.goto('SampleHolderInfo/positionlist'):
				if x.name==b'shpos':
					y = pickle.loads(x.goto('pickle').value)
					pos = toXY((y['stage_x'],y['stage_y']),W,H)
					if pos[0]>=0 and pos[0]<W and pos[1]>=0 and pos[1]<H:
							ax.annotate(y['name'],xy=pos,xytext=(-15, -25), textcoords='offset points',arrowprops=dict(arrowstyle='->',facecolor='black'));
				pos = toXY((X,Y),W,H)						
				ax.plot(pos[0],pos[1],'xr');
		ax.set_xlim((0,W))
		ax.set_ylim((0,H));

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

	def show(self, ax=None):
		"""
		Shows the total SI image with the indication of the field of view.
		ax (=None): if you provide an ax argument, the image can be plottet in the axis of your choice
		"""
		if ax is None:
			fig, ax = plt.subplots(1,1,figsize=(5,5))
		ax.imshow(self.img,extent=(0,self.fov*1e6,0,self.fov*1e6))
		ax.set_title("Total SI")	
		ax.set_xlabel("x [$\mu$m]")
		ax.set_ylabel("y [$\mu$m]")

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

	def getXsectionByMass(self, x1, y1, x2, y2, masses, N=None, prog=False, ax=None, col='w-',**kargs):
		if N is None: N = int(np.sqrt((x2-x1)**2+(y2-y1)**2))+1
		x=np.linspace(x1,x2,N)
		y=np.linspace(y1,y2,N)
		out=np.zeros((self.Nscan,N))
		Y=range(self.Nscan)
		if ax is not None:
			ax.plot([x1,x2],[y1,y2],col)
		if prog:
			from tqdm import tqdm
			Y=tqdm(Y)
		for s in Y:
			Z = self.getSumImageByMass(masses,s,**kargs)
			P = scipy.ndimage.map_coordinates(Z,np.vstack((y,x)))
			out[s,:] = P
		return out

	def getSavedShift(self):
		"""
		getSavedShift returns the shifts saved with the file. Usually this is the shift correction you perform with the IonToF software.
		"""
		X = zlib.decompress(self.root.goto('filterdata/TofCorrection/ImageStack/Reduced Data/ImageStackScans/ShiftCoordinates/ImageStack.ShiftCoordinates').value)
		D = struct.unpack('<'+str(len(X)//4)+'i',X)
		dx = D[::2]
		dy = D[1::2]
		return list(zip(dx,dy))
	
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
		"""
		getImage retrieve the image of a specific channel (ID) and a specific scan.
		channel: channel ID
		scan: scan nummber (start with 0)
		Shifts: None=No shift, otherwise provide an array of tuple ((x,y) shift for each scan)
		ShiftMode:	* roll (roll the data over. easy but unphysical)
								* const (replace missing values by a constant. given by argument const)
								* NaN (the same as const with const=NaN)
		"""
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
