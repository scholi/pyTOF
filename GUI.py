from PyQt4 import QtCore, QtGui

class GUI_values(QtGui.QWidget):
	def __init__(self, data):
		QtGui.QWidget.__init__(self)
		self.treeView = QtGui.QTreeView()
		self.model = QtGui.QStandardItemModel()
		self.addItems(self.model,data)
		self.treeView.setModel(self.model)
		layout = QtGui.QVBoxLayout()
		layout.addWidget(self.treeView)
		self.setLayout(layout)

	def addItems(self, parent, elements):
		for k in elements.keys():
				item = QtGui.QStandardItem(k)
				parent.appendRow(item)
				if type(elements[k])==dict:
					self.addItems(item, elements[k])
				else:
					child = QtGui.QStandardItem(str(elements[k]))
					item.appendRow(child)

def ShowValues(data):
	app = QtGui.QApplication([])
	G = GUI_values(data)
	G.show()
	app.exec_()
