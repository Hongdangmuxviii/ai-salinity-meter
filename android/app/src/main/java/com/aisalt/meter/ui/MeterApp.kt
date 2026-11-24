package com.aisalt.meter.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.aisalt.meter.ble.LinkState
import com.aisalt.meter.data.MeterViewModel

private val tabs = listOf("연결", "측정", "조리", "설정", "로그")

fun blePermissions(): Array<String> =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
    } else {
        arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION, Manifest.permission.ACCESS_FINE_LOCATION)
    }

@Composable
fun MeterApp(vm: MeterViewModel = viewModel()) {
    val st by vm.state.collectAsStateWithLifecycle()
    var tab by rememberSaveable { mutableIntStateOf(0) }
    val context = LocalContext.current
    var granted by remember {
        mutableStateOf(blePermissions().all {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        })
    }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        granted = result.values.all { it }
    }

    Scaffold(
        topBar = {
            Column {
                TabRow(selectedTabIndex = tab) {
                    tabs.forEachIndexed { i, title ->
                        Tab(selected = tab == i, onClick = { tab = i }, text = { Text(title) })
                    }
                }
                val linkText = when (st.link) {
                    LinkState.READY -> "연결됨: ${st.hello?.name ?: st.deviceName ?: ""}"
                    LinkState.CONNECTING -> "연결 중… ${st.linkNote ?: ""}"
                    LinkState.DISCONNECTING -> "해제 중…"
                    LinkState.FAILED -> "연결 실패 ${st.linkNote ?: ""}"
                    LinkState.DISCONNECTED -> "연결 안 됨"
                }
                Text(linkText, Modifier.padding(horizontal = 12.dp, vertical = 4.dp), style = MaterialTheme.typography.labelMedium)
                st.lastError?.let { err ->
                    Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text("오류: $err", Modifier.weight(1f), color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall)
                        TextButton(onClick = vm::clearError) { Text("닫기") }
                    }
                }
            }
        },
    ) { padding ->
        val modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 12.dp)
        when (tab) {
            0 -> ConnectScreen(st, vm, granted, { launcher.launch(blePermissions()) }, modifier)
            1 -> MeasureScreen(st, vm, modifier)
            2 -> CookScreen(st, vm, modifier)
            3 -> SetupScreen(st, vm, modifier)
            else -> LogScreen(st, vm, modifier)
        }
    }
}
