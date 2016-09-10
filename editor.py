# USE QPROCESS TO COMPILE THROUGH TERMIN
import sys
import subprocess
import os
import syntax
from PyQt4 import QtGui, QtCore # import the right files
from PyQt4.QtCore import Qt
from PyQt4.Qt import QFrame, QWidget, QTextEdit, QHBoxLayout, QPainter
from subprocess import Popen, PIPE

from ext import *

def generate_tokens(pipe):
    buf = []
    while True:
        b = pipe.read(1) # read one byte
        if not b: # EOF
            pipe.close()
            if buf:
                yield b''.join(buf)
            return
        elif not b.isspace(): # grow token
            buf.append(b)
        elif buf: # full token read
            yield b''.join(buf)
            buf = []

class LineTextWidget(QFrame):
 
    class NumberBar(QWidget):
 
        def __init__(self, *args):
            QWidget.__init__(self, *args)
            self.edit = None
            # This is used to update the width of the control.
            # It is the highest line that is currently visibile.
            self.highest_line = 0
 
        def setTextEdit(self, edit):
            self.edit = edit
 
        def update(self, *args):
            '''
            Updates the number bar to display the current set of numbers.
            Also, adjusts the width of the number bar if necessary.
            '''
            # The + 4 is used to compensate for the current line being bold.
            width = self.fontMetrics().width(str(self.highest_line)) + 4
            if self.width() != width:
                self.setFixedWidth(width)
            QWidget.update(self, *args)
 
        def paintEvent(self, event):
            contents_y = self.edit.verticalScrollBar().value()
            page_bottom = contents_y + self.edit.viewport().height()
            font_metrics = self.fontMetrics()
            current_block = self.edit.document().findBlock(self.edit.textCursor().position())
 
            painter = QPainter(self)
 
            line_count = 0
            # Iterate over all text blocks in the document.
            block = self.edit.document().begin()
            while block.isValid():
                line_count += 1
 
                # The top left position of the block in the document
                position = self.edit.document().documentLayout().blockBoundingRect(block).topLeft()
 
                # Check if the position of the block is out side of the visible
                # area.
                if position.y() > page_bottom:
                    break
 
                # We want the line number for the selected line to be bold.
                bold = False
                if block == current_block:
                    bold = True
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
 
                # Draw the line number right justified at the y position of the
                # line. 3 is a magic padding number. drawText(x, y, text).
                painter.drawText(self.width() - font_metrics.width(str(line_count)) - 3, round(position.y()) - contents_y + font_metrics.ascent(), str(line_count))
 
                # Remove the bold style if it was set previously.
                if bold:
                    font = painter.font()
                    font.setBold(False)
                    painter.setFont(font)
 
                block = block.next()
 
            self.highest_line = line_count
            painter.end()
 
            QWidget.paintEvent(self, event)
 
 
    def __init__(self, *args):
        QFrame.__init__(self, *args)
 
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
 
        self.edit = QTextEdit()
        self.edit.setFrameStyle(QFrame.NoFrame)
        self.edit.setAcceptRichText(False)
 
        self.number_bar = self.NumberBar()
        self.number_bar.setTextEdit(self.edit)
 
        hbox = QHBoxLayout(self)
        hbox.setSpacing(0)
        hbox.setMargin(0)
        hbox.addWidget(self.number_bar)
        hbox.addWidget(self.edit)
 
        self.edit.installEventFilter(self)
        self.edit.viewport().installEventFilter(self)
 
    def eventFilter(self, object, event):
        # Update the line numbers for all events on the text edit and the viewport.
        # This is easier than connecting all necessary singals.
        if object in (self.edit, self.edit.viewport()):
            self.number_bar.update()
            return False
        return QFrame.eventFilter(object, event)
 
    def getTextEdit(self):
        return self.edit


class Main(QtGui.QMainWindow): # Create a class called Main and let it inherit from PyQt's QMainWindow class

    def __init__(self,parent=None): # initialize the parent class and the UI setting for the application
        QtGui.QMainWindow.__init__(self,parent) # self refers to the instance of class that's being processed

        self.filename = ""

        self.initUI()

        self.changesSaved = True

    def initFileAction(self):

        self.newAction = QtGui.QAction("New File", self) # this block is repeated when we want to add new functionality. Must also write the slot function for these
        self.newAction.setShortcut("Ctrl+N")
        self.newAction.setStatusTip("Create a new document from scratch.")
        self.newAction.triggered.connect(self.new)

        self.openAction = QtGui.QAction("Open...", self)
        self.openAction.setStatusTip("Open existing document")
        self.openAction.setShortcut("Ctrl+O")
        self.openAction.triggered.connect(self.open)

        self.saveAction = QtGui.QAction("Save", self)
        self.saveAction.setStatusTip("Save document")
        self.saveAction.setShortcut("Ctrl+S")
        self.saveAction.triggered.connect(self.save)

        self.save_asAction = QtGui.QAction("Save As...", self)
        self.save_asAction.setStatusTip("Save document in different extensions")
        self.save_asAction.triggered.connect(self.save_as)

        self.printAction = QtGui.QAction("Print", self)
        self.printAction.setStatusTip("Print document")
        self.printAction.setShortcut("Ctrl+P")
        self.printAction.triggered.connect(self.printHandler)

        self.previewAction = QtGui.QAction("Print Preview...", self)
        self.previewAction.setStatusTip("Preview page before printing")
        self.previewAction.setShortcut("Ctrl+Shift+P")
        self.previewAction.triggered.connect(self.preview)

    def initEditAction(self):

        self.cutAction = QtGui.QAction("Cut", self)
        self.cutAction.setStatusTip("Delete and copy text to clipboard")
        self.cutAction.setShortcut("Ctrl+X")
        self.cutAction.triggered.connect(self.text.cut)

        self.copyAction = QtGui.QAction("Copy", self)
        self.copyAction.setStatusTip("Copy text to clipboard")
        self.copyAction.setShortcut("Ctrl+C")
        self.copyAction.triggered.connect(self.text.copy)

        self.pasteAction = QtGui.QAction("Paste", self)
        self.pasteAction.setStatusTip("Paste text from clipboard")
        self.pasteAction.setShortcut("Ctrl+V")
        self.pasteAction.triggered.connect(self.text.paste)

        self.undoAction = QtGui.QAction("Undo", self)
        self.undoAction.setStatusTip("Undo last action")
        self.undoAction.setShortcut("Ctrl+Z")
        self.undoAction.triggered.connect(self.text.undo)

        self.redoAction = QtGui.QAction("Redo", self)
        self.redoAction.setStatusTip("Redo last undone thing")
        self.redoAction.setShortcut("Ctrl+Y")
        self.redoAction.triggered.connect(self.text.redo)

    def initFindAction(self):

        self.findAction = QtGui.QAction("Replace...", self)
        self.findAction.setStatusTip("Find and replace words in your document")
        self.findAction.setShortcut("Ctrl+F")
        self.findAction.triggered.connect(find.Find(self).show)

    def initInsertAction(self):

        self.dateTimeAction = QtGui.QAction("Insert Date", self)
        self.dateTimeAction.setStatusTip("Insert current date/time")
        self.dateTimeAction.setShortcut("Ctrl+D")
        self.dateTimeAction.triggered.connect(datetime.DateTime(self).show)

        self.tableAction = QtGui.QAction("Insert Table", self)
        self.tableAction.setStatusTip("Insert table")
        self.tableAction.setShortcut("Ctrl+T")
        self.tableAction.triggered.connect(table.Table(self).show)

        self.imageAction = QtGui.QAction("Insert Image", self)
        self.imageAction.setStatusTip("Insert Image")
        self.imageAction.setShortcut("Ctrl+Shift+I")
        self.imageAction.triggered.connect(self.insertImage)

        self.bulletAction = QtGui.QAction(QtGui.QIcon("icons/bullet.png"), "Insert bullet list", self)
        self.bulletAction.setStatusTip("Insert Bullet List")
        self.bulletAction.setShortcut("Ctrl+Shift+B")
        self.bulletAction.triggered.connect(self.bulletList)

        self.numberedAction = QtGui.QAction(QtGui.QIcon("icons/number.png"), "Insert Numbered List", self)
        self.numberedAction.setStatusTip("Insert Numbered List")
        self.numberedAction.setShortcut("Ctrl+Shift+L")
        self.numberedAction.triggered.connect(self.numberList)


    def initFormatAction(self):

        self.fontColor = QtGui.QAction("Change Font Color", self)
        self.fontColor.setStatusTip("Change Font Color")
        self.fontColor.triggered.connect(self.fontColorChanged)

        self.boldAction = QtGui.QAction(QtGui.QIcon("icons/bold.png"), "Bold", self)
        self.boldAction.setStatusTip("Bold Selected Text")
        self.boldAction.triggered.connect(self.bold)

        self.italicAction = QtGui.QAction(QtGui.QIcon("icons/italic.png"), "Italic", self)
        self.italicAction.setStatusTip("Italize Selected Text")
        self.italicAction.triggered.connect(self.italic)

        self.underlAction = QtGui.QAction(QtGui.QIcon("icons/underline.png"), "Underline", self)
        self.underlAction.setStatusTip("Underline Selected Text")
        self.underlAction.triggered.connect(self.underline)

        self.strikeAction = QtGui.QAction(QtGui.QIcon("icons/strike.png"), "Strike Through", self)
        self.strikeAction.setStatusTip("Strike Through Selected Text")
        self.strikeAction.triggered.connect(self.strike)

        self.superAction = QtGui.QAction(QtGui.QIcon("icons/superscript.png"), "Superscript", self)
        self.superAction.setStatusTip("Superscript Selected Text")
        self.superAction.triggered.connect(self.superScript)

        self.subAction = QtGui.QAction(QtGui.QIcon("icons/subscript.png"), "Subscript", self)
        self.subAction.setStatusTip("Subscript Selected Text")
        self.subAction.triggered.connect(self.subScript)

        self.alignLeftAction = QtGui.QAction(QtGui.QIcon("icons/align-left.png"), "Align Left", self)
        self.alignLeftAction.setStatusTip("Align Selected Text To The Left")
        self.alignLeftAction.triggered.connect(self.alignLeft)

        self.alignCenterAction = QtGui.QAction(QtGui.QIcon("icons/align-center.png"), "Align Center", self)
        self.alignCenterAction.setStatusTip("Align Selected Text To The Center")
        self.alignCenterAction.triggered.connect(self.alignCenter)

        self.alignRightAction = QtGui.QAction(QtGui.QIcon("icons/align-right.png"), "Align Right", self)
        self.alignRightAction.setStatusTip("Align Selected Text To The Right")
        self.alignRightAction.triggered.connect(self.alignRight)

        self.alignJustifyAction = QtGui.QAction(QtGui.QIcon("icons/align-justify.png"), "Align Justify", self)
        self.alignJustifyAction.setStatusTip("Align Justify The Selected Text")
        self.alignJustifyAction.triggered.connect(self.alignJustify)

        self.indentAction = QtGui.QAction(QtGui.QIcon("icons/indent.png"), "Indent", self)
        self.indentAction.setStatusTip("Indent Selected Text")
        self.indentAction.setShortcut("Ctrl+Tab")
        self.indentAction.triggered.connect(self.indent)

        self.dedentAction = QtGui.QAction(QtGui.QIcon("icons/dedent.png"), "Dedent", self)
        self.dedentAction.setStatusTip("Dedent Selected Text")
        self.dedentAction.setShortcut("Shift+Tab")
        self.dedentAction.triggered.connect(self.dedent)

        self.backColor = QtGui.QAction("Background Color", self)
        self.backColor.setStatusTip("Change The Background Color")
        self.backColor.triggered.connect(self.highlight)

    def initReviewAction(self):

        self.wordCountAction = QtGui.QAction("Word Count", self)
        self.wordCountAction.setStatusTip("See word/symbol count")
        self.wordCountAction.setShortcut("Ctrl+W")
        self.wordCountAction.triggered.connect(self.wordCount)
    
    def initWordbar(self):

        fontBox = QtGui.QFontComboBox(self) # A convenient combo box that automatically includes all the fonts available to the system 
        fontBox.currentFontChanged.connect(lambda font: self.text.setCurrentFont(font)) # connect currenFontChanged signal to a slot function called self.fontFamily()

        fontSize = QtGui.QSpinBox(self)

        # Will display " pt" after each value
        fontSize.setSuffix(" pt")

        fontSize.valueChanged.connect(lambda size: self.text.setFontPointSize(size))

        fontSize.setValue(11)

        self.wordBar = self.addToolBar("Word")

        self.wordBar.addWidget(fontBox)
        self.wordBar.addWidget(fontSize)

        self.wordBar.addAction(self.boldAction)
        self.wordBar.addAction(self.italicAction)
        self.wordBar.addAction(self.underlAction)
        self.wordBar.addAction(self.strikeAction)
        self.wordBar.addAction(self.superAction)
        self.wordBar.addAction(self.subAction)

        self.wordBar.addSeparator()

        self.wordBar.addAction(self.bulletAction)
        self.wordBar.addAction(self.numberedAction)
        self.wordBar.addAction(self.indentAction)
        self.wordBar.addAction(self.dedentAction)
        self.wordBar.addAction(self.alignLeftAction)
        self.wordBar.addAction(self.alignCenterAction)
        self.wordBar.addAction(self.alignRightAction)
        self.wordBar.addAction(self.alignJustifyAction)

    def initMenubar(self):

        menubar = self.menuBar()

        file = menubar.addMenu("File")
        edit = menubar.addMenu("Edit")
        find = menubar.addMenu("Find")
        insert = menubar.addMenu("Insert")
        format = menubar.addMenu("Format")
        view = menubar.addMenu("View")
        review = menubar.addMenu("Review")
        project = menubar.addMenu("Project")

        # Add the most important actions to the menubar

        file.addAction(self.newAction)
        file.addAction(self.openAction)
        file.addAction(self.saveAction)
        file.addAction(self.save_asAction)
        file.addAction(self.printAction)
        file.addAction(self.previewAction)

        edit.addAction(self.undoAction)
        edit.addAction(self.redoAction)
        edit.addAction(self.cutAction)
        edit.addAction(self.copyAction)
        edit.addAction(self.pasteAction)

        find.addAction(self.findAction)
        
        insert.addAction(self.dateTimeAction)
        insert.addAction(self.tableAction)
        insert.addAction(self.imageAction)
        insert.addAction(self.bulletAction)
        insert.addAction(self.numberedAction)

        format.addAction(self.fontColor)
        format.addAction(self.boldAction)
        format.addAction(self.italicAction)
        format.addAction(self.underlAction)
        format.addAction(self.strikeAction)
        format.addAction(self.superAction)
        format.addAction(self.alignLeftAction)
        format.addAction(self.alignCenterAction)
        format.addAction(self.alignRightAction)
        format.addAction(self.alignJustifyAction)
        format.addAction(self.indentAction)
        format.addAction(self.dedentAction)
        format.addAction(self.backColor)

        review.addAction(self.wordCountAction)

        # Toggling actions for the various bars
        toggleWordBarAction = QtGui.QAction("Toggle Word Bar", self)
        toggleWordBarAction.triggered.connect(self.toggleWordBar)

        view.addAction(toggleWordBarAction)

        buildAction = QtGui.QAction("Compile current file",self)
        buildAction.setShortcut("Ctrl+B")
        buildAction.triggered.connect(self.run)

        project.addAction(buildAction)
 

    def initUI(self):

        self.text = QtGui.QTextEdit(self)

        # Set the tab stop width to around 33 pixels which is
        # more or less 8 spaces
        self.text.setTabStopWidth(33)

        self.initFileAction()
        self.initEditAction()
        self.initFindAction()
        self.initInsertAction()
        self.initFormatAction()
        self.initReviewAction()

        self.initWordbar()
        self.initMenubar()

        self.highlight = syntax.PythonHighlighter(self.text.document()) #causing the document to be marked as modified
        self.setCentralWidget(self.text)

        # self.inputField = QtGui.QDockWidget(self)
        # self.inputText = QtGui.QTextEdit()
        # self.inputField.setWidget(self.inputText)
        # self.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.inputField)
        # self.inputField.setWindowTitle("Inputs for command line")

        # Initialize a statusbar for the window
        self.statusbar = self.statusBar()

        # If the cursor position changes, call the function that displays
        # the line and column number
        self.text.cursorPositionChanged.connect(self.cursorPosition)

        # We need our own context menu for tables
        self.text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text.customContextMenuRequested.connect(self.context)

        self.text.textChanged.connect(self.changed)

        self.setGeometry(100,100,1030,800)
        self.setWindowTitle("Writer")
        self.setWindowIcon(QtGui.QIcon("icons/icon.png"))
        
        color = QtGui.QColor('#66cc80')
        style = "QWidget { border: 1px solid %s; }" % color.name()
        self.wordBar.setStyleSheet(style)

       #  self.setStyleSheet("""

       #     QMenuBar {
       #         background-color: rgb(49,49,49);
       #         color: rgb(255,255,255);
       #         border: 1px solid #000;
       #     }
 
       #     QMenuBar::item {
       #         background-color: rgb(49,49,49);
       #         color: rgb(255,255,255);
       #     }
 
       #     QMenuBar::item::selected {
       #         background-color: rgb(30,30,30);
       #     }
 
       #     QMenu {
       #         background-color: rgb(49,49,49);
       #         color: rgb(255,255,255);
       #         border: 1px solid #000;          
       #     }
 
       #     QMenu::item::selected {
       #         background-color: rgb(30,30,30);
       #     }
       # """)

    def changed(self):
        self.changesSaved = False

    def closeEvent(self,event):

        if self.changesSaved:

            event.accept()

        else:
        
            popup = QtGui.QMessageBox(self)

            popup.setIcon(QtGui.QMessageBox.Warning)
            
            popup.setText("The document has been modified")
            
            popup.setInformativeText("Do you want to save your changes?")
            
            popup.setStandardButtons(QtGui.QMessageBox.Save   |
                                      QtGui.QMessageBox.Cancel |
                                      QtGui.QMessageBox.Discard)
            
            popup.setDefaultButton(QtGui.QMessageBox.Save)

            answer = popup.exec_()

            if answer == QtGui.QMessageBox.Save:
                self.save()

            elif answer == QtGui.QMessageBox.Discard:
                event.accept()

            else:
                event.ignore()

    def context(self,pos):

        # Grab the cursor
        cursor = self.text.textCursor()

        # Grab the current table, if there is one
        table = cursor.currentTable()

        # Above will return 0 if there is no current table, in which case
        # we call the normal context menu. If there is a table, we create
        # our own context menu specific to table interaction
        if table:

            menu = QtGui.QMenu(self)

            appendRowAction = QtGui.QAction("Append row",self)
            appendRowAction.triggered.connect(lambda: table.appendRows(1))

            appendColAction = QtGui.QAction("Append column",self)
            appendColAction.triggered.connect(lambda: table.appendColumns(1))


            removeRowAction = QtGui.QAction("Remove row",self)
            removeRowAction.triggered.connect(self.removeRow)

            removeColAction = QtGui.QAction("Remove column",self)
            removeColAction.triggered.connect(self.removeCol)


            insertRowAction = QtGui.QAction("Insert row",self)
            insertRowAction.triggered.connect(self.insertRow)

            insertColAction = QtGui.QAction("Insert column",self)
            insertColAction.triggered.connect(self.insertCol)


            mergeAction = QtGui.QAction("Merge cells",self)
            mergeAction.triggered.connect(lambda: table.mergeCells(cursor))

            # Only allow merging if there is a selection
            if not cursor.hasSelection():
                mergeAction.setEnabled(False)


            splitAction = QtGui.QAction("Split cells",self)

            cell = table.cellAt(cursor)

            # Only allow splitting if the current cell is larger
            # than a normal cell
            if cell.rowSpan() > 1 or cell.columnSpan() > 1:

                splitAction.triggered.connect(lambda: table.splitCell(cell.row(),cell.column(),1,1))

            else:
                splitAction.setEnabled(False)


            menu.addAction(appendRowAction)
            menu.addAction(appendColAction)

            menu.addSeparator()

            menu.addAction(removeRowAction)
            menu.addAction(removeColAction)

            menu.addSeparator()

            menu.addAction(insertRowAction)
            menu.addAction(insertColAction)

            menu.addSeparator()

            menu.addAction(mergeAction)
            menu.addAction(splitAction)

            # Convert the widget coordinates into global coordinates
            pos = self.mapToGlobal(pos)

            # Add pixels for the tool and formatbars, which are not included
            # in mapToGlobal(), but only if the two are currently visible and
            # not toggled by the user

            if self.toolbar.isVisible():
                pos.setY(pos.y() + 45)

            if self.formatbar.isVisible():
                pos.setY(pos.y() + 45)
                
            # Move the menu to the new position
            menu.move(pos)

            menu.show()

        else:

            event = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse,QtCore.QPoint())

            self.text.contextMenuEvent(event)


        # add function that returns the terminal output
    def run(self): # make it compile code 
        #ls_output = subprocess.check_output(['ls'])
        #popup = QtGui.QMessageBox(self)

        #popup.setText(ls_output)
        #popup.show()
        terminalOutput = "Standard Output:\n"
        fileExtension = self.filename.split(".")[-1]
        if (fileExtension == "py"):
            terminalstdout = subprocess.Popen( ['python2', self.filename], stdout=subprocess.PIPE ).communicate()[0]
            terminalstderr = subprocess.Popen( ['python2', self.filename], stderr=subprocess.PIPE ).communicate()[1]
            terminalOutput += terminalstdout
            terminalOutput += "Standard Error:\n"
            terminalOutput += terminalstderr
            #p = Popen(['python2', self.filename], stdout=PIPE, bufsize=0)
            #for token in generate_tokens(p.stdout):
                #terminalOutput += token
        elif(fileExtension == "cpp" or fileExtension == "c"):
            terminalstdout = subprocess.Popen( ['g++', self.filename,], stdout=subprocess.PIPE ).communicate()[0]
            terminalstderr = subprocess.Popen( ['g++', self.filename,], stderr=subprocess.PIPE ).communicate()[1]
            if terminalstderr == "":
                terminalOutput += subprocess.Popen( ['./a.out'], stdout=subprocess.PIPE ).communicate()[0]
                terminalOutput += "Standard Error:\n"
                terminalOutput += subprocess.Popen( ['./a.out'], stderr=subprocess.PIPE ).communicate()[1]
            else:
                terminalOutput += terminalstdout
                #terminalOutput += subprocess.Popen( ['./a.out'], stdout=subprocess.PIPE ).communicate()[0]
                terminalOutput += "Standard Error:\n"
                terminalOutput += terminalstderr
                #terminalOutput += subprocess.Popen( ['./.aout'], stderr=subprocess.PIPE ).communicate()[1]
        terminalOutput = terminalOutput.decode('utf-8')
        popup = QtGui.QMessageBox(self)
        popup.setText(terminalOutput)
        popup.show()


    def removeRow(self):

        # Grab the cursor
        cursor = self.text.textCursor()

        # Grab the current table (we assume there is one, since
        # this is checked before calling)
        table = cursor.currentTable()

        # Get the current cell
        cell = table.cellAt(cursor)

        # Delete the cell's row
        table.removeRows(cell.row(),1)

    def removeCol(self):

        # Grab the cursor
        cursor = self.text.textCursor()

        # Grab the current table (we assume there is one, since
        # this is checked before calling)
        table = cursor.currentTable()

        # Get the current cell
        cell = table.cellAt(cursor)

        # Delete the cell's column
        table.removeColumns(cell.column(),1)

    def insertRow(self):

        # Grab the cursor
        cursor = self.text.textCursor()

        # Grab the current table (we assume there is one, since
        # this is checked before calling)
        table = cursor.currentTable()

        # Get the current cell
        cell = table.cellAt(cursor)

        # Insert a new row at the cell's position
        table.insertRows(cell.row(),1)

    def insertCol(self):

        # Grab the cursor
        cursor = self.text.textCursor()

        # Grab the current table (we assume there is one, since
        # this is checked before calling)
        table = cursor.currentTable()

        # Get the current cell
        cell = table.cellAt(cursor)

        # Insert a new row at the cell's position
        table.insertColumns(cell.column(),1)


    def toggleWordBar(self):

        state = self.wordBar.isVisible()

        # Set the visibility to its inverse
        self.wordBar.setVisible(not state)

    def new(self):

        spawn = Main()

        spawn.show()

    def open(self): # fix open to look for files with different extension

        # Get filename and show files that fits the filter
        self.filename = QtGui.QFileDialog.getOpenFileName(self, 'Open File',".","Writer files(*.writer);;Text files(*.txt);;C source file(*.c);; C++ source file(*.h *.hpp *.hxx *.cpp *.cxx *.cc);;Python source file(*.py)")
        
        if self.filename:
            with open(self.filename,"rt") as file:
                self.text.setText(file.read())

            self.changesSaved = True
    
    # define a new function called save as which allows the user to save in any extension
    def save_as(self):
        if not self.filename:
          self.filename = QtGui.QFileDialog.getSaveFileName(self, 'Save As...')

        if self.filename:

            with open(self.filename,"wt") as file:
                file.write(self.text.toPlainText())

            self.changesSaved = True

    def save(self): # change save as to allow for different extensions

        # Only open dialog if there is no filename yet
        if not self.filename:
          self.filename = QtGui.QFileDialog.getSaveFileName(self, 'Save File')
        

        if self.filename:
            
            fullPath = self.filename
            fileExtension = fullPath.split(".")[-1]
            if not fileExtension:
                self.filename += ".writer"

            # We just store the contents of the text file along with the
            # format in html, which Qt does in a very nice way for us
            with open(self.filename,"wt") as file:
                file.write(self.text.toPlainText())

            self.changesSaved = True

    def preview(self):

        # Open preview dialog
        preview = QtGui.QPrintPreviewDialog()

        # If a print is requested, open print dialog
        preview.paintRequested.connect(lambda p: self.text.print_(p))

        preview.exec_()

    def printHandler(self):

        # Open printing dialog
        dialog = QtGui.QPrintDialog()

        if dialog.exec_() == QtGui.QDialog.Accepted:
            self.text.document().print_(dialog.printer())

    def cursorPosition(self):

        cursor = self.text.textCursor()

        # Mortals like 1-indexed things
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber()

        self.statusbar.showMessage("Line: {} | Column: {}".format(line,col))

    def wordCount(self):

        wc = wordcount.WordCount(self)

        wc.getText()

        wc.show()

    def insertImage(self):

        # Get image file name
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Insert image',".","Images (*.png *.xpm *.jpg *.bmp *.gif)")

        if filename:
            
            # Create image object
            image = QtGui.QImage(filename)

            # Error if unloadable
            if image.isNull():

                popup = QtGui.QMessageBox(QtGui.QMessageBox.Critical,
                                          "Image load error",
                                          "Could not load image file!",
                                          QtGui.QMessageBox.Ok,
                                          self)
                popup.show()

            else:

                cursor = self.text.textCursor()

                cursor.insertImage(image,filename)

    def fontColorChanged(self):

        # Get a color from the text dialog
        color = QtGui.QColorDialog.getColor()

        # Set it as the new text color
        self.text.setTextColor(color)

    def highlight(self):

        color = QtGui.QColorDialog.getColor()

        self.text.setTextBackgroundColor(color)

    def bold(self):

        if self.text.fontWeight() == QtGui.QFont.Bold:

            self.text.setFontWeight(QtGui.QFont.Normal)

        else:

            self.text.setFontWeight(QtGui.QFont.Bold)

    def italic(self):

        state = self.text.fontItalic()

        self.text.setFontItalic(not state)

    def underline(self):

        state = self.text.fontUnderline()

        self.text.setFontUnderline(not state)

    def strike(self):

        # Grab the text's format
        fmt = self.text.currentCharFormat()

        # Set the fontStrikeOut property to its opposite
        fmt.setFontStrikeOut(not fmt.fontStrikeOut())

        # And set the next char format
        self.text.setCurrentCharFormat(fmt)

    def superScript(self):

        # Grab the current format
        fmt = self.text.currentCharFormat()

        # And get the vertical alignment property
        align = fmt.verticalAlignment()

        # Toggle the state
        if align == QtGui.QTextCharFormat.AlignNormal:

            fmt.setVerticalAlignment(QtGui.QTextCharFormat.AlignSuperScript)

        else:

            fmt.setVerticalAlignment(QtGui.QTextCharFormat.AlignNormal)

        # Set the new format
        self.text.setCurrentCharFormat(fmt)

    def subScript(self):

        # Grab the current format
        fmt = self.text.currentCharFormat()

        # And get the vertical alignment property
        align = fmt.verticalAlignment()

        # Toggle the state
        if align == QtGui.QTextCharFormat.AlignNormal:

            fmt.setVerticalAlignment(QtGui.QTextCharFormat.AlignSubScript)

        else:

            fmt.setVerticalAlignment(QtGui.QTextCharFormat.AlignNormal)

        # Set the new format
        self.text.setCurrentCharFormat(fmt)

    def alignLeft(self):
        self.text.setAlignment(Qt.AlignLeft)

    def alignRight(self):
        self.text.setAlignment(Qt.AlignRight)

    def alignCenter(self):
        self.text.setAlignment(Qt.AlignCenter)

    def alignJustify(self):
        self.text.setAlignment(Qt.AlignJustify)

    def indent(self):

        # Grab the cursor
        cursor = self.text.textCursor()

        if cursor.hasSelection():

            # Store the current line/block number
            temp = cursor.blockNumber()

            # Move to the selection's end
            cursor.setPosition(cursor.anchor())

            # Calculate range of selection
            diff = cursor.blockNumber() - temp

            direction = QtGui.QTextCursor.Up if diff > 0 else QtGui.QTextCursor.Down

            # Iterate over lines (diff absolute value)
            for n in range(abs(diff) + 1):

                # Move to start of each line
                cursor.movePosition(QtGui.QTextCursor.StartOfLine)

                # Insert tabbing
                cursor.insertText("\t")

                # And move back up
                cursor.movePosition(direction)

        # If there is no selection, just insert a tab
        else:

            cursor.insertText("\t")

    def handleDedent(self,cursor):

        cursor.movePosition(QtGui.QTextCursor.StartOfLine)

        # Grab the current line
        line = cursor.block().text()

        # If the line starts with a tab character, delete it
        if line.startsWith("\t"):

            # Delete next character
            cursor.deleteChar()

        # Otherwise, delete all spaces until a non-space character is met
        else:
            for char in line[:8]:

                if char != " ":
                    break

                cursor.deleteChar()

    def dedent(self):

        cursor = self.text.textCursor()

        if cursor.hasSelection():

            # Store the current line/block number
            temp = cursor.blockNumber()

            # Move to the selection's last line
            cursor.setPosition(cursor.anchor())

            # Calculate range of selection
            diff = cursor.blockNumber() - temp

            direction = QtGui.QTextCursor.Up if diff > 0 else QtGui.QTextCursor.Down

            # Iterate over lines
            for n in range(abs(diff) + 1):

                self.handleDedent(cursor)

                # Move up
                cursor.movePosition(direction)

        else:
            self.handleDedent(cursor)


    def bulletList(self):

        cursor = self.text.textCursor()

        # Insert bulleted list
        cursor.insertList(QtGui.QTextListFormat.ListDisc)

    def numberList(self):

        cursor = self.text.textCursor()

        # Insert list with numbers
        cursor.insertList(QtGui.QTextListFormat.ListDecimal)

def main():
    app = QtGui.QApplication(sys.argv)

    main = Main()
    main.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()





# Can probably access the text in the new widget with self.textField

# lambda functions
# f = lambda x: x**2 + 2*x - 5

# Those things are actually quite useful. Python supports a style of programming called functional programming where you can pass functions to other functions to do stuff. Example:

# mult3 = filter(lambda x: x % 3 == 0, [1, 2, 3, 4, 5, 6, 7, 8, 9])

# sets mult3 to [3, 6, 9], those elements of the original list that are multiples of 3. This is shorter (and, one could argue, clearer) than

# def filterfunc(x):
    # return x % 3 == 0
# mult3 = filter(filterfunc, [1, 2, 3, 4, 5, 6, 7, 8, 9])


# FF9C30
# 008AFF
# D96EA8
# F0B2AD
# 3DAD3D
# 5CB8FF

