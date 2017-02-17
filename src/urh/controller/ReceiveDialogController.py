import numpy as np
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QMessageBox

from urh.LiveSceneManager import LiveSceneManager
from urh.controller.SendRecvDialogController import SendRecvDialogController
from urh.dev.VirtualDevice import Mode, VirtualDevice
from urh.util import FileOperator
from urh.util.Formatter import Formatter


class ReceiveDialogController(SendRecvDialogController):
    files_recorded = pyqtSignal(list)

    def __init__(self, freq, samp_rate, bw, gain, device: str, parent=None, testing_mode=False):
        self.is_rx = True
        super().__init__(freq, samp_rate, bw, gain, device, parent=parent, testing_mode=testing_mode)

        self.graphics_view = self.ui.graphicsViewReceive
        self.ui.stackedWidget.setCurrentIndex(0)
        self.hide_send_ui_items()
        self.already_saved = True
        self.recorded_files = []

        self.scene_manager = LiveSceneManager(np.array([]), parent=self)  # set really in on_device_started

        self.graphics_view.setScene(self.scene_manager.scene)
        self.graphics_view.scene_manager = self.scene_manager

        self.init_device()

        self.create_connects()

    def create_connects(self):
        super().create_connects()
        self.ui.btnSave.clicked.connect(self.on_save_clicked)

    def save_before_close(self):
        if not self.already_saved and self.device.current_index > 0:
            reply = QMessageBox.question(self, self.tr("Save data?"),
                                         self.tr("Do you want to save the data you have captured so far?"),
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Abort)
            if reply == QMessageBox.Yes:
                self.on_save_clicked()
            elif reply == QMessageBox.Abort:
                return False

            self.files_recorded.emit(self.recorded_files)

        return True

    def update_view(self):
        if super().update_view():
            self.scene_manager.end = self.device.current_index
            self.scene_manager.init_scene()
            self.scene_manager.show_full_scene()
            self.graphics_view.update()

    def init_device(self):
        device_name = self.ui.cbDevice.currentText()
        if self.device:
            self.device.free_data()
        # Can't perform gc.collect() here, because the dialog itself would be deleted
        # see https://github.com/jopohl/urh/issues/83
        # gc.collect()
        self.device = VirtualDevice(self.backend_handler, device_name, Mode.receive, bw=1e6,
                                    freq=433.92e6, gain=40, samp_rate=1e6,
                                    device_ip="192.168.10.2", parent=self)
        self._create_device_connects()

        self.scene_manager = LiveSceneManager(np.array([]), parent=self)

    @pyqtSlot()
    def on_start_clicked(self):
        super().on_start_clicked()
        self.device.start()

    @pyqtSlot()
    def on_device_started(self):
        super().on_device_started()

        self.scene_manager.plot_data = self.device.data.real if self.device.data is not None else None
        self.already_saved = False
        self.ui.btnStart.setEnabled(False)
        self.set_device_ui_items_enabled(False)

    @pyqtSlot()
    def on_clear_clicked(self):
        self.reset()

    @pyqtSlot()
    def on_save_clicked(self):
        data = self.device.data[:self.device.current_index]

        dev = self.device
        big_val = Formatter.big_value_with_suffix
        initial_name = "{0} {1}Hz {2}Sps {3}Hz.complex".format(dev.name, big_val(dev.frequency),
                                                               big_val(dev.sample_rate),
                                                               big_val(dev.bandwidth)).replace(
            Formatter.local_decimal_seperator(), "_").replace("_000", "")

        filename = FileOperator.save_data_dialog(initial_name, data, parent=self)
        self.already_saved = True
        if filename is not None and filename not in self.recorded_files:
            self.recorded_files.append(filename)
