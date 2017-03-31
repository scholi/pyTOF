import ITM
import GUI
from PyQt4 import QtCore, QtGui

app = QtGui.QApplication([])
filename = QtGui.QFileDialog.getOpenFileName()
I=ITM.ITM(filename)
I.showValues()
