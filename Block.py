import binascii
import struct
import numpy as np
import binascii

class Block:
	def __init__(self, f):
		self.f = f
		self.offset = self.f.tell()
		self.Type = self.f.read(5)
		if self.Type[1:]!=b'\x19\x00\x00\x00':
			raise ValueError('Wrong block type ({Type}) found @{pos}'.format(pos=self.offset,Type=binascii.hexlify(self.Type[1:])))
		if len(self.Type)<5: raise ValueError('EOF reached. Block cannot be read')
		self.head = dict(zip(['length','z','u','x','y'],struct.unpack('<5I',f.read(20))))
		self.name = self.f.read(self.head['length'])
		self.value = self.f.read(self.head['x'])
		self.List=[]
		t = self.Type[0:1]
		if t in [b'\x01',b'\x03']:
			self.getList()
		
	def getName(self):
		return self.name
	
	def getList(self):
		length,nums,ID,L,NextBlock = struct.unpack('<III9xI8xQ',self.value[:41])
		self.nums= L
		self.subType = ID
		self.List=[]
		N = self.head['u']
		if N==0: N=self.nums
		for i in range(N):
			S=dict(zip(['index','slen','id','blen','bidx'],struct.unpack('<III4xQQ',self.value[42+33*i:42+33*i+32])))
			S['name']=self.value[S['index']:S['index']+S['slen']]
			self.List.append(S)
		if NextBlock>0:
			self.f.seek(NextBlock)
			try:
				_next = Block(self.f)
				_next.getList()
				self.List+=_next.List
			except: pass
	
	def getString(self):
		return self.value.decode('utf16')
	
	def dictList(self):
		d={}
		for i,l in enumerate(self.List):
			self.f.seek(l['bidx'])
			child = Block(self.f)
			if child.Type[0:1]==b'\x00':
				value=binascii.hexlify(child.value)
				d[child.name]={'raw':value}
				if len(child.value)==4:
					d[child.name]['long'] = child.getLong()
				elif len(child.value)==8:
					d[child.name]['float'] = child.getDouble()
				try:
					d[child.name]['utf16']=child.value.decode('utf16')
				except: pass
			del child
		return d
	
	def showList(self):
		print('List of',len(self.List),'elements. Type:',self.subType)
		for i,l in enumerate(self.List):
			self.f.seek(l['bidx'])
			try:
				child = Block(self.f)
				if child.Type[0]==b'\x00':
					if len(child.value)==4:
						vL = child.getLong()
						Dtype='long'
					elif len(child.value)==8:
						vL = child.getDouble()
						Dtype='double'
					else:
						try:
							vL=child.value.decode('utf16')
							if len(vL)>20:
								vL=vL[:20]+'...'
							Dtype='UTF-16'
						except:
							Dtype = '???'
							vL = '???'
					value=binascii.hexlify(child.value)
					if len(value)>10:
						value=value[:10]+'...'
					print(u"{name} ({id}) @{bidx}, value = {value} (hex) = {vL} ({Dtype})".format(value=value,vL=vL,Dtype=Dtype,**l))
				else:
					print("{name} ({id}) @{bidx}".format(**l))
				del child
			except: pass
			
			
	def gotoItem(self, name, idx=0):
		self.f.seek(self.getIndex(name,idx))
		return Block(self.f)
	
	def getIndex(self, name, idx=0):
		for l in self.List:
			if l['name'].decode()==name and l['id']==idx:
				return l['bidx']
		raise ValueError('Item "{name}" (index={index}) not found!'.format(name=name,index=idx))
		
	def goto(self,path):
		s = self
		for p in path.split('/'):
			idx = 0
			if '[' in p and p[-1]==']':
				i=p.index('[')
				idx=int(p[i+1:-1])
				p=p[:i]
			s=s.gotoItem(p,idx)
		return s
		
	def getDouble(self):
		return struct.unpack('<d',self.value)[0]
	
	def getULong(self):
		return struct.unpack('<I',self.value)[0]
	
	def getLong(self):
		return struct.unpack('<i',self.value)[0]
	
	def show(self,maxlevel=3,level=0, All=False):
		for l in self.List:
			if l['id']==0 or All:
				print("{tab}{name} ({id}) @{bidx}".format(tab="\t"*level,**l))
				if level<maxlevel:
					try: self.gotoItem(l['name'],l['id']).show(maxlevel,level+1,All=All)
					except: pass
	
