package com.aisalt.meter.ble

import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCharacteristic
import android.content.Context
import com.aisalt.meter.protocol.LineAssembler
import no.nordicsemi.android.ble.BleManager
import no.nordicsemi.android.ble.ConnectionPriorityRequest
import no.nordicsemi.android.ble.PhyRequest
import no.nordicsemi.android.ble.ktx.suspend
import no.nordicsemi.android.ble.observer.ConnectionObserver
import java.util.UUID

/** GATT layout of firmware/SalinityMeterApp (BleLink.h). */
object MeterUuids {
    val NUS_SERVICE: UUID = UUID.fromString("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
    val NUS_RX: UUID = UUID.fromString("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
    val NUS_TX: UUID = UUID.fromString("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
    val IMG_SERVICE: UUID = UUID.fromString("5A17A000-6D2B-4E8C-9C3B-7E3F0A1C0001")
    val IMG_DATA: UUID = UUID.fromString("5A17A001-6D2B-4E8C-9C3B-7E3F0A1C0001")
}

enum class LinkState { DISCONNECTED, CONNECTING, READY, DISCONNECTING, FAILED }

/**
 * Nordic Android-BLE-Library manager. Callbacks run on the main thread.
 * Requests MTU 517, high connection priority and 2M PHY to speed up image transfer.
 */
class MeterBleManager(
    context: Context,
    private val onLine: (String) -> Unit,
    private val onImagePacket: (ByteArray) -> Unit,
    private val onState: (LinkState, String?) -> Unit,
) : BleManager(context) {

    private var rx: BluetoothGattCharacteristic? = null
    private var tx: BluetoothGattCharacteristic? = null
    private var img: BluetoothGattCharacteristic? = null
    private val lines = LineAssembler()

    init {
        setConnectionObserver(object : ConnectionObserver {
            override fun onDeviceConnecting(device: BluetoothDevice) = onState(LinkState.CONNECTING, null)
            override fun onDeviceConnected(device: BluetoothDevice) = onState(LinkState.CONNECTING, "initializing")
            override fun onDeviceFailedToConnect(device: BluetoothDevice, reason: Int) =
                onState(LinkState.FAILED, "connect failed ($reason)")
            override fun onDeviceReady(device: BluetoothDevice) = onState(LinkState.READY, null)
            override fun onDeviceDisconnecting(device: BluetoothDevice) = onState(LinkState.DISCONNECTING, null)
            override fun onDeviceDisconnected(device: BluetoothDevice, reason: Int) =
                onState(LinkState.DISCONNECTED, "reason $reason")
        })
    }

    override fun isRequiredServiceSupported(gatt: BluetoothGatt): Boolean {
        val nus = gatt.getService(MeterUuids.NUS_SERVICE) ?: return false
        rx = nus.getCharacteristic(MeterUuids.NUS_RX)
        tx = nus.getCharacteristic(MeterUuids.NUS_TX)
        img = gatt.getService(MeterUuids.IMG_SERVICE)?.getCharacteristic(MeterUuids.IMG_DATA)
        return rx != null && tx != null
    }

    override fun initialize() {
        lines.reset()
        requestMtu(517).enqueue()
        requestConnectionPriority(ConnectionPriorityRequest.CONNECTION_PRIORITY_HIGH).enqueue()
        setPreferredPhy(PhyRequest.PHY_LE_2M_MASK, PhyRequest.PHY_LE_2M_MASK, PhyRequest.PHY_OPTION_NO_PREFERRED)
            .enqueue()
        img?.let { characteristic ->
            setNotificationCallback(characteristic).with { _, data ->
                data.value?.let(onImagePacket)
            }
            enableNotifications(characteristic).enqueue()
        }
        // Subscribe to TX last: the firmware pushes hello/settings when TX is enabled.
        setNotificationCallback(tx).with { _, data ->
            data.value?.let { bytes -> lines.feed(bytes).forEach(onLine) }
        }
        enableNotifications(tx).enqueue()
    }

    override fun onServicesInvalidated() {
        rx = null
        tx = null
        img = null
    }

    suspend fun connectTo(device: BluetoothDevice) {
        connect(device)
            .retry(3, 200)
            .useAutoConnect(false)
            .timeout(15_000)
            .suspend()
    }

    suspend fun disconnectNow() {
        disconnect().suspend()
    }

    /** Writes one command line. */
    suspend fun send(command: String) {
        val characteristic = rx ?: error("not connected")
        writeCharacteristic(
            characteristic,
            (command.trim() + "\n").toByteArray(Charsets.UTF_8),
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT,
        ).suspend()
    }
}
