package com.aisalt.meter.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.aisalt.meter.ble.LinkState
import com.aisalt.meter.data.MeterUiState
import com.aisalt.meter.data.MeterViewModel

@Composable
fun ConnectScreen(
    st: MeterUiState,
    vm: MeterViewModel,
    permissionsGranted: Boolean,
    requestPermissions: () -> Unit,
    modifier: Modifier,
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (!permissionsGranted) {
            Text("블루투스 검색·연결 권한이 필요합니다.")
            Button(onClick = requestPermissions) { Text("권한 요청") }
            return@Column
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (st.scanning) OutlinedButton(onClick = vm::stopScan) { Text("검색 중지") }
            else Button(onClick = vm::startScan, enabled = st.link != LinkState.READY) { Text("기기 검색") }
            if (st.link == LinkState.READY || st.link == LinkState.CONNECTING) {
                OutlinedButton(onClick = vm::disconnect) { Text("연결 해제") }
            }
        }
        st.hello?.let { h ->
            Section("기기 정보") {
                KeyValue("이름 / 펌웨어", "${h.name ?: "—"} / ${h.fw ?: "—"}")
                KeyValue("보정표", h.cal ?: "—")
                KeyValue("ADS / 온도 / OLED", "${ok(h.adc)} / ${ok(h.tempSensor)} / ${ok(h.oled)}")
                KeyValue("ToF / 카메라 / PSRAM", "${ok(h.tof)} / ${ok(h.camera)} / ${ok(h.psram)}")
                KeyValue("저장된 기록", "${h.records ?: 0}건")
            }
        }
        Text("발견한 기기 (SaltMeter-XXXX)")
        LazyColumn {
            items(st.found, key = { it.device.address }) { d ->
                Column(
                    Modifier.fillMaxWidth().clickable(enabled = st.link != LinkState.READY) { vm.connect(d) }
                        .padding(vertical = 10.dp),
                ) {
                    Text(d.name)
                    Text("${d.device.address}  RSSI ${d.rssi} dBm")
                }
                HorizontalDivider()
            }
        }
    }
}

private fun ok(b: Boolean) = if (b) "있음" else "없음"
