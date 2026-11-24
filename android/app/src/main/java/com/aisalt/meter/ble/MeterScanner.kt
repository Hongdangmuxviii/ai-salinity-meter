package com.aisalt.meter.ble

import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.ParcelUuid

data class FoundDevice(val device: BluetoothDevice, val name: String, val rssi: Int)

/** Scans for devices advertising the NUS service (the meter's advertisement). */
@SuppressLint("MissingPermission")  // the UI requests BLUETOOTH_SCAN / location before calling
class MeterScanner(context: Context, private val onFound: (FoundDevice) -> Unit) {
    private val adapter = (context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager).adapter
    private var scanning = false

    private val callback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val name = result.scanRecord?.deviceName ?: result.device.name ?: result.device.address
            onFound(FoundDevice(result.device, name, result.rssi))
        }
    }

    val isBluetoothOn: Boolean get() = adapter?.isEnabled == true

    fun start(): Boolean {
        val scanner = adapter?.bluetoothLeScanner ?: return false
        if (scanning) return true
        val filter = ScanFilter.Builder().setServiceUuid(ParcelUuid(MeterUuids.NUS_SERVICE)).build()
        val settings = ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build()
        scanner.startScan(listOf(filter), settings, callback)
        scanning = true
        return true
    }

    fun stop() {
        if (!scanning) return
        adapter?.bluetoothLeScanner?.stopScan(callback)
        scanning = false
    }
}
