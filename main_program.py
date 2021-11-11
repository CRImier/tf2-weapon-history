import json, os, string
import breeze_resources
from math import ceil
from datetime import datetime, timedelta
import sys
from PIL import Image
import io

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.uic import loadUi
from PyQt5.QtCore import QFile, QTextStream, Qt, QUrl, QByteArray
from PyQt5.QtGui import QFont, QPixmap, QPainter, QPainterPath, QPen, QColor, QBrush, QFontDatabase, QImage
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QGridLayout, QVBoxLayout, QStyle, QStyleOption, QSizePolicy
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

BASE_DATE = datetime(2007, 10, 10)

class Ticks(QtWidgets.QSlider):
	def __init__(self, values, size, parent = None):
		super(Ticks, self).__init__(parent)

		self.values = values
		self.offset = abs(self.style().pixelMetric(
			QStyle.PM_SliderSpaceAvailable,
			QStyleOption(1, QStyleOption.SO_Slider),
			self))

		self.setOrientation(QtCore.Qt.Horizontal)
		self.setGeometry(size)
		self.setStyleSheet("QSlider::sub-page:horizontal {background-color: darkgray; border: 1px; height: 40px; width: 40px; margin: 0 0;} QSlider{background-color:transparent}")

	def paintEvent(self, event):
		QtWidgets.QSlider.paintEvent(self, event)

		painter = QPainter(self)
		for point in self.values:
			position = int(self.offset / 1.9 + QStyle.sliderPositionFromValue(
				self.minimum(), self.maximum(),
				point, self.width() - self.offset))

			#painter.drawLine(position, 0, position, self.height())
			p = QPainter()
			p.begin(self)

			
			if self.values.index(point) % 2 == 0:
				brush = QBrush(QColor(191, 57, 28))
				pen = QPen(brush, 4, Qt.SolidLine, Qt.RoundCap)
				p.setPen(pen)
				p.drawLine(position, 18, position, self.height()/1.25)
			else:
				brush = QBrush(QColor(90, 140, 173))
				pen = QPen(brush, 4, Qt.SolidLine, Qt.RoundCap)
				p.setPen(pen)
				p.drawLine(position, 5, position, self.height()/2.3)
			p.end()


class Window(QMainWindow):
	all_weapons = {}

	def __init__(self):
		super().__init__()
		
		loadUi("main.ui", self)

		self.tiny_images = {}

		self.valid_chars = string.ascii_lowercase + string.ascii_uppercase

		self.fontDB = QtGui.QFontDatabase()
		self.fontDB.addApplicationFont(":/fonts/tf2build.ttf")
		self.fontDB.addApplicationFont(":/fonts/TF2secondary.ttf")

		self.sounds = json.load( open("sounds/weapon_sounds.json") )

		self.setFixedSize(1056, 692)

		self.setWindowTitle("TF2 Item History")
		self.setWindowIcon(QtGui.QIcon('logo.png'))

		self.load_all_weapons()

		self.file = json.load(open("updates.json", encoding="utf-8"))
		dates = [datetime.strptime(i, "%Y-%m-%d") for i in list(self.file["updates"].keys())]
		date_list_days = [(i-dates[0]).days for i in dates][1:]

		self.DateSelector = Ticks(date_list_days, QtCore.QRect(20, 50, 1021, 31), parent = self)
		max_days = datetime.now() - BASE_DATE
		self.DateSelector.setMaximum(max_days.days)

		print(self.DateSelector.value())

		self.DateSelector.valueChanged.connect(self.add_valid_weapons)
		self.DateSelector.valueChanged.connect(self.update_update)

		self.scroll_widget.setLayout(QGridLayout())

		self.scroll_widget.layout().setColumnMinimumWidth(8, 0)
		self.scroll_widget.layout().setColumnStretch(8, 1)
		self.scroll_widget.layout().setRowMinimumHeight(8, 0)
		self.scroll_widget.layout().setRowStretch(8, 1)

		self.player = QMediaPlayer()
		self.player.setVolume(5)

		self.first = datetime.strptime(list(self.file["updates"].keys())[0], "%Y-%m-%d")
		self.last = datetime.strptime(list(self.file["updates"].keys())[-1], "%Y-%m-%d")

		self.next.setFont(QFont("TF2 Build", 16))
		self.next.clicked.connect(self.next_update)
		self.previous.setFont(QFont("TF2 Build", 16))
		self.previous.clicked.connect(self.prev_update)

		self.update_n.setText("Release")
		self.update_n.setFont(QFont("TF2 Build", 16))
		self.update_d.setText("Oct 10, 2007")
		self.update_d.setFont(QFont("TF2 Build", 16))

		self.sort_order = "Release"

		self.Alphabetical.setFont(QFont("TF2 Secondary", 14))

		self.Alphabetical.clicked.connect(self.sort_Aa)
		self.ReleaseOrder.clicked.connect(self.sort_Release)

		self.search.setFont(QFont("TF2 Secondary", 16))
		self.search.lower()
		self.search.textChanged.connect(self.add_valid_weapons)

		self.clear_text.clicked.connect(self.clearText)

		self.setStyleSheet("""QToolTip {
								font-family: "TF2 Secondary";
								font-size: 16px;
								color: #EBE2CA;
								border-radius: 10px;
								border-color: rgb(120, 106, 93);
								background-color: rgb(120, 106, 93);
								font-weight: bold;
								opacity: 255;
								}""")

	def clearText(self):
		self.search.setText("")

	def sort_Aa(self):
		self.sort_order = "Alphabetical"
		self.add_valid_weapons()

	def sort_Release(self):
		self.sort_order = "Release"
		self.add_valid_weapons()

	def update_update(self):
		nearest = self.get_nearest_date()
		self.update_d.setText(nearest.strftime("%b %d, %Y"))
		self.update_n.setText(self.file["updates"][nearest.strftime("%Y-%m-%d")])

	def get_nearest_date(self):
		current_date = self.first + timedelta(days = self.DateSelector.value())
		dates = [datetime.strptime(i, "%Y-%m-%d") for i in list(self.file["updates"].keys())]
		display = min([(current_date-date, date) for date in dates if (current_date-date).days>=0], key=lambda x: x[0])[1]
		#get the closest update date behind us

		return(display)

	def next_update(self):
		current_date = self.first + timedelta(days = self.DateSelector.value())
		print(current_date, self.DateSelector.value())
		dates = [datetime.strptime(i, "%Y-%m-%d") for i in list(self.file["updates"].keys())]
		try: #get a list of the distance between now and the date for every update
			display = max([(current_date-date, date) for date in dates if (current_date-date).days<0], key=lambda x: x[0])[1]
		except ValueError: #find the largest negative value, which is the closest update in front of us
			return()
		nearest = display - self.first

		self.DateSelector.setValue( nearest.days )

	def prev_update(self):
		current_date = self.first + timedelta(days = self.DateSelector.value())
		dates = [datetime.strptime(i, "%Y-%m-%d") for i in list(self.file["updates"].keys())]
		try: #get a list of the distance between now and the date for every update
			display = min([(current_date-date, date) for date in dates if (current_date-date).days>0], key=lambda x: x[0])[1]
		except ValueError: #find the smallest positive value, which is the closest update behind us
			return()
		nearest = display - self.first #and snap directly to it

		self.DateSelector.setValue( nearest.days )

	def display_item_window(self, item):
		try: #play sound that matches to the schema
			self.play_sound( self.sounds[item]+"_pickup.wav" )
		except: #otherwise play generic sound
			self.play_sound("item_default_pickup.wav")
		self.sub_window = SubWindow(item, self.all_weapons[item])
		self.sub_window.show()
		
	def add_box(self, x, y, item, name):

		name = name.replace(' ', '_')
		name = ''.join(c for c in name if c in self.valid_chars)

		label = QLabel(name)

		if item not in self.tiny_images.keys():
			im = Image.open(f"weapon_images/{item}.png")
			with io.BytesIO() as f: #resize image to 94, 94 
				im = im.resize((94, 94))
				im.save(f, format='png')
				f.seek(0)
				image_data = f.read()
				qimg = QImage.fromData(image_data)
				patch_qt = QPixmap.fromImage(qimg)
				self.tiny_images[item] = patch_qt

		else:
			patch_qt = self.tiny_images[item]
		
		hover_stylesheet = "QLabel#" + name + "::hover{background-color:#B29600;}"
		label.setStyleSheet("QLabel#" + name + "{border-radius:10px; border-color: #FFD700; border-width:3px; border-style: solid; background-color: rgb(34, 30, 27);}" + hover_stylesheet)
		label.setText("")
		#label.setPixmap(QtGui.QPixmap(f"weapon_images/{item}.png"))
		label.setPixmap(patch_qt)
		label.setFixedSize(121, 94)
		#label.setScaledContents(True)
		label.setObjectName(name)
		label.setAlignment(Qt.AlignCenter)

		label.enterEvent = lambda event: self.play_sound("item_info_mouseover.wav")
		label.mousePressEvent = lambda event: self.display_item_window(item)
		label.setCursor(Qt.PointingHandCursor)

		self.scroll_widget.layout().addWidget(label, x, y, Qt.AlignLeft | Qt.AlignTop)

	def sort_release(self, weapon_list):
		to_sort = {}
		weapons = {name:data for name, data in self.all_weapons.items() if name in weapon_list}
		for weapon_name, weapon_data in weapons.items():
			to_sort[weapon_name] = (datetime.strptime(weapon_data["added"], "%Y-%m-%d") - BASE_DATE).days #with a value of how many days its been
																											#between introduction and launch
		to_sort = sorted(to_sort.items(), key = lambda x: x[1])
		sorted_weapons = [i[0] for i in to_sort] #sort based on the number of days, and then keep the weapon name
		return(sorted_weapons)

	def add_valid_weapons(self):
		index = self.scroll_widget.layout().count()
		for i in reversed(range(index)): 
			self.scroll_widget.layout().itemAt(i).widget().setParent(None) #Remove all prior widgets

		valid_weapons = self.get_valid_weapons()
		print(self.DateSelector.value())

		minimum = ceil(len(valid_weapons)/8) #theres 8 columns per row
		positions = [(x, y) for x in range(minimum) for y in range(8)][:len(valid_weapons)] #Make sure there are enough grid coordinates to assign the weapons

		print(positions)
		print(valid_weapons)
		#print("self.search.text()", repr(self.search.text()))

		if self.search.text() != '':
			matched_weapons = [weapon for weapon in valid_weapons if self.search.text().lower() in weapon.lower()]
			print(matched_weapons) #if the search bar is empty, check to see if our substring matches any of the valid weapons

			if self.sort_order == "Release":
				print("a")
				matched_weapons = self.sort_release(matched_weapons)

			for position, weapon in zip(positions, matched_weapons):
				self.add_box(*position, weapon, weapon)

		elif self.sort_order == "Alphabetical": #alphabetical is the default sort from os.listdir()
			for position, weapon in zip(positions, valid_weapons):
				self.add_box(*position, weapon, weapon)

		elif self.sort_order == "Release":
			sorted_weapons = self.sort_release(valid_weapons)

			for position, weapon in zip(positions, sorted_weapons):
				self.add_box(*position, weapon, weapon)

	def get_valid_weapons(self):
		valid_weapons = []
		for weapon_name, weapon_data in self.all_weapons.items():
			date_added = datetime.strptime(weapon_data["added"], "%Y-%m-%d")
			if (date_added - BASE_DATE).days <= self.DateSelector.value():
				valid_weapons.append(weapon_name)

		return(valid_weapons) #return all weapons which have an addition date greater than or equals to the current date

	def load_all_weapons(self):
		for weapon_filename in os.listdir("weapon_data"):
			weapon_data = json.load(open(f"weapon_data/{weapon_filename}"))
			weapon_name = weapon_data["weapon"]
			self.all_weapons[weapon_name] = weapon_data
			# post-load processing goes here - maybe a call to a separate function

	def play_sound(self, sound):
		file_path = QUrl.fromLocalFile(f"sounds/{sound}")
		file = QMediaContent(file_path)
		self.player.setMedia(file)
		self.player.play()


class SubWindow(QMainWindow):
	def __init__(self, weapon, weapon_data):
		super(SubWindow, self).__init__()

		self.weapon = weapon
		self.file = weapon_data
		self.sounds = json.load( open("sounds/weapon_sounds.json") )

		loadUi("item_window.ui", self)

		self.setFixedSize(838, 853)

		self.setWindowTitle(self.weapon)
		self.setWindowIcon(QtGui.QIcon('logo.png'))

		self.Date.setFont(QFont("TF2 Build", 16))
		
		dates = [datetime.strptime(i, "%Y-%m-%d") for i in list(self.file["stats"].keys())]
		date_list_days = [(i-dates[-1]).days for i in dates][:-1]
		print(date_list_days)
		self.DateSelector = Ticks(date_list_days, QtCore.QRect(10, 45, 781, 31),  parent = self)
		self.DateSelector.valueChanged.connect(self.update_date)
		self.DateSelector.valueChanged.connect(self.update_info)

		self.initialize_date_range()
		self.DateSelector.setMaximum((self.last - self.first).days)
		self.Date.setText(self.first.strftime("%b %d, %Y"))

		self.item.setPixmap(QtGui.QPixmap(f"weapon_images/{self.weapon}.png"))

		self.name.setFont(QFont("TF2 Build", 18))
		self.name.setText(f"{self.weapon}")

		self.type.setFont(QFont("TF2 Secondary", 16))
		self.type.setText(f"{self.file['title']}")

		self.attrs.setLayout(QVBoxLayout())
		self.changes.setLayout(QVBoxLayout())

		self.changelog.setFont(QFont("TF2 Build", 20))

		self.back.setFont(QFont("TF2 Build", 18))
		self.back.clicked.connect(self.close_window)
		self.back.setCursor(Qt.PointingHandCursor)

		self.next.setFont(QFont("TF2 Build", 16))
		self.next.clicked.connect(self.next_update)
		self.previous.setFont(QFont("TF2 Build", 16))
		self.previous.clicked.connect(self.prev_update)

		self.update_info()

		self.player = QMediaPlayer()
		self.player.setVolume(5)

		self.setStyleSheet("""QToolTip {
								font-family: "TF2 Secondary";
								font-size: 16px;
								border-radius:10px;
								border-color:rgb(132, 132, 132);
								border-width:3px; 
								border-style: solid;
								background-color: rgb(43, 39, 36);
								font-weight: bold;
								}""")

	def get_nearest_date(self):
		current_date = self.first + timedelta(days = self.DateSelector.value())
		dates = [datetime.strptime(i, "%Y-%m-%d") for i in list(self.file["stats"].keys())]
		display = min([(current_date-date, date) for date in dates if (current_date-date).days>=0], key=lambda x: x[0])[1]

		return(display)

	def next_update(self):
		current_date = self.first + timedelta(days = self.DateSelector.value())
		dates = [datetime.strptime(i, "%Y-%m-%d") for i in list(self.file["stats"].keys())]
		try:
			display = max([(current_date-date, date) for date in dates if (current_date-date).days<0], key=lambda x: x[0])[1]
		except ValueError:
			return()
		nearest = display - self.first
		self.DateSelector.setValue( nearest.days )

	def prev_update(self):
		current_date = self.first + timedelta(days = self.DateSelector.value())
		dates = [datetime.strptime(i, "%Y-%m-%d") for i in list(self.file["stats"].keys())]
		try:
			display = min([(current_date-date, date) for date in dates if (current_date-date).days>0], key=lambda x: x[0])[1]
		except ValueError:
			return()
		nearest = display - self.first

		self.DateSelector.setValue( nearest.days )

	def close_window(self):
		if self.sounds[self.weapon]+"_drop.wav" in os.listdir("sounds"):
			Window.play_sound(self, self.sounds[self.weapon]+"_drop.wav" )
		else:
			Window.play_sound(self, "item_default_drop.wav" )
		self.close()

	def update_date(self):
		delta = self.DateSelector.value()
		new_date = self.first + timedelta(days = delta)
		self.Date.setText(new_date.strftime("%b %d, %Y"))

	def update_info(self):
		index = self.attrs.layout().count()
		for i in reversed(range(index)): 
			self.attrs.layout().itemAt(i).widget().setParent(None)

		display = self.get_nearest_date()
		date = display.strftime("%Y-%m-%d")

		pos = self.file['stats'][date]['positive']
		neg = self.file['stats'][date]['negative']
		neu = self.file['stats'][date]['neutral']

		index = 0
		if pos != []:
			self.attrs.layout().addWidget(self.positive, Qt.AlignTop)
			self.attrs.layout().setStretch(index, 0)
			index += 1
		
		if neg != []:
			self.attrs.layout().addWidget(self.negative, Qt.AlignTop)
			self.attrs.layout().setStretch(index, 0)
			index += 1
		
		if neu != []:
			self.attrs.layout().addWidget(self.neutral, Qt.AlignTop)
			self.attrs.layout().setStretch(index, 0)
			index += 1

		self.attrs.layout().setAlignment(Qt.AlignTop)
		
		self.attrs.layout().addWidget(self.dummy, Qt.AlignTop)

		self.positive.setFont(QFont("TF2 Secondary", 16))
		self.positive.setText('\n'.join(pos))

		self.negative.setFont(QFont("TF2 Secondary", 16))
		self.negative.setText('\n'.join(neg))

		self.neutral.setFont(QFont("TF2 Secondary", 16))
		self.neutral.setText('\n'.join(neu))

		update = ""
		for i in range( len(self.file['stats'][date]['changes']) ):
			if i % 2 == 0:
				update += '<div style="color:rgb(252, 243, 222);">• ' + self.file['stats'][date]['changes'][i] + "</div>\n"
			else:
				update += '<div style="color:rgb(178, 172, 149);">• ' + self.file['stats'][date]['changes'][i] + "</div>\n"

		self.changelog_date.setFont(QFont("TF2 Build", 20))
		self.changelog_date.setText(date)

		self.changes_text.setFont(QFont("TF2 Secondary", 16))
		self.changes_text.setText(update)

		self.changes.layout().setStretch(0, 0)
		self.changes.layout().addWidget(self.changes_text, Qt.AlignTop)
		self.changes.layout().addWidget(self.dummy_2, Qt.AlignTop)


	def initialize_date_range(self):
		self.last = datetime.strptime(list(self.file["stats"].keys())[0], "%Y-%m-%d")
		self.first = datetime.strptime(list(self.file["stats"].keys())[-1], "%Y-%m-%d")


 
app = QApplication(sys.argv)

file = QFile(":/dark/stylesheet.qss")
file.open(QFile.ReadOnly | QFile.Text)
stream = QTextStream(file)
app.setStyleSheet(stream.readAll())

window = Window()
window.show()
sys.exit(app.exec())
